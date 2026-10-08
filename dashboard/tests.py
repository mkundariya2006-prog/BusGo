import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from buses.models import Bus, BusType, Seat
from bookings.models import Booking, Passenger
from operators.models import BusOperator
from routes.models import BusSchedule, City, Route


class AdminCancelScheduleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='scheduleadmin',
            email='admin@example.com',
            password='test-password',
        )
        operator_user = User.objects.create_user(
            username='scheduleoperator',
            password='test-password',
        )
        operator = BusOperator.objects.create(
            user=operator_user,
            company_name='Schedule Test Travels',
            registration_number='SCHEDULE-TEST-001',
            contact_email='operator@example.com',
            contact_phone='1234567890',
            address='Test address',
            city='Ahmedabad',
            state='Gujarat',
        )
        bus_type = BusType.objects.create(name='Test bus')
        bus = Bus.objects.create(
            operator=operator,
            bus_type=bus_type,
            bus_name='Test bus',
            bus_number='GJ-TEST-SCHEDULE',
        )
        origin = City.objects.create(name='Schedule Test Origin')
        destination = City.objects.create(name='Schedule Test Destination')
        route = Route.objects.create(origin=origin, destination=destination)
        self.schedule = BusSchedule.objects.create(
            bus=bus,
            route=route,
            departure_date=datetime.date(2026, 11, 1),
            departure_time=datetime.time(9, 0),
            arrival_date=datetime.date(2026, 11, 1),
            arrival_time=datetime.time(14, 0),
            base_price=Decimal('500.00'),
        )
        self.cancel_url = reverse(
            'dashboard:admin_cancel_schedule',
            args=[self.schedule.pk],
        )

    def test_admin_can_cancel_scheduled_bus(self):
        self.client.force_login(self.admin)

        response = self.client.post(self.cancel_url)

        self.assertRedirects(response, reverse('dashboard:admin_schedules'))
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.status, 'cancelled')

    def test_cancelling_schedule_emails_each_affected_customer_once(self):
        customer = User.objects.create_user(
            username='schedulecustomer',
            email='customer@example.com',
            password='test-password',
        )
        bookings = [
            Booking.objects.create(
                booking_id=f'BG-CANCEL-{index}',
                customer=customer,
                schedule=self.schedule,
                total_seats=1,
                base_fare=Decimal('500.00'),
                total_amount=Decimal('500.00'),
                booking_status='confirmed',
                contact_email=customer.email,
                contact_phone='1234567890',
            )
            for index in (1, 2)
        ]
        self.client.force_login(self.admin)

        response = self.client.post(self.cancel_url)

        self.assertRedirects(response, reverse('dashboard:admin_schedules'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [customer.email])
        self.assertIn('bus cancellation', mail.outbox[0].subject)
        self.assertIn('Please book another available bus', mail.outbox[0].body)
        self.assertIn('refund will be credited to your original payment method within 3-4 working days', mail.outbox[0].body)
        for booking in bookings:
            self.assertIn(booking.booking_id, mail.outbox[0].body)
            booking.refresh_from_db()
            self.assertEqual(booking.booking_status, 'confirmed')

    def test_cancellation_email_includes_passenger_and_booking_contact_addresses(self):
        customer = User.objects.create_user(
            username='passengercustomer',
            email='account@example.com',
            password='test-password',
        )
        booking = Booking.objects.create(
            booking_id='BG-PASSENGER-1',
            customer=customer,
            schedule=self.schedule,
            total_seats=1,
            base_fare=Decimal('500.00'),
            total_amount=Decimal('500.00'),
            booking_status='confirmed',
            contact_email='booking-contact@example.com',
            contact_phone='1234567890',
        )
        seat = Seat.objects.create(
            bus=self.schedule.bus,
            seat_number='A1',
        )
        Passenger.objects.create(
            booking=booking,
            seat=seat,
            name='Bus Passenger',
            age=30,
            gender='other',
            email='passenger@example.com',
            seat_fare=Decimal('500.00'),
        )
        self.client.force_login(self.admin)

        response = self.client.post(self.cancel_url)

        self.assertRedirects(response, reverse('dashboard:admin_schedules'))
        sent_to = {message.to[0] for message in mail.outbox}
        self.assertEqual(
            sent_to,
            {
                'account@example.com',
                'booking-contact@example.com',
                'passenger@example.com',
            },
        )
        passenger_email = next(
            message for message in mail.outbox
            if message.to == ['passenger@example.com']
        )
        self.assertIn('BG-PASSENGER-1', passenger_email.body)
        self.assertIn('3-4 working days', passenger_email.body)

    def test_admin_schedule_list_shows_cancel_action(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:admin_schedules'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cancel Bus')

    def test_admin_schedule_list_starts_with_today_and_paginates_all_upcoming(self):
        departure_cutoff = timezone.localtime(timezone.now() + datetime.timedelta(hours=2))
        today = departure_cutoff.date()
        self.schedule.departure_date = today - datetime.timedelta(days=1)
        self.schedule.save(update_fields=['departure_date'])
        for day_offset in range(51):
            departure_date = today + datetime.timedelta(days=day_offset)
            BusSchedule.objects.create(
                bus=self.schedule.bus,
                route=self.schedule.route,
                departure_date=departure_date,
                departure_time=(
                    (departure_cutoff + datetime.timedelta(minutes=1)).time()
                    if day_offset == 0 else datetime.time(9, 0)
                ),
                arrival_date=departure_date,
                arrival_time=datetime.time(14, 0),
                base_price=Decimal('500.00'),
            )
        self.client.force_login(self.admin)

        first_page_response = self.client.get(reverse('dashboard:admin_schedules'))

        self.assertEqual(first_page_response.status_code, 200)
        first_page = first_page_response.context['schedules']
        self.assertEqual(first_page.paginator.count, 51)
        self.assertEqual(len(first_page.object_list), 50)
        self.assertEqual(first_page.object_list[0].departure_date, today)
        self.assertTrue(first_page.has_next())
        self.assertTrue(all(
            schedule.departure_date > today or (
                schedule.departure_date == today and
                schedule.departure_time >= departure_cutoff.time()
            )
            for schedule in first_page.object_list
        ))

        second_page_response = self.client.get(
            reverse('dashboard:admin_schedules'),
            {'page': 2},
        )
        second_page = second_page_response.context['schedules']
        self.assertEqual(len(second_page.object_list), 1)
        self.assertEqual(
            second_page.object_list[0].departure_date,
            today + datetime.timedelta(days=50),
        )

    def test_admin_schedule_list_can_filter_for_a_specific_date(self):
        departure_cutoff = timezone.localtime(timezone.now() + datetime.timedelta(hours=2))
        today = departure_cutoff.date()
        target_schedule = BusSchedule.objects.create(
            bus=self.schedule.bus,
            route=self.schedule.route,
            departure_date=today,
            departure_time=(departure_cutoff + datetime.timedelta(minutes=1)).time(),
            arrival_date=today,
            arrival_time=datetime.time(14, 0),
            base_price=Decimal('500.00'),
        )
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('dashboard:admin_schedules'),
            {'date': today.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context['schedules'].object_list),
            [target_schedule],
        )

    def test_admin_schedule_list_hides_today_departures_before_two_hour_cutoff(self):
        departure_cutoff = timezone.localtime(timezone.now() + datetime.timedelta(hours=2))
        today = departure_cutoff.date()
        before_cutoff = BusSchedule.objects.create(
            bus=self.schedule.bus,
            route=self.schedule.route,
            departure_date=today,
            departure_time=(departure_cutoff - datetime.timedelta(minutes=1)).time(),
            arrival_date=today,
            arrival_time=datetime.time(23, 59),
            base_price=Decimal('500.00'),
        )
        at_cutoff = BusSchedule.objects.create(
            bus=self.schedule.bus,
            route=self.schedule.route,
            departure_date=today,
            departure_time=(departure_cutoff + datetime.timedelta(minutes=1)).time(),
            arrival_date=today,
            arrival_time=datetime.time(23, 59),
            base_price=Decimal('500.00'),
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard:admin_schedules'))
        filtered_response = self.client.get(
            reverse('dashboard:admin_schedules'),
            {'date': today.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(filtered_response.status_code, 200)
        for page_response in (response, filtered_response):
            listed_schedules = list(page_response.context['schedules'].object_list)
            self.assertNotIn(before_cutoff, listed_schedules)
            self.assertIn(at_cutoff, listed_schedules)

    def test_schedule_cancellation_requires_post(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.cancel_url)

        self.assertEqual(response.status_code, 405)
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.status, 'scheduled')

    def test_completed_bus_cannot_be_cancelled(self):
        self.client.force_login(self.admin)
        self.schedule.status = 'completed'
        self.schedule.save(update_fields=['status'])

        self.client.post(self.cancel_url)

        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.status, 'completed')

# Create your tests here.
