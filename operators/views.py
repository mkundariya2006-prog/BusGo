from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone

from .models import BusOperator
from buses.models import Bus, BusType, Seat
from routes.models import Route, City, BusSchedule, BoardingPoint, DroppingPoint
from bookings.models import Booking, Passenger, ScheduleSeatStatus

def get_operator(user):
    if hasattr(user, 'operator_profile'):
        return user.operator_profile
    return None

@login_required
def operator_dashboard_view(request):
    operator = get_operator(request.user)
    if not operator:
        messages.error(request, "Access restricted to registered Bus Operators.")
        return redirect('home')

    today = timezone.localdate()
    buses = Bus.objects.filter(operator=operator)
    schedules = BusSchedule.objects.filter(bus__operator=operator)
    
    total_trips = schedules.count()
    active_trips_today = schedules.filter(departure_date=today).count()
    
    bookings = Booking.objects.filter(schedule__bus__operator=operator, booking_status='confirmed')
    total_passengers = Passenger.objects.filter(booking__schedule__bus__operator=operator, booking__booking_status='confirmed').count()
    
    total_earnings = bookings.aggregate(Sum('total_amount'))['total_amount__sum'] or 0.00
    # Net operator earnings after 10% commission
    net_earnings = float(total_earnings) * 0.90

    recent_schedules = schedules.select_related('bus', 'route', 'route__origin', 'route__destination').order_by('-departure_date', '-departure_time')[:6]

    context = {
        'operator': operator,
        'buses_count': buses.count(),
        'active_trips_today': active_trips_today,
        'total_passengers': total_passengers,
        'net_earnings': net_earnings,
        'total_earnings': float(total_earnings),
        'recent_schedules': recent_schedules,
    }
    return render(request, 'operators/operator_dashboard.html', context)


@login_required
def operator_buses_view(request):
    operator = get_operator(request.user)
    if not operator:
        return redirect('home')

    buses = Bus.objects.filter(operator=operator).select_related('bus_type')
    bus_types = BusType.objects.all()

    if request.method == 'POST':
        bus_name = request.POST.get('bus_name')
        bus_number = request.POST.get('bus_number')
        bus_type_id = request.POST.get('bus_type')

        bus = Bus.objects.create(
            operator=operator,
            bus_name=bus_name,
            bus_number=bus_number,
            bus_type_id=bus_type_id,
            has_wifi=request.POST.get('has_wifi') == 'on',
            has_charging=request.POST.get('has_charging') == 'on',
            has_water=request.POST.get('has_water') == 'on',
            has_blanket=request.POST.get('has_blanket') == 'on',
        )

        # Generate seats
        b_type = bus.bus_type
        if b_type.has_upper_deck:
            s_idx = 1
            for r in range(1, 6):
                for c in [1, 2, 3]:
                    Seat.objects.create(bus=bus, seat_number=f"L{s_idx}", deck='lower', row=r, column=c, is_ladies_only=(s_idx in [1, 2]))
                    Seat.objects.create(bus=bus, seat_number=f"U{s_idx}", deck='upper', row=r, column=c)
                    s_idx += 1
        else:
            s_idx = 1
            for r in range(1, 10):
                for c in [1, 2, 3, 4]:
                    Seat.objects.create(bus=bus, seat_number=str(s_idx), deck='lower', row=r, column=c, is_ladies_only=(s_idx in [1, 2]))
                    s_idx += 1

        messages.success(request, f"Bus {bus.bus_name} [{bus.bus_number}] added to your fleet!")
        return redirect('operators:operator_buses')

    return render(request, 'operators/operator_buses.html', {
        'operator': operator,
        'buses': buses,
        'bus_types': bus_types,
    })


@login_required
def operator_schedules_view(request):
    operator = get_operator(request.user)
    if not operator:
        return redirect('home')

    schedules = BusSchedule.objects.filter(bus__operator=operator).select_related(
        'bus', 'route', 'route__origin', 'route__destination'
    ).order_by('-departure_date', 'departure_time')

    buses = Bus.objects.filter(operator=operator, is_active=True)
    routes = Route.objects.filter(is_active=True)

    if request.method == 'POST':
        bus_id = request.POST.get('bus')
        route_id = request.POST.get('route')
        dept_date = request.POST.get('departure_date')
        dept_time = request.POST.get('departure_time')
        arr_date = request.POST.get('arrival_date')
        arr_time = request.POST.get('arrival_time')
        base_price = request.POST.get('base_price')

        sch = BusSchedule.objects.create(
            bus_id=bus_id,
            route_id=route_id,
            departure_date=dept_date,
            departure_time=dept_time,
            arrival_date=arr_date,
            arrival_time=arr_time,
            base_price=base_price,
            status='scheduled'
        )
        for s in sch.bus.seats.all():
            ScheduleSeatStatus.objects.create(schedule=sch, seat=s, status='available')

        messages.success(request, "New schedule published!")
        return redirect('operators:operator_schedules')

    return render(request, 'operators/operator_schedules.html', {
        'operator': operator,
        'schedules': schedules,
        'buses': buses,
        'routes': routes,
    })


@login_required
def operator_passenger_manifest_view(request, schedule_id):
    """
    Passenger manifest print sheet for conductor/driver.
    """
    operator = get_operator(request.user)
    if not operator and not request.user.is_staff:
        return redirect('home')

    schedule = get_object_or_404(
        BusSchedule.objects.select_related('bus', 'route', 'route__origin', 'route__destination'),
        id=schedule_id,
        bus__operator=operator
    )

    passengers = Passenger.objects.filter(
        booking__schedule=schedule,
        booking__booking_status='confirmed'
    ).select_related('booking', 'seat', 'booking__boarding_point', 'booking__dropping_point').order_by('seat__seat_number')

    return render(request, 'operators/manifest.html', {
        'schedule': schedule,
        'passengers': passengers,
        'total_passengers': passengers.count(),
        'now': timezone.now(),
    })
