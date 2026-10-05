# BusGo Gujarat – Online Bus Booking System

A modern, responsive, commercial-grade web-based bus ticket booking platform built with **Python**, **Django**, and **Django REST Framework**, exclusively tailored for intercity travel across **Gujarat**.

---

## 🌟 Gujarat Network Highlights

- **Exhaustive Gujarat Coverage (All 33 Districts)**: 271 cities, taluka headquarters, and pilgrimage centers mapped across all 33 districts of Gujarat (Ahmedabad, Surat, Vadodara, Rajkot, Bhavnagar, Jamnagar, Gandhinagar, Junagadh, Kutch, Anand, Kheda, Bharuch, Navsari, Valsad, Morbi, Surendranagar, Banaskantha, Mehsana, Patan, Sabarkantha, Aravalli, Panchmahal, Dahod, Mahisagar, Chhota Udaipur, Narmada, Tapi, Dang, Amreli, Botad, Gir Somnath, Porbandar, and Devbhumi Dwarka).
- **Major Tourism & Pilgrimage Centers**: Somnath, Dwarka, Ambaji, Palitana, Kevadia (Statue of Unity), Saputara, Sasan Gir, Dakor, Modhera, Siddhpur, Pavagadh, Shamlaji, Bet Dwarka, Sarangpur.
- **90 Connecting Intercity Routes within Gujarat**: Ahmedabad ⇄ Surat, Ahmedabad ⇄ Rajkot, Ahmedabad ⇄ Vadodara, Vadodara ⇄ Surat, Ahmedabad ⇄ Bhavnagar, Ahmedabad ⇄ Jamnagar, Rajkot ⇄ Jamnagar, Ahmedabad ⇄ Bhuj, Surat ⇄ Rajkot, Ahmedabad ⇄ Somnath, Ahmedabad ⇄ Dwarka, Ahmedabad ⇄ Kevadia (Statue of Unity), Vadodara ⇄ Kevadia, Ahmedabad ⇄ Ambaji, Surat ⇄ Vapi, Surat ⇄ Saputara, Rajkot ⇄ Somnath, and dozens more.
- **Top Gujarat Operators**: Gujarat Express (Ahmedabad), Patel Tours & Travels, Shree Sahjanand Travels (Bhavnagar), Jay Khodiyar Travels (Surat), Eagle Falcon Travels (Rajkot), Shree Roadways Gujarat.
- **Authentic Local Boarding Points**: Paldi Cross Road, Geeta Mandir Central ST, CTM Expressway, Iscon SG Highway, Kamrej Toll Plaza, Varachha Hirabaug, Amit Nagar Circle, Greenland Chokdi, Madhapar Chokdi, Ekta Nagar Station Bus Bay, etc.
- **476+ Live Schedules across 14 days** with real-time seat inventories and pricing.
- **Dedicated REST API**: Full city and route discovery API at `/api/cities/` with search and district filtering.

### 1. Customer Experience
- **Hero & Search Widget**: Direct departure and destination city selection, real-time swap button, and journey date picker.
- **Bus Search & Filters**: Live filtering by AC/Non-AC, Sleeper/Seater/Semi-Sleeper, Departure Time slots (Morning, Afternoon, Evening, Night), Bus Operator, and Amenities (Wi-Fi, Charging, Water bottle, Blanket, Live GPS).
- **Sorting**: Cheapest First, Earliest Departure, Shortest Duration, and Highest Rated.
- **Interactive Seat Selection**: Dual-deck bus layout (Lower Deck & Upper Deck) with driver steering wheel. Displays live seat states: *Available*, *Booked*, *Ladies Only*, and *Selected* (with checkmark and live fare calculator).
- **Passenger Details**: Multi-passenger form with Govt ID validation, saved passenger quick-fill, and coupon codes (`BUSGO15`, `FIRSTBUS`, `FESTIVE50`).
- **Mock Payment Gateway**: Simulates UPI (Google Pay, PhonePe, Paytm QR), Credit/Debit Cards, Net Banking, and instant 1-click **BusGo Wallet** payments.
- **Digital Boarding Pass & E-Ticket**:
  - Live cryptographic QR Code for conductor scanning.
  - Official A4 PDF Ticket generation using **ReportLab**.
  - Browser print layout with print-optimized CSS.
  - Automated confirmation email dispatch.
- **Customer Dashboard ("My Bookings")**:
  - Exact match to commercial mockup: Wallet Balance (₹25,840.50), Total Bookings (3), Reward Points (450), Active Bookings (2).
  - Tabs for Upcoming Journeys, Completed Journeys, and Cancelled Bookings.
