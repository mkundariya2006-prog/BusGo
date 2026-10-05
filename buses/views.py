import datetime
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Min, Max
from django.utils import timezone
from routes.models import City, Route, BusSchedule, BoardingPoint, DroppingPoint
from .models import Bus, BusType, Seat
from bookings.models import ScheduleSeatStatus
from operators.models import BusOperator

def home_view(request):
    """
    BusGo Home Page with modern hero section, city selectors, popular routes, and destinations across Gujarat.
    """
    cities = City.objects.all().order_by('name')
    popular_cities = City.objects.filter(is_popular=True).order_by('name')
    top_destinations = popular_cities[:12]
    popular_routes = Route.objects.filter(is_active=True).select_related('origin', 'destination')[:12]
    
    # Calculate starting price for popular routes
    route_cards = []
    today = timezone.localdate()
    for r in popular_routes:
        min_price = BusSchedule.objects.filter(
            route=r, departure_date__gte=today
        ).aggregate(Min('base_price'))['base_price__min'] or 499.00
        
        bus_count = BusSchedule.objects.filter(
            route=r, departure_date=today
        ).values('bus').distinct().count() or 4

        route_cards.append({
            'route': r,
            'origin': r.origin.name,
            'destination': r.destination.name,
            'distance_km': r.distance_km,
            'duration_hours': r.estimated_duration_hours,
            'starting_price': int(min_price),
            'bus_count': bus_count,
        })

    offers = [
        {
            'code': 'BUSGO15',
            'discount': '15% OFF',
            'title': 'First Booking Special',
            'desc': 'Save up to ₹150 on your first bus journey with BusGo.',
            'badge': 'NEW USERS'
        },
        {
            'code': 'FESTIVE50',
            'discount': 'FLAT ₹50 OFF',
            'title': 'Weekend Explorer Pass',
            'desc': 'Instant discount on all intercity round trips and sleepers.',
            'badge': 'POPULAR'
        },
        {
            'code': 'VOLVOPRO',
            'discount': '₹120 OFF',
            'title': 'Luxury Multi-Axle Volvo',
            'desc': 'Premium comfort with high-speed WiFi and onboard blankets.',
            'badge': 'LUXURY'
        },
    ]

    context = {
        'cities': cities,
        'popular_cities': popular_cities,
        'top_destinations': top_destinations,
        'route_cards': route_cards,
        'offers': offers,
        'today_str': today.strftime('%Y-%m-%d'),
        'total_cities_count': cities.count(),
    }
    return render(request, 'buses/home.html', context)


