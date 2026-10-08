import os
import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from routes.models import BusSchedule, BoardingPoint, DroppingPoint
from buses.models import Seat
from .models import ScheduleSeatStatus, Booking, Passenger, Cancellation, Refund
from payments.models import Payment
from notifications.models import notify_user
from .utils import generate_booking_qr, generate_ticket_pdf, calculate_refund_amount, send_booking_ticket_email
from accounts.models import CustomerProfile, SavedPassenger

@login_required
def select_seats_view(request, schedule_id):
    """
    Dedicated seat selection page or handles seat selection submission.
    """
    schedule = get_object_or_404(
        BusSchedule.objects.select_related('bus', 'bus__bus_type', 'route', 'route__origin', 'route__destination'),
        id=schedule_id
    )
    return render(request, 'bookings/seat_selection.html', {
        'schedule': schedule,
    })


@login_required
def passenger_details_view(request, schedule_id):
    """
    Passenger details entry for selected seats. Locks seats temporarily.
    """
    schedule = get_object_or_404(
        BusSchedule.objects.select_related('bus', 'route', 'route__origin', 'route__destination'),
        id=schedule_id
    )

    if request.method == 'POST':
        # Handling submission of passenger form
        seat_ids_raw = request.POST.get('seat_ids', '')
        seat_ids = [int(sid.strip()) for sid in seat_ids_raw.split(',') if sid.strip().isdigit()]
        bp_id = request.POST.get('boarding_point')
        dp_id = request.POST.get('dropping_point')

        if not seat_ids:
            messages.error(request, "No seats selected. Please select at least one seat.")
            return redirect(f"/buses/search/?origin={schedule.route.origin.name}&destination={schedule.route.destination.name}")

        seats = Seat.objects.filter(id__in=seat_ids, bus=schedule.bus)
        if len(seats) != len(seat_ids):
            messages.error(request, "Invalid seats selected.")
            return redirect('home')

        # Lock seats concurrency-safe
        try:
            ScheduleSeatStatus.lock_seats(schedule, seat_ids, request.user, duration_minutes=10)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect(f"/buses/search/?origin={schedule.route.origin.name}&destination={schedule.route.destination.name}")

        # Check if this POST is submitting passenger names
        if 'passenger_name_0' in request.POST:
            # Contact details and promo code removed from form; use defaults
            contact_email = request.user.email
            contact_phone = ''

            # Calculate fares
            base_fare = Decimal('0.00')
            for s in seats:
                base_fare += schedule.base_price * s.price_multiplier

            tax_amount = round(base_fare * Decimal('0.05'), 2)
            convenience_fee = Decimal('20.00')
            discount_amount = Decimal('0.00')

            total_amount = max(Decimal('0.00'), base_fare + tax_amount + convenience_fee - discount_amount)

            boarding_point = BoardingPoint.objects.filter(id=bp_id).first() if bp_id else schedule.route.boarding_points.first()
            dropping_point = DroppingPoint.objects.filter(id=dp_id).first() if dp_id else schedule.route.dropping_points.first()

            with transaction.atomic():
                booking = Booking.objects.create(
                    customer=request.user,
                    schedule=schedule,
                    boarding_point=boarding_point,
                    dropping_point=dropping_point,
                    total_seats=len(seats),
                    base_fare=base_fare,
                    tax_amount=tax_amount,
                    convenience_fee=convenience_fee,
                    discount_amount=discount_amount,
                    total_amount=total_amount,
                    booking_status='pending',
                    contact_email=contact_email,
                    contact_phone=contact_phone,
                )

                for idx, s in enumerate(seats):
                    p_name = request.POST.get(f'passenger_name_{idx}', f'Passenger {idx+1}')
                    p_phone = request.POST.get(f'passenger_phone_{idx}', '')
                    p_email = request.POST.get(f'passenger_email_{idx}', '')
                    # Age, Govt ID Type and ID Number removed from UI - use safe defaults
                    p_age = 0
                    p_gender = request.POST.get(f'passenger_gender_{idx}', 'male')
                    p_id_type = ''
                    p_id_num = ''
                    seat_fare = schedule.base_price * s.price_multiplier

                    Passenger.objects.create(
                        booking=booking,
                        seat=s,
                        name=p_name,
                        age=p_age,
                        gender=p_gender,
                        id_type=p_id_type,
                        id_number=p_id_num,
                        phone=p_phone,
                        email=p_email,
                        seat_fare=seat_fare
                    )

                # Initialize Pending Payment
                Payment.objects.create(
                    booking=booking,
                    amount=total_amount,
                    payment_method='upi',
                    status='pending'
                )

            return redirect('bookings:payment', booking_id=booking.booking_id)

    # GET Request: Initial display of passenger form
    seat_ids_raw = request.GET.get('seats', '')
    bp_id = request.GET.get('bp', '')
    dp_id = request.GET.get('dp', '')

    seat_ids = [int(sid.strip()) for sid in seat_ids_raw.split(',') if sid.strip().isdigit()]
    if not seat_ids:
        messages.error(request, "Please select your seats first.")
        return redirect('buses:search')

    seats = Seat.objects.filter(id__in=seat_ids, bus=schedule.bus)
    if not seats.exists():
        messages.error(request, "No matching seats found.")
        return redirect('buses:search')

    # Try temporary lock
    try:
        ScheduleSeatStatus.lock_seats(schedule, seat_ids, request.user, duration_minutes=10)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect(f"/buses/search/?origin={schedule.route.origin.name}&destination={schedule.route.destination.name}")

    # Base price calculation
    base_fare = sum([schedule.base_price * s.price_multiplier for s in seats])
    tax_amount = round(base_fare * Decimal('0.05'), 2)
    convenience_fee = Decimal('20.00')
    total_amount = base_fare + tax_amount + convenience_fee

    boarding_point = schedule.route.boarding_points.filter(id=bp_id).first() if bp_id else schedule.route.boarding_points.first()
    dropping_point = schedule.route.dropping_points.filter(id=dp_id).first() if dp_id else schedule.route.dropping_points.first()

    customer_profile = getattr(request.user, 'customer_profile', None)
    saved_passengers = customer_profile.saved_passengers.all() if customer_profile else []

    context = {
        'schedule': schedule,
        'seats': seats,
        'seat_ids_raw': ",".join([str(s.id) for s in seats]),
        'seat_numbers': ", ".join([s.seat_number for s in seats]),
        'boarding_point': boarding_point,
        'dropping_point': dropping_point,
        'base_fare': base_fare,
        'tax_amount': tax_amount,
        'convenience_fee': convenience_fee,
        'total_amount': total_amount,
        'saved_passengers': saved_passengers,
        'user_phone': customer_profile.phone_number if customer_profile else '',
    }
    return render(request, 'bookings/passenger_details.html', context)


