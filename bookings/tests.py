import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import CustomerProfile
from operators.models import BusOperator
from buses.models import BusType, Bus, Seat
from routes.models import City, Route, BusSchedule, BoardingPoint, DroppingPoint
from bookings.models import ScheduleSeatStatus, Booking, Passenger, Cancellation, Refund
from payments.models import Payment
from bookings.utils import generate_booking_qr, generate_ticket_pdf, calculate_refund_amount

class BusGoSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.user = User.objects.create_user(
            username='testcustomer',
            email='test@example.com',
            password='Password123'
        )
        self.profile = CustomerProfile.objects.create(
            user=self.user,
            phone_number='+91 99999 88888',
            wallet_balance=Decimal('5000.00')
        )

        self.user2 = User.objects.create_user(
            username='testcustomer2',
            email='test2@example.com',
            password='Password123'
        )

        self.operator_user = User.objects.create_user(
            username='testoperator',
            email='op@example.com',
            password='Password123'
        )
        self.operator = BusOperator.objects.create(
            user=self.operator_user,
            company_name='Test Gujarat Travels',
            registration_number='GJ-TEST-001',
            contact_email='op@example.com',
            contact_phone='+91 79 1234 5678',
            city='Ahmedabad',
            state='Gujarat'
        )

        # Bus Type, Bus, Seats
        self.bus_type = BusType.objects.create(
            name='Volvo AC Sleeper',
            category='sleeper',
            is_ac=True,
            has_upper_deck=True,
            total_seats=2
        )
        self.bus = Bus.objects.create(
            operator=self.operator,
            bus_type=self.bus_type,
            bus_name='Test Volvo Express',
            bus_number='GJ-01-TEST-1234'
        )
        self.seat1 = Seat.objects.create(bus=self.bus, seat_number='L1', deck='lower', row=1, column=1)
        self.seat2 = Seat.objects.create(bus=self.bus, seat_number='L2', deck='lower', row=1, column=2, is_ladies_only=True)

        # Cities & Route (Gujarat)
        self.city_origin = City.objects.create(name='Ahmedabad', state='Gujarat')
        self.city_dest = City.objects.create(name='Surat', state='Gujarat')
        self.route = Route.objects.create(
            origin=self.city_origin,
            destination=self.city_dest,
            distance_km=265,
            estimated_duration_hours=4.5
        )
        self.bp = BoardingPoint.objects.create(route=self.route, city=self.city_origin, location_name='Paldi Cross Road')
        self.dp = DroppingPoint.objects.create(route=self.route, city=self.city_dest, location_name='Kamrej Toll Plaza')

        # Schedule for tomorrow
        self.tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        self.schedule = BusSchedule.objects.create(
            bus=self.bus,
            route=self.route,
            departure_date=self.tomorrow,
            departure_time=datetime.time(20, 0),
            arrival_date=self.tomorrow + datetime.timedelta(days=1),
            arrival_time=datetime.time(6, 0),
            base_price=Decimal('1000.00'),
            status='scheduled'
        )

        # Initialize seat statuses
        self.ss1 = ScheduleSeatStatus.objects.create(schedule=self.schedule, seat=self.seat1, status='available')
        self.ss2 = ScheduleSeatStatus.objects.create(schedule=self.schedule, seat=self.seat2, status='available')

    def test_user_registration_and_login(self):
        """Test user registration and login flow"""
        res = self.client.post('/accounts/register/', {
            'username': 'newuser123',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@example.com',
            'phone_number': '+91 88888 77777',
            'gender': 'male',
            'password': 'StrongPassword123',
            'confirm_password': 'StrongPassword123'
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser123').exists())

        # Test login
        self.client.logout()
        login_res = self.client.post('/accounts/login/', {
            'username': 'newuser123',
            'password': 'StrongPassword123'
        })
        self.assertEqual(login_res.status_code, 302)

    def test_bus_search(self):
        """Test bus search endpoint with origin, destination, and date"""
        response = self.client.get('/buses/search/', {
            'origin': 'Ahmedabad',
            'destination': 'Surat',
            'date': self.tomorrow.strftime('%Y-%m-%d')
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Volvo Express')

    def test_seat_locking_and_double_booking_prevention(self):
        """Test concurrency safe seat locking and double-booking prevention"""
        # User 1 locks seat 1
        locked_seats = ScheduleSeatStatus.lock_seats(self.schedule, [self.seat1.id], self.user, duration_minutes=10)
        self.assertEqual(len(locked_seats), 1)
        self.assertEqual(locked_seats[0].status, 'locked')
        self.assertEqual(locked_seats[0].locked_by, self.user)

        # User 2 attempts to lock the same seat -> must raise ValueError!
        with self.assertRaises(ValueError):
            ScheduleSeatStatus.lock_seats(self.schedule, [self.seat1.id], self.user2, duration_minutes=10)

    def test_booking_payment_and_ticket_generation(self):
        """Test complete booking, payment simulation, and QR/PDF ticket generation"""
        self.client.force_login(self.user)

        # Step 1: Create booking
        booking = Booking.objects.create(
            customer=self.user,
            schedule=self.schedule,
            boarding_point=self.bp,
            dropping_point=self.dp,
            total_seats=1,
            base_fare=Decimal('1000.00'),
            tax_amount=Decimal('50.00'),
            convenience_fee=Decimal('20.00'),
            total_amount=Decimal('1070.00'),
            booking_status='pending',
            contact_email=self.user.email,
            contact_phone=self.profile.phone_number
        )
        Passenger.objects.create(
            booking=booking,
            seat=self.seat1,
            name='Test Traveler',
            age=29,
            gender='male',
            seat_fare=Decimal('1000.00')
        )

        # Step 2: Payment
        pay_res = self.client.post(f'/bookings/payment/{booking.booking_id}/', {
            'payment_method': 'wallet',
            'action': 'pay_success'
        })
        self.assertEqual(pay_res.status_code, 302)

        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 'confirmed')

        # Check QR code and PDF generation
        self.assertTrue(bool(booking.qr_code_image))
        self.assertTrue(bool(booking.pdf_ticket))

        # Check seat marked booked
        self.ss1.refresh_from_db()
        self.assertEqual(self.ss1.status, 'booked')

    def test_cancellation_and_refund_calculation(self):
        """Test cancellation and refund calculation policy"""
        # Booking more than 24h away
        booking = Booking.objects.create(
            customer=self.user,
            schedule=self.schedule,
            total_seats=1,
            base_fare=Decimal('1000.00'),
            tax_amount=Decimal('50.00'),
            convenience_fee=Decimal('20.00'),
            total_amount=Decimal('1070.00'),
            booking_status='confirmed',
            contact_email=self.user.email,
            contact_phone=self.profile.phone_number
        )
        Passenger.objects.create(
            booking=booking,
            seat=self.seat1,
            name='Test Traveler',
            age=29,
            gender='male',
            seat_fare=Decimal('1000.00')
        )

        fee, refund_amt, fee_pct = calculate_refund_amount(booking)
        # > 24 hours -> 10% fee, 90% refund
        self.assertEqual(fee_pct, 10)
        self.assertEqual(fee, round(1070.00 * 0.10, 2))
        self.assertEqual(refund_amt, round(1070.00 * 0.90, 2))

        # Test cancellation execution
        self.client.force_login(self.user)
        cancel_res = self.client.post(f'/bookings/cancel/{booking.booking_id}/', {
            'reason': 'Change of plans'
        })
        self.assertEqual(cancel_res.status_code, 302)

        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, 'cancelled')

        # Verify seat released back to available
        self.ss1.refresh_from_db()
        self.assertEqual(self.ss1.status, 'available')
