import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import CustomerProfile, SavedPassenger
from operators.models import BusOperator
from buses.models import BusType, Bus, Seat
from routes.models import City, Route, BoardingPoint, DroppingPoint, BusSchedule
from bookings.models import ScheduleSeatStatus, Booking, Passenger
from payments.models import Payment
from bookings.utils import generate_booking_qr, generate_ticket_pdf

class Command(BaseCommand):
    help = 'Seeds sample data exclusively for Gujarat routes, cities, and operators'

    def handle(self, *args, **options):
        self.stdout.write("Starting BusGo Gujarat data seeding...")

        # 1. Superuser / Admin
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@busgo.com',
                'first_name': 'Gujarat Admin',
                'last_name': 'Desk',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write("Created Admin user: admin / admin123")

        # 2. Operator User
        operator_user, created = User.objects.get_or_create(
            username='operator',
            defaults={
                'email': 'operator@gujaratexpress.com',
                'first_name': 'Ketan',
                'last_name': 'Patel',
                'is_staff': False,
            }
        )
        if created:
            operator_user.set_password('operator123')
            operator_user.save()
            self.stdout.write("Created Operator user: operator / operator123")

        # 3. Customer User
        customer_user, created = User.objects.get_or_create(
            username='customer',
            defaults={
                'email': 'customer@busgo.com',
                'first_name': 'Aarav',
                'last_name': 'Patel',
                'is_staff': False,
            }
        )
        if created:
            customer_user.set_password('customer123')
            customer_user.save()
            self.stdout.write("Created Customer user: customer / customer123")

        customer_profile, _ = CustomerProfile.objects.get_or_create(
            user=customer_user,
            defaults={
                'phone_number': '+91 98765 43210',
                'gender': 'male',
                'city': 'Ahmedabad',
                'state': 'Gujarat',
                'wallet_balance': 25840.50,
                'reward_points': 450,
            }
        )
        customer_profile.city = 'Ahmedabad'
        customer_profile.state = 'Gujarat'
        customer_profile.save()

        # Saved passengers for customer
        SavedPassenger.objects.get_or_create(
            customer=customer_profile,
            name='Aarav Patel',
            defaults={'age': 28, 'gender': 'male', 'id_type': 'aadhaar', 'id_number': '7894-3210-9988'}
        )
        SavedPassenger.objects.get_or_create(
            customer=customer_profile,
            name='Priya Patel',
            defaults={'age': 26, 'gender': 'female', 'id_type': 'pan', 'id_number': 'ABCPS1234F'}
        )

        # 4. Bus Operators (Top Gujarat Travel Operators)
        operators_data = [
            {
                'user': operator_user,
                'company_name': 'Gujarat Express',
                'reg_num': 'GJ-01-GE-2018',
                'email': 'contact@gujaratexpress.com',
                'phone': '+91 79 2658 9900',
                'city': 'Ahmedabad',
                'state': 'Gujarat',
                'rating': 4.85,
                'total_ratings': 420,
            },
            {
                'user': None,
                'company_name': 'Patel Tours & Travels',
                'reg_num': 'GJ-01-PT-2016',
                'email': 'support@pateltravelsgujarat.com',
                'phone': '+91 79 2640 1122',
                'city': 'Ahmedabad',
                'state': 'Gujarat',
                'rating': 4.75,
                'total_ratings': 380,
            },
            {
                'user': None,
                'company_name': 'Shree Sahjanand Travels',
                'reg_num': 'GJ-04-ST-2017',
                'email': 'info@sahjanandtravels.in',
                'phone': '+91 278 251 3344',
                'city': 'Bhavnagar',
                'state': 'Gujarat',
                'rating': 4.70,
                'total_ratings': 310,
            },
            {
                'user': None,
                'company_name': 'Jay Khodiyar Travels',
                'reg_num': 'GJ-05-JK-2019',
                'email': 'booking@jaykhodiyarbus.com',
                'phone': '+91 261 254 7788',
                'city': 'Surat',
                'state': 'Gujarat',
                'rating': 4.65,
                'total_ratings': 290,
            },
            {
                'user': None,
                'company_name': 'Eagle Falcon Travels',
                'reg_num': 'GJ-03-EF-2015',
                'email': 'help@eaglebusgujarat.com',
                'phone': '+91 281 246 8899',
                'city': 'Rajkot',
                'state': 'Gujarat',
                'rating': 4.80,
                'total_ratings': 450,
            },
            {
                'user': None,
                'company_name': 'Shree Roadways Gujarat',
                'reg_num': 'GJ-05-SR-2020',
                'email': 'contact@shreeroadwaysgujarat.com',
                'phone': '+91 261 255 1100',
                'city': 'Surat',
                'state': 'Gujarat',
                'rating': 4.55,
                'total_ratings': 210,
            }
        ]

        operators_dict = {}
        for op in operators_data:
            op_user = op['user']
            if not op_user:
                u_name = op['company_name'].lower().replace(' ', '_').replace('&', 'and')
                op_user, _ = User.objects.get_or_create(
                    username=u_name,
                    defaults={'email': op['email'], 'first_name': op['company_name'], 'is_staff': False}
                )
                op_user.set_password('operator123')
                op_user.save()

            b_op, _ = BusOperator.objects.get_or_create(
                company_name=op['company_name'],
                defaults={
                    'user': op_user,
                    'registration_number': op['reg_num'],
                    'contact_email': op['email'],
                    'contact_phone': op['phone'],
                    'address': f"Head Office, {op['city']}, Gujarat",
                    'city': op['city'],
                    'state': op['state'],
                    'status': 'approved',
                    'rating': op['rating'],
                    'total_ratings': op['total_ratings'],
                }
            )
            operators_dict[op['company_name']] = b_op

        # 5. Bus Types
        types_data = [
            {
                'name': 'Volvo 9600 Multi-Axle AC Sleeper (2+1)',
                'category': 'sleeper',
                'is_ac': True,
                'has_upper_deck': True,
                'total_seats': 30,
                'layout_type': '2+1'
            },
            {
                'name': 'Mercedes-Benz Multi-Axle Semi-Sleeper (2+2)',
                'category': 'semi_sleeper',
                'is_ac': True,
                'has_upper_deck': False,
                'total_seats': 36,
                'layout_type': '2+2'
            },
            {
                'name': 'Scania Metrolink AC Seater/Sleeper (2+1)',
                'category': 'seater_sleeper',
                'is_ac': True,
                'has_upper_deck': True,
                'total_seats': 30,
                'layout_type': '2+1'
            },
            {
                'name': 'BharatBenz Luxury AC Sleeper (2+1)',
                'category': 'sleeper',
                'is_ac': True,
                'has_upper_deck': True,
                'total_seats': 30,
                'layout_type': '2+1'
            },
            {
                'name': 'Ashok Leyland 2+2 Executive Non-AC Seater',
                'category': 'seater',
                'is_ac': False,
                'has_upper_deck': False,
                'total_seats': 36,
                'layout_type': '2+2'
            },
        ]

        types_dict = {}
        for td in types_data:
            bt, _ = BusType.objects.get_or_create(
                name=td['name'],
                defaults=td
            )
            types_dict[td['name']] = bt

        # 6. Cities (Only proper cities & towns — No villages)
        #    Includes: District HQs, Taluka HQs, Municipalities, Nagar Palikas,
        #    Industrial Towns, Tourist/Pilgrimage Centers
        gujarat_cities = [
            # 1. Ahmedabad District
            ('Ahmedabad', 'Ahmedabad', 'Gujarat', True),
            ('Sanand', 'Ahmedabad', 'Gujarat', False),
            ('Viramgam', 'Ahmedabad', 'Gujarat', False),
            ('Dholka', 'Ahmedabad', 'Gujarat', False),
            ('Dhandhuka', 'Ahmedabad', 'Gujarat', False),
            ('Bavla', 'Ahmedabad', 'Gujarat', False),

            # 2. Surat District
            ('Surat', 'Surat', 'Gujarat', True),
            ('Bardoli', 'Surat', 'Gujarat', False),
            ('Kamrej', 'Surat', 'Gujarat', False),
            ('Kadodara', 'Surat', 'Gujarat', False),

            # 3. Vadodara District
            ('Vadodara', 'Vadodara', 'Gujarat', True),
            ('Padra', 'Vadodara', 'Gujarat', False),
            ('Dabhoi', 'Vadodara', 'Gujarat', False),
            ('Karjan', 'Vadodara', 'Gujarat', False),
            ('Savli', 'Vadodara', 'Gujarat', False),

            # 4. Rajkot District
            ('Rajkot', 'Rajkot', 'Gujarat', True),
            ('Gondal', 'Rajkot', 'Gujarat', True),
            ('Jetpur', 'Rajkot', 'Gujarat', False),
            ('Dhoraji', 'Rajkot', 'Gujarat', False),
            ('Upleta', 'Rajkot', 'Gujarat', False),
            ('Jasdan', 'Rajkot', 'Gujarat', False),

            # 5. Bhavnagar District
            ('Bhavnagar', 'Bhavnagar', 'Gujarat', True),
            ('Palitana', 'Bhavnagar', 'Gujarat', True),
            ('Mahuva', 'Bhavnagar', 'Gujarat', False),
            ('Talaja', 'Bhavnagar', 'Gujarat', False),
            ('Sihor', 'Bhavnagar', 'Gujarat', False),
            ('Vallabhipur', 'Bhavnagar', 'Gujarat', False),

            # 6. Jamnagar District
            ('Jamnagar', 'Jamnagar', 'Gujarat', True),
            ('Dhrol', 'Jamnagar', 'Gujarat', False),
            ('Kalavad', 'Jamnagar', 'Gujarat', False),
            ('Jamjodhpur', 'Jamnagar', 'Gujarat', False),

            # 7. Gandhinagar District
            ('Gandhinagar', 'Gandhinagar', 'Gujarat', True),
            ('Kalol', 'Gandhinagar', 'Gujarat', False),
            ('Dehgam', 'Gandhinagar', 'Gujarat', False),
            ('Mansa', 'Gandhinagar', 'Gujarat', False),

            # 8. Junagadh District
            ('Junagadh', 'Junagadh', 'Gujarat', True),
            ('Keshod', 'Junagadh', 'Gujarat', False),
            ('Mangrol', 'Junagadh', 'Gujarat', False),
            ('Manavadar', 'Junagadh', 'Gujarat', False),
            ('Visavadar', 'Junagadh', 'Gujarat', False),

            # 9. Kutch District
            ('Bhuj', 'Kutch', 'Gujarat', True),
            ('Gandhidham', 'Kutch', 'Gujarat', True),
            ('Anjar', 'Kutch', 'Gujarat', False),
            ('Mandvi (Kutch)', 'Kutch', 'Gujarat', True),
            ('Mundra', 'Kutch', 'Gujarat', False),
            ('Bhachau', 'Kutch', 'Gujarat', False),
            ('Rapar', 'Kutch', 'Gujarat', False),
            ('Nakhatrana', 'Kutch', 'Gujarat', False),

            # 10. Anand District
            ('Anand', 'Anand', 'Gujarat', True),
            ('Petlad', 'Anand', 'Gujarat', False),
            ('Khambhat', 'Anand', 'Gujarat', False),
            ('Borsad', 'Anand', 'Gujarat', False),
            ('Umreth', 'Anand', 'Gujarat', False),
            ('Vallabh Vidyanagar', 'Anand', 'Gujarat', False),

            # 11. Kheda District
            ('Nadiad', 'Kheda', 'Gujarat', True),
            ('Kapadvanj', 'Kheda', 'Gujarat', False),
            ('Kheda', 'Kheda', 'Gujarat', False),
            ('Thasra', 'Kheda', 'Gujarat', False),
            ('Dakor', 'Kheda', 'Gujarat', True),
            ('Mehmedabad', 'Kheda', 'Gujarat', False),

            # 12. Bharuch District
            ('Bharuch', 'Bharuch', 'Gujarat', True),
            ('Ankleshwar', 'Bharuch', 'Gujarat', True),
            ('Jambusar', 'Bharuch', 'Gujarat', False),
            ('Dahej', 'Bharuch', 'Gujarat', False),

            # 13. Navsari District
            ('Navsari', 'Navsari', 'Gujarat', True),
            ('Bilimora', 'Navsari', 'Gujarat', False),
            ('Gandevi', 'Navsari', 'Gujarat', False),
            ('Chikhli', 'Navsari', 'Gujarat', False),

            # 14. Valsad District
            ('Valsad', 'Valsad', 'Gujarat', True),
            ('Vapi', 'Valsad', 'Gujarat', True),
            ('Umbergaon', 'Valsad', 'Gujarat', False),
            ('Dharampur', 'Valsad', 'Gujarat', False),

            # 15. Morbi District
            ('Morbi', 'Morbi', 'Gujarat', True),
            ('Wankaner', 'Morbi', 'Gujarat', False),
            ('Halvad', 'Morbi', 'Gujarat', False),
            ('Tankara', 'Morbi', 'Gujarat', False),

            # 16. Surendranagar District
            ('Surendranagar', 'Surendranagar', 'Gujarat', True),
            ('Wadhwan', 'Surendranagar', 'Gujarat', False),
            ('Dhrangadhra', 'Surendranagar', 'Gujarat', False),
            ('Limbdi', 'Surendranagar', 'Gujarat', False),
            ('Chotila', 'Surendranagar', 'Gujarat', True),
            ('Thangadh', 'Surendranagar', 'Gujarat', False),

            # 17. Banaskantha District
            ('Palanpur', 'Banaskantha', 'Gujarat', True),
            ('Deesa', 'Banaskantha', 'Gujarat', True),
            ('Dhanera', 'Banaskantha', 'Gujarat', False),
            ('Tharad', 'Banaskantha', 'Gujarat', False),
            ('Ambaji', 'Banaskantha', 'Gujarat', True),

            # 18. Mehsana District
            ('Mehsana', 'Mehsana', 'Gujarat', True),
            ('Kadi', 'Mehsana', 'Gujarat', False),
            ('Visnagar', 'Mehsana', 'Gujarat', False),
            ('Vadnagar', 'Mehsana', 'Gujarat', True),
            ('Unjha', 'Mehsana', 'Gujarat', False),
            ('Vijapur', 'Mehsana', 'Gujarat', False),
            ('Becharaji', 'Mehsana', 'Gujarat', True),
            ('Modhera', 'Mehsana', 'Gujarat', True),

            # 19. Patan District
            ('Patan', 'Patan', 'Gujarat', True),
            ('Siddhpur', 'Patan', 'Gujarat', True),
            ('Radhanpur', 'Patan', 'Gujarat', False),
            ('Chanasma', 'Patan', 'Gujarat', False),
            ('Harij', 'Patan', 'Gujarat', False),

            # 20. Sabarkantha District
            ('Himatnagar', 'Sabarkantha', 'Gujarat', True),
            ('Idar', 'Sabarkantha', 'Gujarat', False),
            ('Prantij', 'Sabarkantha', 'Gujarat', False),
            ('Talod', 'Sabarkantha', 'Gujarat', False),
            ('Khedbrahma', 'Sabarkantha', 'Gujarat', False),

            # 21. Aravalli District
            ('Modasa', 'Aravalli', 'Gujarat', False),
            ('Bayad', 'Aravalli', 'Gujarat', False),
            ('Bhiloda', 'Aravalli', 'Gujarat', False),
            ('Shamlaji', 'Aravalli', 'Gujarat', True),

            # 22. Panchmahal District
            ('Godhra', 'Panchmahal', 'Gujarat', True),
            ('Halol', 'Panchmahal', 'Gujarat', False),
            ('Pavagadh', 'Panchmahal', 'Gujarat', True),

            # 23. Dahod District
            ('Dahod', 'Dahod', 'Gujarat', True),
            ('Jhalod', 'Dahod', 'Gujarat', False),
            ('Devgadh Baria', 'Dahod', 'Gujarat', False),

            # 24. Mahisagar District
            ('Lunawada', 'Mahisagar', 'Gujarat', False),
            ('Balasinor', 'Mahisagar', 'Gujarat', False),

            # 25. Chhota Udaipur District
            ('Chhota Udaipur', 'Chhota Udaipur', 'Gujarat', False),
            ('Bodeli', 'Chhota Udaipur', 'Gujarat', False),

            # 26. Narmada District
            ('Rajpipla', 'Narmada', 'Gujarat', False),
            ('Kevadia (Statue of Unity)', 'Narmada', 'Gujarat', True),

            # 27. Tapi District
            ('Vyara', 'Tapi', 'Gujarat', False),
            ('Songadh', 'Tapi', 'Gujarat', False),

            # 28. Dang District
            ('Ahwa', 'Dang', 'Gujarat', False),
            ('Saputara', 'Dang', 'Gujarat', True),

            # 29. Amreli District
            ('Amreli', 'Amreli', 'Gujarat', True),
            ('Savarkundla', 'Amreli', 'Gujarat', False),
            ('Rajula', 'Amreli', 'Gujarat', False),
            ('Babra', 'Amreli', 'Gujarat', False),
            ('Dhari', 'Amreli', 'Gujarat', False),

            # 30. Botad District
            ('Botad', 'Botad', 'Gujarat', True),
            ('Gadhada', 'Botad', 'Gujarat', True),
            ('Sarangpur', 'Botad', 'Gujarat', True),

            # 31. Gir Somnath District
            ('Somnath', 'Gir Somnath', 'Gujarat', True),
            ('Veraval', 'Gir Somnath', 'Gujarat', True),
            ('Kodinar', 'Gir Somnath', 'Gujarat', False),
            ('Una', 'Gir Somnath', 'Gujarat', False),
            ('Talala', 'Gir Somnath', 'Gujarat', False),
            ('Sasan Gir', 'Gir Somnath', 'Gujarat', True),

            # 32. Porbandar District
            ('Porbandar', 'Porbandar', 'Gujarat', True),
            ('Kutiyana', 'Porbandar', 'Gujarat', False),

            # 33. Devbhumi Dwarka District
            ('Dwarka', 'Devbhumi Dwarka', 'Gujarat', True),
            ('Khambhalia', 'Devbhumi Dwarka', 'Gujarat', False),
            ('Okha', 'Devbhumi Dwarka', 'Gujarat', False),
            ('Bet Dwarka', 'Devbhumi Dwarka', 'Gujarat', True),
        ]

        cities_dict = {}
        for cname, cdist, cstate, is_pop in gujarat_cities:
            c, created = City.objects.get_or_create(
                name=cname,
                defaults={'district': cdist, 'state': cstate, 'is_popular': is_pop}
            )
            if not created:
                c.district = cdist
                c.state = cstate
                c.is_popular = is_pop
                c.save()
            cities_dict[cname] = c

        self.stdout.write(f"Populated {len(gujarat_cities)} cities/towns across all 33 districts of Gujarat.")

        # 7. Routes (100% within Gujarat - Connecting major hubs and regional centers)
        routes_spec = [
            # Core Trunk Lines
            ('Ahmedabad', 'Surat', 265, 4.5),
            ('Surat', 'Ahmedabad', 265, 4.5),
            ('Ahmedabad', 'Rajkot', 215, 4.0),
            ('Rajkot', 'Ahmedabad', 215, 4.0),
            ('Ahmedabad', 'Vadodara', 110, 2.0),
            ('Vadodara', 'Ahmedabad', 110, 2.0),
            ('Vadodara', 'Surat', 155, 2.5),
            ('Surat', 'Vadodara', 155, 2.5),
            ('Ahmedabad', 'Bhavnagar', 175, 3.5),
            ('Bhavnagar', 'Ahmedabad', 175, 3.5),
            ('Ahmedabad', 'Jamnagar', 310, 5.5),
            ('Jamnagar', 'Ahmedabad', 310, 5.5),
            ('Rajkot', 'Jamnagar', 90, 1.5),
            ('Jamnagar', 'Rajkot', 90, 1.5),
            ('Ahmedabad', 'Bhuj', 335, 6.5),
            ('Bhuj', 'Ahmedabad', 335, 6.5),
            ('Surat', 'Rajkot', 430, 7.5),
            ('Rajkot', 'Surat', 430, 7.5),
            ('Ahmedabad', 'Somnath', 410, 7.5),
            ('Somnath', 'Ahmedabad', 410, 7.5),
            ('Ahmedabad', 'Dwarka', 440, 8.0),
            ('Dwarka', 'Ahmedabad', 440, 8.0),
            ('Surat', 'Bhavnagar', 360, 6.0),
            ('Ahmedabad', 'Junagadh', 320, 6.0),
            ('Junagadh', 'Ahmedabad', 320, 6.0),

            # Statue of Unity / Kevadia Routes
            ('Ahmedabad', 'Kevadia (Statue of Unity)', 195, 3.5),
            ('Kevadia (Statue of Unity)', 'Ahmedabad', 195, 3.5),
            ('Vadodara', 'Kevadia (Statue of Unity)', 90, 1.8),
            ('Kevadia (Statue of Unity)', 'Vadodara', 90, 1.8),
            ('Surat', 'Kevadia (Statue of Unity)', 155, 3.2),
            ('Kevadia (Statue of Unity)', 'Surat', 155, 3.2),

            # North Gujarat / Banaskantha / Patan / Mehsana Routes
            ('Ahmedabad', 'Ambaji', 185, 3.8),
            ('Ambaji', 'Ahmedabad', 185, 3.8),
            ('Ahmedabad', 'Palanpur', 145, 3.0),
            ('Palanpur', 'Ahmedabad', 145, 3.0),
            ('Ahmedabad', 'Mehsana', 75, 1.5),
            ('Mehsana', 'Ahmedabad', 75, 1.5),
            ('Ahmedabad', 'Patan', 125, 2.5),
            ('Patan', 'Ahmedabad', 125, 2.5),
            ('Ahmedabad', 'Gandhinagar', 28, 0.6),
            ('Gandhinagar', 'Ahmedabad', 28, 0.6),
            ('Ahmedabad', 'Himatnagar', 85, 1.7),

            # Central & South Gujarat Routes
            ('Ahmedabad', 'Anand', 75, 1.5),
            ('Anand', 'Ahmedabad', 75, 1.5),
            ('Vadodara', 'Anand', 45, 0.9),
            ('Anand', 'Vadodara', 45, 0.9),
            ('Vadodara', 'Bharuch', 75, 1.4),
            ('Bharuch', 'Vadodara', 75, 1.4),
            ('Vadodara', 'Ankleshwar', 85, 1.5),
            ('Surat', 'Bharuch', 70, 1.3),
            ('Surat', 'Ankleshwar', 60, 1.1),
            ('Surat', 'Navsari', 38, 0.8),
            ('Navsari', 'Surat', 38, 0.8),
            ('Surat', 'Valsad', 90, 1.8),
            ('Valsad', 'Surat', 90, 1.8),
            ('Surat', 'Vapi', 115, 2.2),
            ('Vapi', 'Surat', 115, 2.2),
            ('Ahmedabad', 'Vapi', 360, 6.5),
            ('Surat', 'Saputara', 160, 3.5),
            ('Saputara', 'Surat', 160, 3.5),

            # Saurashtra & Kutch Inter-Connectivity
            ('Ahmedabad', 'Morbi', 210, 4.0),
            ('Morbi', 'Ahmedabad', 210, 4.0),
            ('Ahmedabad', 'Porbandar', 390, 7.5),
            ('Porbandar', 'Ahmedabad', 390, 7.5),
            ('Ahmedabad', 'Gandhidham', 290, 5.5),
            ('Gandhidham', 'Ahmedabad', 290, 5.5),
            ('Ahmedabad', 'Mandvi (Kutch)', 390, 7.5),
            ('Mandvi (Kutch)', 'Ahmedabad', 390, 7.5),
            ('Bhuj', 'Gandhidham', 58, 1.1),
            ('Bhuj', 'Mandvi (Kutch)', 60, 1.2),
            ('Rajkot', 'Junagadh', 105, 2.0),
            ('Junagadh', 'Rajkot', 105, 2.0),
            ('Rajkot', 'Somnath', 195, 3.8),
            ('Somnath', 'Rajkot', 195, 3.8),
            ('Rajkot', 'Dwarka', 225, 4.2),
            ('Dwarka', 'Rajkot', 225, 4.2),
            ('Rajkot', 'Porbandar', 180, 3.5),
            ('Porbandar', 'Rajkot', 180, 3.5),
            ('Rajkot', 'Morbi', 65, 1.3),
            ('Rajkot', 'Gondal', 40, 0.8),
            ('Bhavnagar', 'Palitana', 55, 1.2),
            ('Palitana', 'Bhavnagar', 55, 1.2),
            ('Jamnagar', 'Dwarka', 135, 2.5),
            ('Dwarka', 'Jamnagar', 135, 2.5),
            ('Somnath', 'Sasan Gir', 45, 1.0),
            ('Sasan Gir', 'Somnath', 45, 1.0),
            ('Ahmedabad', 'Botad', 150, 3.0),
            ('Ahmedabad', 'Surendranagar', 125, 2.3),
            ('Ahmedabad', 'Godhra', 125, 2.5),
            ('Ahmedabad', 'Dakor', 85, 1.8),
        ]

        # Authentic Gujarat Boarding/Dropping Landmark Points
        points_map = {
            'Ahmedabad': [
                ('Paldi Cross Road (Near BusGo Lounge)', 'Opposite NID / Ellisbridge', 0),
                ('Geeta Mandir Central ST Terminus', 'Platform No. 4', 15),
                ('CTM Expressway Express Point', 'Near CTM Flyover Toll Booth', 35),
                ('Iscon Crossroad / SG Highway', 'BRTS Junction', 45),
            ],
            'Surat': [
                ('Kamrej Toll Plaza / Express Entry', 'Near Kamrej Chokdi', 0),
                ('Varachha Hirabaug Circle', 'Opp. Sardar Patel Statue', 20),
                ('Surat Central Station (Delhi Gate)', 'Station Road', 35),
            ],
            'Vadodara': [
                ('Amit Nagar Circle / Golden Toll', 'VIP Road Crossing', 0),
                ('Central Bus Station (Pandya Bridge)', 'Opposite Railway Station', 20),
            ],
            'Rajkot': [
                ('Greenland Chokdi / Expressway Entry', 'Ahmedabad Highway', 0),
                ('Madhapar Chokdi / Jamnagar Bypass', 'Ring Road Crossing', 15),
                ('Trikon Baug / City Bus Terminus', 'Main City Center', 25),
            ],
            'Bhavnagar': [
                ('Rupani Circle Bus Point', 'Near Rupani Hall', 0),
                ('Kaliyabid Bus Stand', 'Near Water Tank', 15),
            ],
            'Jamnagar': [
                ('Victoria Bridge Point', 'Near Digjam Circle', 0),
                ('Gurudwara Circle Chokdi', 'Lal Bunglow Road', 15),
            ],
            'Bhuj': [
                ('Jubilee Ground Bus Point', 'Station Road', 0),
                ('RTO Circle Chokdi', 'Bhuj-Mandvi Road', 15),
            ],
            'Somnath': [
                ('Somnath Temple Entry Gate 1', 'Near Mandir Parking', 0),
                ('Veraval Bypass Chokdi', 'Highway Junction', 15),
            ],
            'Dwarka': [
                ('Dwarka ST Bus Stand Chowk', 'Near Bhadrakali Temple', 0),
                ('ISKCON Gate / Highway Point', 'Dwarka Highway', 15),
            ],
            'Junagadh': [
                ('Majevadi Gate Bus Stop', 'Near Sardar Patel Chowk', 0),
                ('Kalwa Chowk Bus Terminal', 'Central Junagadh', 15),
            ],
            'Kevadia (Statue of Unity)': [
                ('Ekta Nagar Railway Station Bus Bay', 'Opposite Ekta Mall', 0),
                ('Statue of Unity Parking Area 1', 'Near High-Speed Shuttles', 15),
            ],
            'Ambaji': [
                ('Ambaji Mandir Circle Point', 'Near Main Temple Gate', 0),
                ('Ambaji ST Bus Stand', 'Highway Entry', 15),
            ],
            'Palanpur': [
                ('Aroma Circle Highway Point', 'Ahmedabad-Abu Road Highway', 0),
                ('Palanpur Central ST Stand', 'Station Road', 15),
            ],
            'Mehsana': [
                ('Radhanpur Chokdi Highway Point', 'Mehsana Bypass', 0),
                ('Modhera Crossroad Bus Stop', 'Highway Flyover', 15),
            ],
            'Patan': [
                ('Patan ST Bus Depot', 'Near Railway Station', 0),
                ('Rani Ki Vav Road Cross', 'University Road', 15),
            ],
            'Gandhinagar': [
                ('Sector 11 GH Road Point', 'Near Pathika Ashram', 0),
                ('Infocity Circle Point', 'Koba-Gandhinagar Highway', 15),
            ],
            'Anand': [
                ('Anand Express Highway Toll', 'Samarkha Chokdi', 0),
                ('Borsad Chokdi Bus Stop', 'Station Road', 15),
            ],
            'Bharuch': [
                ('Zadeshwar Chokdi Flyover Point', 'NH-48 Toll Point', 0),
                ('Bharuch ST Bus Stand', 'Railway Station Road', 15),
            ],
            'Ankleshwar': [
                ('Valia Chokdi Highway Point', 'NH-48 Junction', 0),
                ('GIDC Bus Terminus', 'Near Ankleshwar Station', 15),
            ],
            'Navsari': [
                ('Navsari Greed Crossroad', 'NH-48 Crossing', 0),
                ('Navsari ST Bus Depot', 'Station Road', 15),
            ],
            'Valsad': [
                ('Dharampur Chokdi Highway', 'NH-48 Junction', 0),
                ('Valsad ST Bus Stand', 'Near Railway Station', 15),
            ],
            'Vapi': [
                ('Gunjan Char Rasta Bus Stop', 'NH-48 Flyover', 0),
                ('Vapi GIDC Bus Point', 'Near Hotel Greenview', 15),
            ],
            'Morbi': [
                ('Morbi Maliya Highway Chokdi', 'National Highway Junction', 0),
                ('Sanala Road Circle Point', 'Near New Bus Stand', 15),
            ],
            'Porbandar': [
                ('Porbandar Central ST Stand', 'Jubilee Bridge Road', 0),
                ('Chowpati Circle Bus Stop', 'Beach Road', 15),
            ],
            'Gandhidham': [
                ('Rotary Circle Bus Point', 'Near Main Market', 0),
                ('Gandhidham Railway Station Point', 'Station Road', 15),
            ],
            'Mandvi (Kutch)': [
                ('Mandvi ST Bus Stand', 'Near Vijay Vilas Palace Road', 0),
                ('Wind Farm Beach Chokdi', 'Coastal Highway', 15),
            ],
            'Saputara': [
                ('Saputara Hill Station Bus Bay', 'Near Lake Garden', 0),
                ('Sunset Point Junction', 'Main Road', 15),
            ],
            'Palitana': [
                ('Palitana Taleti Bus Station', 'Near Shatrunjaya Foothills', 0),
                ('Gariadhar Road Chokdi', 'Main Town Entry', 15),
            ],
            'Sasan Gir': [
                ('Sinh Sadan Safari Gate Point', 'Gir Sanctuary Entry', 0),
                ('Sasan Gir ST Bus Stand', 'Station Road', 15),
            ],
            'Godhra': [
                ('Godhra Vavdi Chokdi', 'Vadodara Highway Point', 0),
                ('Godhra ST Central Bus Stand', 'Station Road', 15),
            ],
            'Himatnagar': [
                ('Motipura Circle Highway Point', 'Shamlaji Highway', 0),
                ('Himatnagar ST Stand', 'Town Center', 15),
            ],
            'Surendranagar': [
                ('Milan Cinema Chokdi', 'Main City Road', 0),
                ('Wadhwan City Gate Point', 'ST Road', 15),
            ],
            'Botad': [
                ('Botad Sarangpur Road Chokdi', 'Near Bus Station', 0),
                ('Botad ST Bus Stand', 'Station Road', 15),
            ],
            'Dakor': [
                ('Dakor Ranchhodraiji Mandir Chowk', 'Temple Parking Gate', 0),
                ('Dakor ST Bus Stand', 'Station Road', 15),
            ],
        }

        routes_dict = {}
        for orig, dest, dist, dur in routes_spec:
            if orig not in cities_dict or dest not in cities_dict:
                continue
            r, _ = Route.objects.get_or_create(
                origin=cities_dict[orig],
                destination=cities_dict[dest],
                defaults={'distance_km': dist, 'estimated_duration_hours': dur}
            )
            routes_dict[f"{orig}->{dest}"] = r

            # Add authentic boarding points
            orig_pts = points_map.get(
                orig,
                [(f"{orig} ST Bus Stand", "Central Bus Terminal Area", 0),
                 (f"{orig} Highway Bypass / Circle", "Express Road Junction", 15)]
            )
            for loc, land, offset in orig_pts:
                BoardingPoint.objects.get_or_create(
                    route=r,
                    city=cities_dict[orig],
                    location_name=loc,
                    defaults={'landmark': land, 'time_offset_minutes': offset, 'contact_number': '+91 99001 22334'}
                )

            # Add authentic dropping points
            dest_pts = points_map.get(
                dest,
                [(f"{dest} Terminus", "Near Station", 0),
                 (f"{dest} Highway Bypass", "Main Entry Point", 15)]
            )
            for loc, land, offset in dest_pts:
                DroppingPoint.objects.get_or_create(
                    route=r,
                    city=cities_dict[dest],
                    location_name=loc,
                    defaults={'landmark': land, 'time_offset_minutes': offset, 'contact_number': '+91 99002 55667'}
                )

        # 8. Gujarat Bus Fleets
        buses_spec = [
            {
                'operator': 'Gujarat Express',
                'type': 'Volvo 9600 Multi-Axle AC Sleeper (2+1)',
                'name': 'Gujarat Express Garvi Volvo',
                'number': 'GJ-01-GE-1001',
                'rating': 4.90,
            },
            {
                'operator': 'Patel Tours & Travels',
                'type': 'Volvo 9600 Multi-Axle AC Sleeper (2+1)',
                'name': 'Patel Saurashtra Queen Volvo',
                'number': 'GJ-01-PT-2002',
                'rating': 4.85,
            },
            {
                'operator': 'Shree Sahjanand Travels',
                'type': 'BharatBenz Luxury AC Sleeper (2+1)',
                'name': 'Sahjanand Diamond Sleeper',
                'number': 'GJ-04-ST-3003',
                'rating': 4.75,
            },
            {
                'operator': 'Jay Khodiyar Travels',
                'type': 'Scania Metrolink AC Seater/Sleeper (2+1)',
                'name': 'Jay Khodiyar Royal Cruiser',
                'number': 'GJ-05-JK-4004',
                'rating': 4.70,
            },
            {
                'operator': 'Eagle Falcon Travels',
                'type': 'Mercedes-Benz Multi-Axle Semi-Sleeper (2+2)',
                'name': 'Eagle Falcon Super Express',
                'number': 'GJ-03-EF-5005',
                'rating': 4.80,
            },
            {
                'operator': 'Shree Roadways Gujarat',
                'type': 'Ashok Leyland 2+2 Executive Non-AC Seater',
                'name': 'Shree Roadways Gurjanagri',
                'number': 'GJ-05-SR-6006',
                'rating': 4.40,
            },
        ]

        buses_list = []
        for bspec in buses_spec:
            bus, _ = Bus.objects.get_or_create(
                bus_number=bspec['number'],
                defaults={
                    'operator': operators_dict[bspec['operator']],
                    'bus_type': types_dict[bspec['type']],
                    'bus_name': bspec['name'],
                    'rating': bspec['rating'],
                    'has_wifi': True,
                    'has_charging': True,
                    'has_water': True,
                    'has_blanket': 'Sleeper' in bspec['type'],
                    'has_reading_light': True,
                    'has_cctv': True,
                    'has_emergency_exit': True,
                    'has_gps_tracking': True,
                }
            )
            buses_list.append(bus)

            # Generate seats if not present
            if not bus.seats.exists():
                is_sleeper = bus.bus_type.has_upper_deck
                if is_sleeper:
                    # Lower deck 15 berths (L1..L15)
                    s_idx = 1
                    for r in range(1, 6):
                        for c in [1, 2, 3]:
                            seat_no = f"L{s_idx}"
                            is_ladies = (s_idx in [1, 2, 7])
                            Seat.objects.create(
                                bus=bus, seat_number=seat_no, deck='lower', seat_type='sleeper',
                                row=r, column=c, is_ladies_only=is_ladies, price_multiplier=1.1 if c==3 else 1.0
                            )
                            s_idx += 1
                    # Upper deck 15 berths (U1..U15)
                    s_idx = 1
                    for r in range(1, 6):
                        for c in [1, 2, 3]:
                            seat_no = f"U{s_idx}"
                            Seat.objects.create(
                                bus=bus, seat_number=seat_no, deck='upper', seat_type='sleeper',
                                row=r, column=c, is_ladies_only=False, price_multiplier=1.15 if c==3 else 1.05
                            )
                            s_idx += 1
                else:
                    # 36 seats 2+2
                    s_idx = 1
                    for r in range(1, 10):
                        for c in [1, 2, 3, 4]:
                            Seat.objects.create(
                                bus=bus, seat_number=str(s_idx), deck='lower', seat_type='seater',
                                row=r, column=c, is_ladies_only=(s_idx in [1, 2, 5, 6]), price_multiplier=1.0
                            )
                            s_idx += 1

        # 9. Schedules Across Gujarat for the Next 14 Days
        today = timezone.localdate()
        schedules_created = []

        route_schedule_templates = [
            ('Ahmedabad->Surat', buses_list[0], datetime.time(6, 30), datetime.time(11, 0), 650.00),
            ('Ahmedabad->Surat', buses_list[1], datetime.time(14, 0), datetime.time(18, 30), 700.00),
            ('Ahmedabad->Surat', buses_list[2], datetime.time(22, 30), datetime.time(3, 0), 750.00),
            ('Surat->Ahmedabad', buses_list[0], datetime.time(7, 0), datetime.time(11, 30), 650.00),
            ('Surat->Ahmedabad', buses_list[3], datetime.time(18, 0), datetime.time(22, 30), 700.00),
            ('Ahmedabad->Rajkot', buses_list[4], datetime.time(6, 0), datetime.time(10, 0), 450.00),
            ('Ahmedabad->Rajkot', buses_list[1], datetime.time(17, 30), datetime.time(21, 30), 550.00),
            ('Ahmedabad->Rajkot', buses_list[0], datetime.time(23, 0), datetime.time(3, 0), 600.00),
            ('Rajkot->Ahmedabad', buses_list[4], datetime.time(7, 30), datetime.time(11, 30), 450.00),
            ('Rajkot->Ahmedabad', buses_list[1], datetime.time(16, 0), datetime.time(20, 0), 550.00),
            ('Ahmedabad->Vadodara', buses_list[5], datetime.time(8, 0), datetime.time(10, 0), 180.00),
            ('Ahmedabad->Vadodara', buses_list[4], datetime.time(15, 30), datetime.time(17, 30), 220.00),
            ('Vadodara->Surat', buses_list[2], datetime.time(9, 30), datetime.time(12, 0), 280.00),
            ('Surat->Vadodara', buses_list[3], datetime.time(16, 30), datetime.time(19, 0), 280.00),
            ('Ahmedabad->Bhavnagar', buses_list[2], datetime.time(6, 30), datetime.time(10, 0), 380.00),
            ('Ahmedabad->Bhavnagar', buses_list[2], datetime.time(18, 0), datetime.time(21, 30), 420.00),
            ('Ahmedabad->Jamnagar', buses_list[4], datetime.time(7, 0), datetime.time(12, 30), 580.00),
            ('Ahmedabad->Bhuj', buses_list[1], datetime.time(21, 30), datetime.time(4, 0), 780.00),
            ('Ahmedabad->Somnath', buses_list[0], datetime.time(21, 0), datetime.time(4, 30), 850.00),
            ('Ahmedabad->Dwarka', buses_list[3], datetime.time(20, 30), datetime.time(4, 30), 890.00),
            ('Rajkot->Jamnagar', buses_list[4], datetime.time(11, 0), datetime.time(12, 30), 150.00),
            ('Surat->Rajkot', buses_list[1], datetime.time(20, 0), datetime.time(3, 30), 850.00),
            ('Ahmedabad->Kevadia (Statue of Unity)', buses_list[0], datetime.time(7, 0), datetime.time(10, 30), 450.00),
            ('Vadodara->Kevadia (Statue of Unity)', buses_list[4], datetime.time(8, 30), datetime.time(10, 15), 180.00),
            ('Ahmedabad->Ambaji', buses_list[2], datetime.time(6, 0), datetime.time(9, 45), 380.00),
            ('Ahmedabad->Palanpur', buses_list[5], datetime.time(14, 0), datetime.time(17, 0), 260.00),
            ('Ahmedabad->Mehsana', buses_list[4], datetime.time(9, 0), datetime.time(10, 30), 140.00),
            ('Surat->Vapi', buses_list[3], datetime.time(10, 0), datetime.time(12, 15), 220.00),
            ('Surat->Saputara', buses_list[1], datetime.time(6, 45), datetime.time(10, 15), 320.00),
            ('Rajkot->Somnath', buses_list[0], datetime.time(8, 0), datetime.time(11, 45), 390.00),
            ('Rajkot->Dwarka', buses_list[3], datetime.time(13, 0), datetime.time(17, 15), 440.00),
            ('Ahmedabad->Morbi', buses_list[4], datetime.time(16, 0), datetime.time(20, 0), 420.00),
            ('Ahmedabad->Gandhidham', buses_list[1], datetime.time(22, 0), datetime.time(3, 30), 620.00),
            ('Ahmedabad->Porbandar', buses_list[2], datetime.time(21, 30), datetime.time(5, 0), 750.00),
        ]

        for day_offset in range(0, 14):
            dept_date = today + datetime.timedelta(days=day_offset)
            for r_key, bus_obj, d_time, a_time, price in route_schedule_templates:
                if r_key in routes_dict:
                    arr_date = dept_date if a_time > d_time else (dept_date + datetime.timedelta(days=1))
                    sch, _ = BusSchedule.objects.get_or_create(
                        bus=bus_obj,
                        route=routes_dict[r_key],
                        departure_date=dept_date,
                        departure_time=d_time,
                        defaults={
                            'arrival_date': arr_date,
                            'arrival_time': a_time,
                            'base_price': price,
                            'status': 'scheduled',
                        }
                    )
                    schedules_created.append(sch)

                    # Initialize seats
                    all_seats = list(bus_obj.seats.all())
                    for idx, seat in enumerate(all_seats):
                        is_demo_booked = (idx in [2, 3, 8, 12, 20])
                        status_str = 'booked' if is_demo_booked else 'available'
                        ScheduleSeatStatus.objects.get_or_create(
                            schedule=sch,
                            seat=seat,
                            defaults={
                                'status': status_str,
                                'booked_gender': 'female' if seat.is_ladies_only else ('male' if is_demo_booked else '')
                            }
                        )

        self.stdout.write(f"Created {len(schedules_created)} schedules across Gujarat for next 14 days.")

        # 10. Sample Gujarat Bookings for Customer
        # Booking 1: Ahmedabad to Surat
        sch_ahm_sur = BusSchedule.objects.filter(
            route=routes_dict.get('Ahmedabad->Surat'),
            departure_date__gte=today
        ).first()

        if sch_ahm_sur:
            seat_l7 = sch_ahm_sur.bus.seats.filter(deck='lower').first()
            if seat_l7:
                ScheduleSeatStatus.objects.filter(schedule=sch_ahm_sur, seat=seat_l7).update(status='booked')
            bp1 = sch_ahm_sur.route.boarding_points.first()
            dp1 = sch_ahm_sur.route.dropping_points.first()

            booking1, b1_created = Booking.objects.get_or_create(
                booking_id='PNR10001',
                defaults={
                    'customer': customer_user,
                    'schedule': sch_ahm_sur,
                    'boarding_point': bp1,
                    'dropping_point': dp1,
                    'total_seats': 1,
                    'base_fare': 650.00,
                    'tax_amount': 32.50,
                    'convenience_fee': 20.00,
                    'total_amount': 702.50,
                    'booking_status': 'confirmed',
                    'contact_email': customer_user.email,
                    'contact_phone': '+91 98765 43210',
                }
            )
            if b1_created and seat_l7:
                Passenger.objects.create(
                    booking=booking1,
                    seat=seat_l7,
                    name='Aarav Patel',
                    age=28,
                    gender='male',
                    id_type='aadhaar',
                    id_number='7894-3210-9988',
                    seat_fare=650.00
                )
                Payment.objects.create(
                    booking=booking1,
                    payment_method='upi',
                    amount=702.50,
                    status='success',
                    upi_id='aarav@okaxis',
                    paid_at=timezone.now()
                )
                generate_booking_qr(booking1)
                generate_ticket_pdf(booking1)

        # Booking 2: Ahmedabad to Rajkot
        sch_ahm_raj = BusSchedule.objects.filter(
            route=routes_dict.get('Ahmedabad->Rajkot'),
            departure_date__gte=today
        ).first()

        if sch_ahm_raj:
            seats_ar = list(sch_ahm_raj.bus.seats.filter(deck='lower')[:2])
            bp2 = sch_ahm_raj.route.boarding_points.first()
            dp2 = sch_ahm_raj.route.dropping_points.first()

            booking2, b2_created = Booking.objects.get_or_create(
                booking_id='PNR10002',
                defaults={
                    'customer': customer_user,
                    'schedule': sch_ahm_raj,
                    'boarding_point': bp2,
                    'dropping_point': dp2,
                    'total_seats': len(seats_ar),
                    'base_fare': 900.00,
                    'tax_amount': 45.00,
                    'convenience_fee': 20.00,
                    'total_amount': 965.00,
                    'booking_status': 'confirmed',
                    'contact_email': customer_user.email,
                    'contact_phone': '+91 98765 43210',
                }
            )
            if b2_created and seats_ar:
                for idx, s in enumerate(seats_ar):
                    ScheduleSeatStatus.objects.filter(schedule=sch_ahm_raj, seat=s).update(status='booked')
                    Passenger.objects.create(
                        booking=booking2,
                        seat=s,
                        name='Aarav Patel' if idx == 0 else 'Priya Patel',
                        age=28 if idx == 0 else 26,
                        gender='male' if idx == 0 else 'female',
                        id_type='aadhaar',
                        id_number='7894-3210-9988' if idx == 0 else 'ABCPS1234F',
                        seat_fare=450.00
                    )
                Payment.objects.create(
                    booking=booking2,
                    payment_method='card',
                    amount=965.00,
                    status='success',
                    card_last4='4242',
                    paid_at=timezone.now()
                )
                generate_booking_qr(booking2)
                generate_ticket_pdf(booking2)

        # Booking 3: Vadodara to Surat (Completed)
        sch_vad_sur = BusSchedule.objects.filter(
            route=routes_dict.get('Vadodara->Surat')
        ).first()

        if sch_vad_sur:
            seat_comp = sch_vad_sur.bus.seats.last()
            bp3 = sch_vad_sur.route.boarding_points.first()
            dp3 = sch_vad_sur.route.dropping_points.first()

            booking3, b3_created = Booking.objects.get_or_create(
                booking_id='PNR10003',
                defaults={
                    'customer': customer_user,
                    'schedule': sch_vad_sur,
                    'boarding_point': bp3,
                    'dropping_point': dp3,
                    'total_seats': 1,
                    'base_fare': 280.00,
                    'tax_amount': 14.00,
                    'convenience_fee': 20.00,
                    'total_amount': 314.00,
                    'booking_status': 'completed',
                    'contact_email': customer_user.email,
                    'contact_phone': '+91 98765 43210',
                }
            )
            if b3_created and seat_comp:
                Passenger.objects.create(
                    booking=booking3,
                    seat=seat_comp,
                    name='Aarav Patel',
                    age=28,
                    gender='male',
                    id_type='aadhaar',
                    id_number='7894-3210-9988',
                    seat_fare=280.00
                )
                Payment.objects.create(
                    booking=booking3,
                    payment_method='wallet',
                    amount=314.00,
                    status='success',
                    paid_at=timezone.now()
                )
                generate_booking_qr(booking3)
                generate_ticket_pdf(booking3)

        self.stdout.write(self.style.SUCCESS("BusGo Gujarat sample data populated successfully!"))