@login_required
def payment_view(request, booking_id):
    """
    Mock payment gateway supporting UPI, Cards, Net Banking, and BusGo Wallet.
    """
    booking = get_object_or_404(
        Booking.objects.select_related('schedule', 'schedule__bus', 'schedule__route', 'customer'),
        booking_id=booking_id
    )

    if booking.customer != request.user and not request.user.is_staff:
        raise Http404("Booking not found.")

    if booking.booking_status == 'confirmed':
        return redirect('bookings:ticket', booking_id=booking.booking_id)

    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action', 'pay_success')
        payment_method = request.POST.get('payment_method', 'upi')

        if action == 'pay_fail':
            messages.error(request, "Payment was declined or cancelled by customer. You can try again.")
            return redirect('bookings:payment', booking_id=booking.booking_id)

        # Process payment
        with transaction.atomic():
            # If wallet payment, check and deduct balance
            if payment_method == 'wallet':
                if profile.wallet_balance < booking.total_amount:
                    messages.error(request, f"Insufficient wallet balance (₹{profile.wallet_balance}). Please top up or choose another payment method.")
                    return redirect('bookings:payment', booking_id=booking.booking_id)
                profile.wallet_balance -= booking.total_amount
                profile.reward_points += int(booking.total_amount * Decimal('0.05')) # 5% reward points
                profile.save()

            # Update or create payment
            payment, _ = Payment.objects.get_or_create(
                booking=booking,
                defaults={'amount': booking.total_amount, 'payment_method': payment_method}
            )
            payment.payment_method = payment_method
            payment.status = 'success'
            payment.paid_at = timezone.now()
            
            if payment_method == 'upi':
                payment.upi_id = request.POST.get('upi_id', 'user@upi')
            elif payment_method == 'card':
                card_num = request.POST.get('card_number', '4242')
                payment.card_last4 = card_num[-4:] if len(card_num) >= 4 else '4242'
            elif payment_method == 'netbanking':
                payment.bank_name = request.POST.get('bank_name', 'HDFC Bank')
            
            payment.save()

            # Mark booking confirmed
            booking.booking_status = 'confirmed'
            booking.save()

            # Mark seats as permanently booked
            seat_ids = booking.passengers.values_list('seat_id', flat=True)
            for p in booking.passengers.all():
                ss, _ = ScheduleSeatStatus.objects.get_or_create(
                    schedule=booking.schedule,
                    seat=p.seat,
                    defaults={'status': 'booked'}
                )
                ss.status = 'booked'
                ss.locked_by = None
                ss.locked_until = None
                ss.booked_gender = p.gender
                ss.save()

        # Generate ticket assets & send email OUTSIDE the transaction
        # so the database lock is released before these slow I/O operations
        generate_booking_qr(booking)
        generate_ticket_pdf(booking)
        send_booking_ticket_email(booking)

        # Notifications
        notify_user(
            user=booking.customer,
            title="Booking Confirmed!",
            message=f"Your booking {booking.booking_id} for {booking.schedule.route} on {booking.schedule.departure_date} is confirmed! Seats: {booking.seat_numbers_display}.",
            notification_type='booking',
            link=f"/bookings/ticket/{booking.booking_id}/"
        )

        # Operator notification
        if hasattr(booking.schedule.bus.operator, 'user'):
            notify_user(
                user=booking.schedule.bus.operator.user,
                title="New Bus Booking Received",
                message=f"New booking {booking.booking_id} on {booking.schedule.bus.bus_name}. {booking.total_seats} seats booked.",
                notification_type='operator'
            )

        messages.success(request, f"Payment successful! Booking {booking.booking_id} confirmed.")
        return redirect('bookings:ticket', booking_id=booking.booking_id)

    context = {
        'booking': booking,
        'profile': profile,
    }
    return render(request, 'bookings/payment.html', context)