def search_buses_view(request):
    """
    Search buses based on Origin, Destination, Journey Date, with multiple filters and sorting.
    """
    origin_name = request.GET.get('origin', '').strip()
    destination_name = request.GET.get('destination', '').strip()
    date_str = request.GET.get('date', '').strip()
    
    today = timezone.localdate()
    if date_str:
        try:
            journey_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            journey_date = today
    else:
        journey_date = today

    # Base Query
    schedules = BusSchedule.objects.filter(
        departure_date=journey_date,
        status='scheduled'
    ).select_related(
        'bus', 'bus__operator', 'bus__bus_type', 'route', 'route__origin', 'route__destination'
    )

    if origin_name:
        schedules = schedules.filter(
            Q(route__origin__name__icontains=origin_name) | Q(route__origin__id__exact=origin_name if origin_name.isdigit() else 0)
        )
    if destination_name:
        schedules = schedules.filter(
            Q(route__destination__name__icontains=destination_name) | Q(route__destination__id__exact=destination_name if destination_name.isdigit() else 0)
        )

    # Filters
    # 1. AC / Non-AC
    ac_filter = request.GET.get('ac_type')
    if ac_filter == 'ac':
        schedules = schedules.filter(bus__bus_type__is_ac=True)
    elif ac_filter == 'non_ac':
        schedules = schedules.filter(bus__bus_type__is_ac=False)

    # 2. Seater / Sleeper
    category_filter = request.GET.get('bus_category')
    if category_filter:
        schedules = schedules.filter(bus__bus_type__category=category_filter)

    # 3. Operator
    operator_id = request.GET.get('operator')
    if operator_id and operator_id.isdigit():
        schedules = schedules.filter(bus__operator_id=int(operator_id))

    # 4. Departure Time slots
    time_slot = request.GET.get('time_slot')
    if time_slot == 'morning': # 06:00 to 12:00
        schedules = schedules.filter(departure_time__gte='06:00:00', departure_time__lt='12:00:00')
    elif time_slot == 'afternoon': # 12:00 to 18:00
        schedules = schedules.filter(departure_time__gte='12:00:00', departure_time__lt='18:00:00')
    elif time_slot == 'evening': # 18:00 to 24:00
        schedules = schedules.filter(departure_time__gte='18:00:00', departure_time__lte='23:59:59')
    elif time_slot == 'night': # 00:00 to 06:00
        schedules = schedules.filter(departure_time__gte='00:00:00', departure_time__lt='06:00:00')

    # 5. Price filtering
    min_p = request.GET.get('min_price')
    max_p = request.GET.get('max_price')
    if min_p and min_p.isdigit():
        schedules = schedules.filter(base_price__gte=float(min_p))
    if max_p and max_p.isdigit():
        schedules = schedules.filter(base_price__lte=float(max_p))

    # 6. Amenities
    if request.GET.get('wifi') == '1':
        schedules = schedules.filter(bus__has_wifi=True)
    if request.GET.get('charging') == '1':
        schedules = schedules.filter(bus__has_charging=True)
    if request.GET.get('water') == '1':
        schedules = schedules.filter(bus__has_water=True)
    if request.GET.get('blanket') == '1':
        schedules = schedules.filter(bus__has_blanket=True)

    # Sorting
    sort_by = request.GET.get('sort', 'cheapest')
    if sort_by == 'cheapest':
        schedules = schedules.order_by('base_price')
    elif sort_by == 'earliest':
        schedules = schedules.order_by('departure_time')
    elif sort_by == 'duration':
        schedules = schedules.order_by('route__estimated_duration_hours')
    elif sort_by == 'rating':
        schedules = schedules.order_by('-bus__rating')
    else:
        schedules = schedules.order_by('departure_time')

    # Build detailed bus list with seat availability
    schedule_data = []
    for s in schedules:
        total_seats = s.bus.seats.count()
        booked_count = ScheduleSeatStatus.objects.filter(
            schedule=s,
            status='booked'
        ).count()
        available_seats = max(0, total_seats - booked_count)

        schedule_data.append({
            'schedule': s,
            'bus': s.bus,
            'operator': s.bus.operator,
            'bus_type': s.bus.bus_type,
            'route': s.route,
            'available_seats': available_seats,
            'total_seats': total_seats,
            'duration': s.duration_display,
            'boarding_points': s.route.boarding_points.all(),
            'dropping_points': s.route.dropping_points.all(),
        })

    all_cities = City.objects.all().order_by('name')
    all_operators = BusOperator.objects.filter(status='approved')

    context = {
        'origin_name': origin_name,
        'destination_name': destination_name,
        'journey_date': journey_date,
        'date_str': journey_date.strftime('%Y-%m-%d'),
        'prev_date': (journey_date - datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
        'next_date': (journey_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
        'is_past_prev': (journey_date - datetime.timedelta(days=1)) < today,
        'schedules': schedule_data,
        'total_results': len(schedule_data),
        'all_cities': all_cities,
        'all_operators': all_operators,
        'current_sort': sort_by,
    }
    return render(request, 'buses/search_results.html', context)


def get_schedule_seats_api(request, schedule_id):
    """
    JSON API returning interactive seat layout for lower & upper deck for a schedule,
    including boarding and dropping points.
    """
    schedule = get_object_or_404(
        BusSchedule.objects.select_related('bus', 'bus__bus_type', 'route'),
        id=schedule_id
    )
    bus = schedule.bus

    # Fetch seat statuses
    seat_statuses = {
        ss.seat_id: ss
        for ss in ScheduleSeatStatus.objects.filter(schedule=schedule).select_related('seat')
    }

    seats = bus.seats.filter(is_active=True).order_by('deck', 'row', 'column')

    lower_deck_seats = []
    upper_deck_seats = []

    for s in seats:
        ss = seat_statuses.get(s.id)
        effective_status = ss.get_effective_status() if ss else 'available'
        
        # Calculate seat price
        seat_price = round(float(schedule.base_price) * float(s.price_multiplier), 2)

        seat_info = {
            'id': s.id,
            'seat_number': s.seat_number,
            'deck': s.deck,
            'seat_type': s.seat_type,
            'row': s.row,
            'column': s.column,
            'is_ladies_only': s.is_ladies_only,
            'price': seat_price,
            'status': effective_status,
        }

        if s.deck == 'lower':
            lower_deck_seats.append(seat_info)
        else:
            upper_deck_seats.append(seat_info)

    boarding_points = [
        {
            'id': bp.id,
            'location_name': bp.location_name,
            'city': bp.city.name,
            'landmark': bp.landmark,
            'time_offset': bp.time_offset_minutes,
            'time': (datetime.datetime.combine(schedule.departure_date, schedule.departure_time) + datetime.timedelta(minutes=bp.time_offset_minutes)).strftime('%I:%M %p')
        }
        for bp in schedule.route.boarding_points.all()
    ]

    dropping_points = [
        {
            'id': dp.id,
            'location_name': dp.location_name,
            'city': dp.city.name,
            'landmark': dp.landmark,
            'time_offset': dp.time_offset_minutes,
            'time': (datetime.datetime.combine(schedule.arrival_date, schedule.arrival_time) + datetime.timedelta(minutes=dp.time_offset_minutes)).strftime('%I:%M %p')
        }
        for dp in schedule.route.dropping_points.all()
    ]

    return JsonResponse({
        'schedule_id': schedule.id,
        'bus_name': bus.bus_name,
        'bus_number': bus.bus_number,
        'bus_type': bus.bus_type.name,
        'has_upper_deck': bus.bus_type.has_upper_deck,
        'layout_type': bus.bus_type.layout_type,
        'base_price': float(schedule.base_price),
        'lower_deck': lower_deck_seats,
        'upper_deck': upper_deck_seats,
        'boarding_points': boarding_points,
        'dropping_points': dropping_points,
    })
