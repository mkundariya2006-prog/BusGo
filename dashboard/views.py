import json
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone

from accounts.models import CustomerProfile
from operators.models import BusOperator
from buses.models import Bus, BusType, Seat
from routes.models import City, Route, BusSchedule, BoardingPoint, DroppingPoint
from bookings.models import Booking, Passenger, Cancellation, Refund, ScheduleSeatStatus
from payments.models import Payment

def is_admin_user(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@user_passes_test(is_admin_user, login_url='/accounts/login/')
def admin_dashboard_view(request):
    """
    Main Admin Dashboard with KPIs and Chart.js analytics.
    """
    today = timezone.localdate()
    
    total_customers = User.objects.filter(is_staff=False).exclude(operator_profile__isnull=False).count()
    total_buses = Bus.objects.count()
    total_operators = BusOperator.objects.count()
    todays_bookings = Booking.objects.filter(created_at__date=today).count()
    
    total_revenue = Payment.objects.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0.00
    cancelled_bookings = Booking.objects.filter(booking_status='cancelled').count()

    # Chart 1: Daily bookings (last 7 days)
    chart_dates = []
    chart_bookings = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        chart_dates.append(d.strftime('%d %b'))
        cnt = Booking.objects.filter(created_at__date=d).count()
        chart_bookings.append(cnt)

    # Chart 2: Popular routes
    route_stats = Route.objects.annotate(
        b_count=Count('schedules__bookings')
    ).order_by('-b_count')[:5]
    route_labels = [f"{r.origin.name} → {r.destination.name}" for r in route_stats]
    route_data = [r.b_count for r in route_stats]

    # Chart 3: Bus Fleet Category breakdown
    bus_type_stats = BusType.objects.annotate(count=Count('buses')).values('name', 'count')
    fleet_labels = [b['name'].split('(')[0].strip() for b in bus_type_stats]
    fleet_data = [b['count'] for b in bus_type_stats]

    # Recent bookings table
    recent_bookings = Booking.objects.select_related(
        'customer', 'schedule', 'schedule__bus', 'schedule__route'
    ).order_by('-created_at')[:8]

    context = {
        'total_customers': total_customers,
        'total_buses': total_buses,
        'total_operators': total_operators,
        'todays_bookings': todays_bookings,
        'total_revenue': float(total_revenue),
        'cancelled_bookings': cancelled_bookings,
        'chart_dates_json': json.dumps(chart_dates),
        'chart_bookings_json': json.dumps(chart_bookings),
        'route_labels_json': json.dumps(route_labels),
        'route_data_json': json.dumps(route_data),
        'fleet_labels_json': json.dumps(fleet_labels),
        'fleet_data_json': json.dumps(fleet_data),
        'recent_bookings': recent_bookings,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@user_passes_test(is_admin_user, login_url='/accounts/login/')
def admin_customers_view(request):
    query = request.GET.get('q', '').strip()
    customers = CustomerProfile.objects.select_related('user').order_by('-created_at')
    
    if query:
        customers = customers.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(phone_number__icontains=query)
        )

    return render(request, 'dashboard/admin_customers.html', {
        'customers': customers,
        'query': query
    })


@user_passes_test(is_admin_user, login_url='/accounts/login/')
def admin_toggle_customer_block(request, profile_id):
    profile = get_object_or_404(CustomerProfile, id=profile_id)
    profile.is_blocked = not profile.is_blocked
    profile.save()
    status_str = "blocked" if profile.is_blocked else "unblocked"
    messages.success(request, f"Customer {profile.user.username} has been {status_str}.")
    return redirect('dashboard:admin_customers')


@user_passes_test(is_admin_user, login_url='/accounts/login/')
def admin_operators_view(request):
    operators = BusOperator.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        op_id = request.POST.get('operator_id')
        operator = get_object_or_404(BusOperator, id=op_id)
        if action == 'approve':
            operator.status = 'approved'
            operator.save()
            messages.success(request, f"Operator {operator.company_name} approved.")
        elif action == 'reject':
            operator.status = 'rejected'
            operator.save()
            messages.warning(request, f"Operator {operator.company_name} rejected.")
        return redirect('dashboard:admin_operators')

    return render(request, 'dashboard/admin_operators.html', {'operators': operators})


@user_passes_test(is_admin_user, login_url='/accounts/login/')
def admin_buses_view(request):
    buses = Bus.objects.select_related('operator', 'bus_type').order_by('-created_at')
    operators = BusOperator.objects.filter(status='approved')
    bus_types = BusType.objects.all()

    if request.method == 'POST':
        operator_id = request.POST.get('operator')
        bus_type_id = request.POST.get('bus_type')
        bus_name = request.POST.get('bus_name')
        bus_number = request.POST.get('bus_number')

        bus = Bus.objects.create(
            operator_id=operator_id,
            bus_type_id=bus_type_id,
            bus_name=bus_name,
            bus_number=bus_number,
            has_wifi=request.POST.get('has_wifi') == 'on',
            has_charging=request.POST.get('has_charging') == 'on',
            has_water=request.POST.get('has_water') == 'on',
            has_blanket=request.POST.get('has_blanket') == 'on',
        )

        # Generate seats automatically
        b_type = bus.bus_type
        if b_type.has_upper_deck:
            # 15 lower, 15 upper
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

        messages.success(request, f"New Bus {bus.bus_name} [{bus.bus_number}] added with seat layout!")
        return redirect('dashboard:admin_buses')

    return render(request, 'dashboard/admin_buses.html', {
        'buses': buses,
        'operators': operators,
        'bus_types': bus_types,
    })


@user_passes_test(is_admin_user, login_url='/accounts/login/')
def admin_routes_view(request):
    routes = Route.objects.select_related('origin', 'destination').order_by('origin__name')
    cities = City.objects.all().order_by('name')

    if request.method == 'POST':
        origin_id = request.POST.get('origin')
        dest_id = request.POST.get('destination')
        distance = request.POST.get('distance_km', 350)
        duration = request.POST.get('duration_hours', 6.0)

        if origin_id == dest_id:
            messages.error(request, "Origin and Destination cannot be the same city.")
        else:
            Route.objects.get_or_create(
                origin_id=origin_id,
                destination_id=dest_id,
                defaults={'distance_km': distance, 'estimated_duration_hours': duration}
            )
            messages.success(request, "Route added successfully.")
            return redirect('dashboard:admin_routes')

    return render(request, 'dashboard/admin_routes.html', {
        'routes': routes,
        'cities': cities,
    })


@user_passes_test(is_admin_user, login_url='/accounts/login/')
def admin_schedules_view(request):
    schedules = BusSchedule.objects.select_related(
        'bus', 'bus__operator', 'route', 'route__origin', 'route__destination'
    ).order_by('-departure_date', 'departure_time')[:100]

    buses = Bus.objects.filter(is_active=True)
    routes = Route.objects.filter(is_active=True)

    if request.method == 'POST':
        bus_id = request.POST.get('bus')
        route_id = request.POST.get('route')
        dept_date = request.POST.get('departure_date')
        dept_time = request.POST.get('departure_time')
        arr_date = request.POST.get('arrival_date')
        arr_time = request.POST.get('arrival_time')
        price = request.POST.get('base_price')

        sch = BusSchedule.objects.create(
            bus_id=bus_id,
            route_id=route_id,
            departure_date=dept_date,
            departure_time=dept_time,
            arrival_date=arr_date,
            arrival_time=arr_time,
            base_price=price,
            status='scheduled'
        )
        # Create seat statuses
        for s in sch.bus.seats.all():
            ScheduleSeatStatus.objects.create(schedule=sch, seat=s, status='available')

        messages.success(request, "Schedule created and seats configured!")
        return redirect('dashboard:admin_schedules')

    return render(request, 'dashboard/admin_schedules.html', {
        'schedules': schedules,
        'buses': buses,
        'routes': routes,
    })


@user_passes_test(is_admin_user, login_url='/accounts/login/')
def admin_bookings_view(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')

    bookings = Booking.objects.select_related(
        'customer', 'schedule', 'schedule__bus', 'schedule__route'
    ).order_by('-created_at')

    if query:
        bookings = bookings.filter(
            Q(booking_id__icontains=query) |
            Q(customer__username__icontains=query) |
            Q(customer__email__icontains=query) |
            Q(contact_phone__icontains=query)
        )

    if status_filter:
        bookings = bookings.filter(booking_status=status_filter)

    return render(request, 'dashboard/admin_bookings.html', {
        'bookings': bookings[:100],
        'query': query,
        'status_filter': status_filter,
    })


@user_passes_test(is_admin_user, login_url='/accounts/login/')
def admin_reports_view(request):
    """
    Financial and operational reports.
    """
    total_revenue = Payment.objects.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0.00
    total_refunds = Refund.objects.filter(status='processed').aggregate(Sum('amount'))['amount__sum'] or 0.00
    net_revenue = float(total_revenue) - float(total_refunds)

    popular_routes = Route.objects.annotate(
        booking_count=Count('schedules__bookings')
    ).order_by('-booking_count')[:10]

    payments = Payment.objects.select_related('booking', 'booking__customer').order_by('-created_at')[:20]
    refunds = Refund.objects.select_related('cancellation', 'cancellation__booking').order_by('-processed_at')[:20]

    context = {
        'total_revenue': float(total_revenue),
        'total_refunds': float(total_refunds),
        'net_revenue': net_revenue,
        'popular_routes': popular_routes,
        'payments': payments,
        'refunds': refunds,
    }
    return render(request, 'dashboard/admin_reports.html', context)