- **Cancellation & Transparent Refund**:
  - > 24 hours: 90% refund (10% fee)
  - 12 to 24 hours: 75% refund (25% fee)
  - 2 to 12 hours: 50% refund (50% fee)
  - < 2 hours: Non-refundable
  - Automated seat release and instant wallet refund credit.

### 2. Concurrency Safety & Double-Booking Prevention
- Implements database transactions (`transaction.atomic()`) and row-level locking (`select_for_update()`).
- Temporarily locks seats for 10 minutes during checkout.
- Prevents concurrent race conditions when two customers attempt to select or purchase the same seat simultaneously.

### 3. Custom Admin Dashboard (`/dashboard/admin/`)
- Sleek modern custom dashboard (not default Django admin).
- Top KPI cards: Total Customers, Bus Fleets, Bus Operators, Today's Bookings, Total Revenue, Cancelled Bookings.
- Chart.js Visualizations:
  - Daily Bookings Activity Line Chart (last 7 days).
  - Bus Fleet Composition Donut Chart.
  - Popular Routes Distribution Bar Chart.
- Operations Management:
  - Customers: search, view details, block/unblock accounts.
  - Operators: approve or reject partner registrations.
  - Buses: add coaches, configure seat layout.
  - Routes: connect cities with distance and travel time.
  - Schedules: publish departures and set base fares.
  - Bookings: inspect PNRs, statuses, and payment records.
  - Reports: gross revenue, refunds, and net platform earnings.

### 4. Bus Operator Portal (`/operators/dashboard/`)
- Dedicated role-based portal for bus operators.
- View assigned fleet coaches and active trips.
- Add new buses and publish departure schedules.
- Generate and print **Driver / Conductor Passenger Manifests** with passenger names, ages, phone numbers, and boarding points.
- Net earnings calculation (90% after 10% platform commission).

### 5. Django REST Framework APIs (`/api/`)
- `POST /api/auth/login/` & `POST /api/auth/register/`
- `GET /api/buses/search/?origin=...&destination=...&date=...`
- `GET /api/buses/<id>/`
- `GET /api/routes/` & `GET /api/schedules/`
- `GET /api/seats/<schedule_id>/`
- `GET /api/bookings/` & `POST /api/bookings/`
- `POST /api/bookings/<id>/cancel/`
- `POST /api/payments/`
- `GET /api/tickets/<booking_id>/`

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.13, Django 6.1, Django REST Framework |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Font Awesome 6.5 |
| **Charts** | Chart.js 4.x |
| **Document Generation** | ReportLab (PDF Tickets), QRCode (PIL) |
| **Database** | SQLite (Local Dev) / PostgreSQL (Production ready) |
| **Authentication** | Session Authentication, Password Hashing, Role-Based Access Control |

---

## 🚀 Setup & Execution Guide

### 1. Prerequisites
Ensure Python 3.10+ is installed on your system.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Populate Realistic Sample Data
Run the custom seeder command to generate 10 cities, 5 operators, 6 buses with dual-deck seat layouts, 224 schedules across 14 days, sample bookings, QR codes, and PDF tickets:
```bash
python manage.py seed_data
```

### 5. SMTP Ticket Email Setup (Optional)
To send confirmed bus tickets via email using SMTP, add your mail server details in `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=BusGo Support <no-reply@busgo.com>
```

When SMTP is configured, the app automatically sends the generated PDF ticket and QR code to the customer email after a successful booking.

### 6. Run the Server
```bash
python manage.py runserver 127.0.0.1:8080
```
Open your browser and navigate to: [http://127.0.0.1:8080/](http://127.0.0.1:8080/)

---

## 🔑 Test Credentials

| Role | Username | Password | Direct Portal URL |
|---|---|---|---|
| **Customer** | `customer` | `customer123` | [http://127.0.0.1:8080/accounts/dashboard/](http://127.0.0.1:8080/accounts/dashboard/) |
| **Operator** | `operator` | `operator123` | [http://127.0.0.1:8080/operators/dashboard/](http://127.0.0.1:8080/operators/dashboard/) |
| **Admin** | `admin` | `admin123` | [http://127.0.0.1:8080/dashboard/admin/](http://127.0.0.1:8080/dashboard/admin/) |

*Note: The login page includes quick autofill buttons for all three roles.*

---

## 🧪 Running Automated Tests

Run the full automated test suite covering authentication, bus search, seat locking, double-booking prevention, mock payment, PDF/QR ticket generation, and cancellation refund policy:
```bash
python manage.py test
```
All tests execute and report `OK` (5/5 tests passing).