@login_required
def ticket_view(request, booking_id):
    """
    Digital ticket page displaying QR code, passenger details, download & print buttons.
    """
    booking = get_object_or_404(
        Booking.objects.select_related('schedule', 'schedule__bus', 'schedule__route', 'customer', 'boarding_point', 'dropping_point'),
        booking_id=booking_id
    )

    if booking.customer != request.user and not request.user.is_staff:
        raise Http404("Ticket not found.")

    # Ensure QR and PDF exist
    if not booking.qr_code_image or not os.path.exists(os.path.join(settings.MEDIA_ROOT, booking.qr_code_image.name)):
        generate_booking_qr(booking)
    if not booking.pdf_ticket or not os.path.exists(os.path.join(settings.MEDIA_ROOT, booking.pdf_ticket.name)):
        generate_ticket_pdf(booking)

    payment = getattr(booking, 'payment', None)

    context = {
        'booking': booking,
        'passengers': booking.passengers.all(),
        'payment': payment,
    }
    return render(request, 'bookings/ticket.html', context)


@login_required
def download_ticket_pdf(request, booking_id):
    """
    Downloads the ReportLab PDF ticket.
    """
    booking = get_object_or_404(Booking, booking_id=booking_id)
    if booking.customer != request.user and not request.user.is_staff:
        raise Http404()

    if not booking.pdf_ticket or not os.path.exists(os.path.join(settings.MEDIA_ROOT, booking.pdf_ticket.name)):
        generate_ticket_pdf(booking)

    file_path = os.path.join(settings.MEDIA_ROOT, booking.pdf_ticket.name)
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="BusGo_Ticket_{booking.booking_id}.pdf"'
        return response


@login_required
def cancel_booking_view(request, booking_id):
    """
    Handles ticket cancellation and refund calculation according to BusGo policy.
    """
    booking = get_object_or_404(
        Booking.objects.select_related('schedule', 'schedule__route', 'customer'),
        booking_id=booking_id
    )

    if booking.customer != request.user and not request.user.is_staff:
        raise Http404("Booking not found.")

    if booking.booking_status == 'cancelled':
        messages.info(request, "This booking has already been cancelled.")
        return redirect('accounts:dashboard')

    cancellation_fee, refund_amount, fee_pct = calculate_refund_amount(booking)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'Cancelled by customer')
        
        with transaction.atomic():
            booking.booking_status = 'cancelled'
            booking.save()

            # Release seats
            seat_ids = booking.passengers.values_list('seat_id', flat=True)
            ScheduleSeatStatus.objects.filter(
                schedule=booking.schedule,
                seat_id__in=seat_ids
            ).update(status='available', locked_by=None, locked_until=None)

            # Record cancellation
            cancellation = Cancellation.objects.create(
                booking=booking,
                reason=reason,
                cancellation_fee=cancellation_fee,
                refund_amount=refund_amount,
                cancelled_by=request.user
            )

            # Record refund as store credit (payment method: store_credit)
            refund = Refund.objects.create(
                cancellation=cancellation,
                amount=refund_amount,
                status='processed',
                payment_method='store_credit'
            )

            # Credit user's store credit balance (separate field on CustomerProfile)
            profile, _ = CustomerProfile.objects.get_or_create(user=booking.customer)
            if not hasattr(profile, 'store_credit'):
                # Add store_credit attribute dynamically for older profiles
                profile.store_credit = Decimal('0.00')
            profile.store_credit = getattr(profile, 'store_credit', Decimal('0.00')) + Decimal(str(refund_amount))
            profile.save()

            # Send notifications
            notify_user(
                user=booking.customer,
                title="Booking Cancelled & Refund Processed",
                message=(
                    f"Booking {booking.booking_id} for "
                    f"{booking.schedule.route.origin.name} to "
                    f"{booking.schedule.route.destination.name} on "
                    f"{booking.schedule.departure_date:%d %b %Y} was cancelled. "
                    f"Cancellation reason: {reason}. "
                    f"Cancellation fee: ₹{cancellation_fee}. "
                    f"Refund of ₹{refund_amount} has been added to your store credit."
                ),
                notification_type='cancellation',
                link=f"/bookings/ticket/{booking.booking_id}/"
            )

        messages.success(request, f"Booking cancelled. ₹{refund_amount} added to your store credit.")
        return redirect('accounts:dashboard')

    context = {
        'booking': booking,
        'cancellation_fee': cancellation_fee,
        'refund_amount': refund_amount,
        'fee_pct': fee_pct,
    }
    return render(request, 'bookings/cancel.html', context)
