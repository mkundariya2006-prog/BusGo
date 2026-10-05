import json
from decimal import Decimal
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.serializers import ModelSerializer, SerializerMethodField, CharField, IntegerField, EmailField

from accounts.models import CustomerProfile
from buses.models import Bus, BusType, Seat
from routes.models import City, Route, BusSchedule
from bookings.models import Booking, Passenger, ScheduleSeatStatus, Cancellation, Refund
from payments.models import Payment
from bookings.utils import generate_booking_qr, generate_ticket_pdf, calculate_refund_amount

# Serializers
class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class CitySerializer(ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'

class RouteSerializer(ModelSerializer):
    origin = CitySerializer()
    destination = CitySerializer()
    class Meta:
        model = Route
        fields = '__all__'

class BusSerializer(ModelSerializer):
    operator_name = CharField(source='operator.company_name', read_only=True)
    bus_type_name = CharField(source='bus_type.name', read_only=True)
    class Meta:
        model = Bus
        fields = '__all__'

class BusScheduleSerializer(ModelSerializer):
    bus = BusSerializer()
    route = RouteSerializer()
    duration = CharField(source='duration_display', read_only=True)
    class Meta:
        model = BusSchedule
        fields = '__all__'

class PassengerSerializer(ModelSerializer):
    seat_number = CharField(source='seat.seat_number', read_only=True)
    class Meta:
        model = Passenger
        fields = ['id', 'name', 'age', 'gender', 'seat_number', 'id_type', 'id_number', 'seat_fare']

class BookingSerializer(ModelSerializer):
    passengers = PassengerSerializer(many=True, read_only=True)
    bus_name = CharField(source='schedule.bus.bus_name', read_only=True)
    route_name = SerializerMethodField()

    def get_route_name(self, obj):
        return f"{obj.schedule.route.origin.name} → {obj.schedule.route.destination.name}"

    class Meta:
        model = Booking
        fields = '__all__'


# API Views
class AuthLoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return Response({
                'status': 'success',
                'user': UserSerializer(user).data,
                'role': 'admin' if user.is_staff else ('operator' if hasattr(user, 'operator_profile') else 'customer')
            })
        return Response({'status': 'error', 'message': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class AuthRegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')
        phone = request.data.get('phone_number', '')

        if not username or not password or not email:
            return Response({'status': 'error', 'message': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'status': 'error', 'message': 'Username already taken'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, email=email, password=password)
        CustomerProfile.objects.create(user=user, phone_number=phone)
        login(request, user)
        return Response({'status': 'success', 'user': UserSerializer(user).data}, status=status.HTTP_201_CREATED)


class BusSearchAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        origin = request.query_params.get('origin', '')
        dest = request.query_params.get('destination', '')
        date = request.query_params.get('date', timezone.localdate().strftime('%Y-%m-%d'))

        schedules = BusSchedule.objects.filter(departure_date=date, status='scheduled')
        if origin:
            schedules = schedules.filter(route__origin__name__icontains=origin)
        if dest:
            schedules = schedules.filter(route__destination__name__icontains=dest)

        serializer = BusScheduleSerializer(schedules, many=True)
        return Response({'count': schedules.count(), 'results': serializer.data})


class BusDetailAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, id):
        bus = get_object_or_404(Bus, id=id)
        return Response(BusSerializer(bus).data)


class CitiesListAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        district = request.query_params.get('district', '').strip()
        is_pop = request.query_params.get('popular')

        cities = City.objects.all()
        if query:
            cities = cities.filter(name__icontains=query)
        if district:
            cities = cities.filter(district__icontains=district)
        if is_pop is not None:
            cities = cities.filter(is_popular=(is_pop.lower() in ['true', '1']))

        cities = cities.order_by('name')
        return Response({
            'count': cities.count(),
            'state': 'Gujarat',
            'results': CitySerializer(cities, many=True).data
        })


class RoutesListAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        routes = Route.objects.filter(is_active=True)
        return Response(RouteSerializer(routes, many=True).data)


class SchedulesListAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        schedules = BusSchedule.objects.filter(status='scheduled')[:50]
        return Response(BusScheduleSerializer(schedules, many=True).data)


class ScheduleSeatsAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, schedule_id):
        schedule = get_object_or_404(BusSchedule, id=schedule_id)
        seats = schedule.bus.seats.all()
        statuses = {ss.seat_id: ss.get_effective_status() for ss in ScheduleSeatStatus.objects.filter(schedule=schedule)}

        results = []
        for s in seats:
            results.append({
                'id': s.id,
                'seat_number': s.seat_number,
                'deck': s.deck,
                'seat_type': s.seat_type,
                'row': s.row,
                'column': s.column,
                'is_ladies_only': s.is_ladies_only,
                'price': float(schedule.base_price * s.price_multiplier),
                'status': statuses.get(s.id, 'available'),
            })
        return Response({'schedule_id': schedule.id, 'seats': results})


class BookingsListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.filter(customer=request.user).order_by('-created_at')
        return Response(BookingSerializer(bookings, many=True).data)

    def post(self, request):
        schedule_id = request.data.get('schedule_id')
        seat_ids = request.data.get('seat_ids', [])
        passengers_data = request.data.get('passengers', [])

        schedule = get_object_or_404(BusSchedule, id=schedule_id)
        seats = Seat.objects.filter(id__in=seat_ids, bus=schedule.bus)

        if len(seats) != len(seat_ids):
            return Response({'status': 'error', 'message': 'Invalid seats'}, status=status.HTTP_400_BAD_REQUEST)

        # Lock seats
        try:
            ScheduleSeatStatus.lock_seats(schedule, seat_ids, request.user, duration_minutes=10)
        except ValueError as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_409_CONFLICT)

        base_fare = sum([schedule.base_price * s.price_multiplier for s in seats])
        tax = round(base_fare * Decimal('0.05'), 2)
        total = base_fare + tax + Decimal('20.00')

        with transaction.atomic():
            booking = Booking.objects.create(
                customer=request.user,
                schedule=schedule,
                total_seats=len(seats),
                base_fare=base_fare,
                tax_amount=tax,
                convenience_fee=Decimal('20.00'),
                total_amount=total,
                booking_status='pending',
                contact_email=request.data.get('contact_email', request.user.email),
                contact_phone=request.data.get('contact_phone', ''),
            )

            for idx, p in enumerate(passengers_data):
                seat = seats[idx]
                Passenger.objects.create(
                    booking=booking,
                    seat=seat,
                    name=p.get('name', f'Passenger {idx+1}'),
                    age=p.get('age', 25),
                    gender=p.get('gender', 'male'),
                    id_type=p.get('id_type', 'aadhaar'),
                    id_number=p.get('id_number', ''),
                    seat_fare=schedule.base_price * seat.price_multiplier
                )

        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id):
        booking = get_object_or_404(Booking, id=id)
        if booking.customer != request.user and not request.user.is_staff:
            return Response({'status': 'error', 'message': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return Response(BookingSerializer(booking).data)


class BookingCancelAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        booking = get_object_or_404(Booking, id=id)
        if booking.customer != request.user and not request.user.is_staff:
            return Response({'status': 'error', 'message': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        if booking.booking_status == 'cancelled':
            return Response({'status': 'error', 'message': 'Already cancelled'}, status=status.HTTP_400_BAD_REQUEST)

        fee, refund_amt, _ = calculate_refund_amount(booking)

        with transaction.atomic():
            booking.booking_status = 'cancelled'
            booking.save()

            seat_ids = booking.passengers.values_list('seat_id', flat=True)
            ScheduleSeatStatus.objects.filter(schedule=booking.schedule, seat_id__in=seat_ids).update(
                status='available', locked_by=None, locked_until=None
            )

            cancellation = Cancellation.objects.create(
                booking=booking,
                reason=request.data.get('reason', 'API Cancellation'),
                cancellation_fee=fee,
                refund_amount=refund_amt,
                cancelled_by=request.user
            )
            Refund.objects.create(
                cancellation=cancellation,
                amount=refund_amt,
                status='processed'
            )

        return Response({
            'status': 'cancelled',
            'cancellation_fee': fee,
            'refund_amount': refund_amt,
        })


class PaymentCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        booking_id = request.data.get('booking_id')
        method = request.data.get('payment_method', 'upi')
        booking = get_object_or_404(Booking, booking_id=booking_id)

        with transaction.atomic():
            payment, _ = Payment.objects.get_or_create(
                booking=booking,
                defaults={'amount': booking.total_amount, 'payment_method': method}
            )
            payment.status = 'success'
            payment.paid_at = timezone.now()
            payment.save()

            booking.booking_status = 'confirmed'
            booking.save()

            # Mark seats booked
            for p in booking.passengers.all():
                ss = ScheduleSeatStatus.objects.filter(schedule=booking.schedule, seat=p.seat).first()
                if ss:
                    ss.status = 'booked'
                    ss.locked_by = None
                    ss.locked_until = None
                    ss.save()

            generate_booking_qr(booking)
            generate_ticket_pdf(booking)

        return Response({'status': 'success', 'booking_id': booking.booking_id, 'payment_id': payment.transaction_id})


class TicketDetailAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, booking_id):
        booking = get_object_or_404(Booking, booking_id=booking_id)
        return Response({
            'booking_id': booking.booking_id,
            'status': booking.booking_status,
            'route': f"{booking.schedule.route.origin.name} to {booking.schedule.route.destination.name}",
            'departure': f"{booking.schedule.departure_date} {booking.schedule.departure_time}",
            'bus': f"{booking.schedule.bus.bus_name} ({booking.schedule.bus.bus_number})",
            'seats': booking.seat_numbers_display,
            'total_amount': float(booking.total_amount),
            'qr_code_url': booking.qr_code_image.url if booking.qr_code_image else None,
            'pdf_url': booking.pdf_ticket.url if booking.pdf_ticket else None,
        })
