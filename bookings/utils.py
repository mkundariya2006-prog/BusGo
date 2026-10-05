import os
import io
import qrcode
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from decimal import Decimal, ROUND_HALF_UP

def generate_booking_qr(booking):
    """
    Generates a QR code image for a booking and saves it to media/qrcodes/.
    Returns the relative media path or URL.
    """
    qr_data = (
        f"BUSGO E-TICKET\n"
        f"PNR: {booking.booking_id}\n"
        f"Status: {booking.booking_status.upper()}\n"
        f"Route: {booking.schedule.route.origin.name} to {booking.schedule.route.destination.name}\n"
        f"Date: {booking.schedule.departure_date.strftime('%d %b %Y')} {booking.schedule.departure_time.strftime('%H:%M')}\n"
        f"Bus: {booking.schedule.bus.bus_name} ({booking.schedule.bus.bus_number})\n"
        f"Seats: {booking.seat_numbers_display}\n"
        f"Total: INR {booking.total_amount}\n"
        f"Verify: https://busgo.com/ticket/{booking.booking_id}/"
    )
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0b2545", back_color="white")

    filename = f"qr_{booking.booking_id}.png"
    rel_path = os.path.join('qrcodes', filename)
    full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    img.save(full_path)
    
    booking.qr_code_image = rel_path
    booking.save(update_fields=['qr_code_image'])
    return rel_path


def send_booking_ticket_email(booking):
    """
    Sends the PDF ticket and QR code to the passenger contacts for this booking.
    Falls back to the booker email if no passenger email is present.
    """
    recipients = []
    for passenger in booking.passengers.exclude(email='').order_by('id'):
        if passenger.email not in recipients:
            recipients.append(passenger.email)
    if not recipients:
        recipients = [booking.contact_email] if booking.contact_email else []

    if not recipients:
        return False

    if not booking.pdf_ticket:
        generate_ticket_pdf(booking)

    pdf_path = booking.pdf_ticket.path if booking.pdf_ticket and hasattr(booking.pdf_ticket, 'path') else None
    if not pdf_path or not os.path.exists(pdf_path):
        return False

    passenger_names = ", ".join(p.name for p in booking.passengers.all() if p.name)
    subject = f"BusGo Ticket {booking.booking_id} | {booking.schedule.route.origin.name} to {booking.schedule.route.destination.name}"
    message = (
        f"Hello,\n\n"
        f"Your BusGo ticket is confirmed.\n\n"
        f"Booking ID: {booking.booking_id}\n"
        f"Passenger(s): {passenger_names or booking.customer.get_full_name() or booking.customer.username}\n"
        f"Route: {booking.schedule.route.origin.name} to {booking.schedule.route.destination.name}\n"
        f"Travel Date: {booking.schedule.departure_date.strftime('%d %b %Y')}\n"
        f"Departure Time: {booking.schedule.departure_time.strftime('%I:%M %p')}\n"
        f"Seats: {booking.seat_numbers_display}\n\n"
        f"This ticket is attached as a PDF for your convenience.\n\n"
        f"Thank you for travelling with BusGo.\n"
        f"Safe journeys!"
    )

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'BusGo Support <no-reply@busgo.com>'),
        to=recipients,
    )
    email.attach_file(pdf_path)

    qr_path = None
    if booking.qr_code_image:
        qr_path = os.path.join(settings.MEDIA_ROOT, str(booking.qr_code_image))
    if qr_path and os.path.exists(qr_path):
        email.attach_file(qr_path)

    try:
        return email.send(fail_silently=False) > 0
    except Exception:
        return False


def generate_ticket_pdf(booking):
    """
    Generates a professional, branded A4 PDF ticket using ReportLab.
    Saves it to media/tickets/ and returns the relative path.
    """
    # Ensure QR code exists
    if not booking.qr_code_image:
        generate_booking_qr(booking)

    filename = f"ticket_{booking.booking_id}.pdf"
    rel_path = os.path.join('tickets', filename)
    full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    doc = SimpleDocTemplate(
        full_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor('#0b2545')
    accent_color = colors.HexColor('#0ea5e9')
    dark_gray = colors.HexColor('#334155')
    light_bg = colors.HexColor('#f8fafc')
    success_color = colors.HexColor('#10b981')

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=primary_color,
        leading=28,
        alignment=TA_LEFT
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=dark_gray,
        leading=14
    )

    h2_style = ParagraphStyle(
        'H2Style',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=6
    )

    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=dark_gray,
        leading=13
    )

    bold_style = ParagraphStyle(
        'BoldStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=primary_color,
        leading=13
    )

    elements = []

    # Header with Logo & PNR
    header_data = [
        [
            Paragraph("<b>BusGo</b> <font size=9 color='#0ea5e9'>• Smart Travel</font><br/><font size=8 color='#64748b'>E-Ticket & Boarding Pass</font>", title_style),
            Paragraph(f"<font color='#64748b' size=8>PNR / BOOKING ID</font><br/><font size=16 color='#0b2545'><b>{booking.booking_id}</b></font><br/><font size=9 color='#10b981'><b>● {booking.booking_status.upper()}</b></font>", ParagraphStyle('HRight', parent=styles['Normal'], alignment=TA_RIGHT))
        ]
    ]
    header_table = Table(header_data, colWidths=[320, 220])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=2, color=accent_color, spaceBefore=4, spaceAfter=12))

    # Journey & Bus Overview Box
    sch = booking.schedule
    bus = sch.bus
    bp = booking.boarding_point
    dp = booking.dropping_point
    bp_text = f"{bp.location_name} ({bp.city.name})" if bp else f"{sch.route.origin.name} Bus Stand"
    dp_text = f"{dp.location_name} ({dp.city.name})" if dp else f"{sch.route.destination.name} Drop Point"

    journey_data = [
        [
            Paragraph("<b>JOURNEY DETAILS</b>", bold_style),
            Paragraph("<b>BUS & OPERATOR</b>", bold_style)
        ],
        [
            Paragraph(
                f"<b>From:</b> {sch.route.origin.name} &nbsp; ➔ &nbsp; <b>To:</b> {sch.route.destination.name}<br/>"
                f"<b>Date:</b> {sch.departure_date.strftime('%A, %d %B %Y')}<br/>"
                f"<b>Departure Time:</b> <font color='#0b2545'><b>{sch.departure_time.strftime('%I:%M %p')}</b></font><br/>"
                f"<b>Est. Arrival:</b> {sch.arrival_time.strftime('%I:%M %p')} ({sch.arrival_date.strftime('%d %b')})<br/>"
                f"<b>Boarding:</b> {bp_text}<br/>"
                f"<b>Dropping:</b> {dp_text}",
                normal_style
            ),
            Paragraph(
                f"<b>Operator:</b> {bus.operator.company_name}<br/>"
                f"<b>Bus Name:</b> {bus.bus_name}<br/>"
                f"<b>Bus Number:</b> {bus.bus_number}<br/>"
                f"<b>Type:</b> {bus.bus_type.name}<br/>"
                f"<b>Seats Booked:</b> <font color='#0ea5e9'><b>{booking.seat_numbers_display}</b></font> ({booking.total_seats} seats)<br/>"
                f"<b>Helpline:</b> {bus.operator.contact_phone}",
                normal_style
            )
        ]
    ]

    journey_table = Table(journey_data, colWidths=[270, 270])
    journey_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light_bg),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(journey_table)
    elements.append(Spacer(1, 14))

    # Passenger Details Table
    elements.append(Paragraph("PASSENGER DETAILS", h2_style))
    passenger_rows = [
        [
            Paragraph("<b>#</b>", bold_style),
            Paragraph("<b>Passenger Name</b>", bold_style),
            Paragraph("<b>Age</b>", bold_style),
            Paragraph("<b>Gender</b>", bold_style),
            Paragraph("<b>Seat No.</b>", bold_style),
            Paragraph("<b>ID Proof</b>", bold_style),
        ]
    ]

    passengers = booking.passengers.all()
    for idx, p in enumerate(passengers, 1):
        id_display = f"{p.get_id_type_display()}: {p.id_number}" if p.id_number else "Verify on Boarding"
        passenger_rows.append([
            Paragraph(str(idx), normal_style),
            Paragraph(f"<b>{p.name}</b>", normal_style),
            Paragraph(str(p.age), normal_style),
            Paragraph(p.gender.capitalize(), normal_style),
            Paragraph(f"<b>{p.seat.seat_number}</b> ({p.seat.get_deck_display()})", bold_style),
            Paragraph(id_display, normal_style),
        ])

    p_table = Table(passenger_rows, colWidths=[25, 175, 45, 65, 85, 145])
    p_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(p_table)
    elements.append(Spacer(1, 14))

    # Fare Breakdown & QR Code Row
    qr_full_path = os.path.join(settings.MEDIA_ROOT, booking.qr_code_image.name)
    qr_img_flowable = None
    if os.path.exists(qr_full_path):
        qr_img_flowable = RLImage(qr_full_path, width=95, height=95)

    fare_table_data = [
        [Paragraph("Base Fare:", normal_style), Paragraph(f"INR {booking.base_fare:.2f}", normal_style)],
        [Paragraph("GST & Taxes (5%):", normal_style), Paragraph(f"INR {booking.tax_amount:.2f}", normal_style)],
        [Paragraph("Convenience Fee:", normal_style), Paragraph(f"INR {booking.convenience_fee:.2f}", normal_style)],
        [Paragraph("Discount:", normal_style), Paragraph(f"- INR {booking.discount_amount:.2f}", normal_style)],
        [Paragraph("<b>Total Fare Paid:</b>", bold_style), Paragraph(f"<b>INR {booking.total_amount:.2f}</b>", bold_style)],
    ]
    fare_subtable = Table(fare_table_data, colWidths=[130, 90])
    fare_subtable.setStyle(TableStyle([
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LINEABOVE', (0,4), (-1,4), 1, primary_color),
    ]))

    payment_info = (
        f"<b>Payment Status:</b> <font color='#10b981'>SUCCESSFUL</font><br/>"
        f"<b>Booked On:</b> {booking.created_at.strftime('%d-%b-%Y %I:%M %p')}<br/>"
        f"<b>Contact:</b> {booking.contact_phone} | {booking.contact_email}"
    )

    qr_block = [
        [
            qr_img_flowable if qr_img_flowable else Paragraph("QR Code", normal_style),
            Paragraph(f"<font size=8 color='#64748b'>Scan at boarding time for contactless verification.</font><br/><br/>{payment_info}", normal_style),
            fare_subtable
        ]
    ]
    bottom_table = Table(qr_block, colWidths=[105, 215, 220])
    bottom_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), light_bg),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(bottom_table)
    elements.append(Spacer(1, 14))

    # Terms & Conditions
    elements.append(Paragraph("IMPORTANT INSTRUCTIONS & CANCELLATION POLICY", h2_style))
    terms = (
        "1. Please report at the boarding point at least 15 minutes before the scheduled departure time.<br/>"
        "2. Passengers must carry a government-issued photo ID (Aadhaar, Passport, Driving License, or Voter ID).<br/>"
        "3. Cancellation Policy: >24 hrs: 90% refund | 12-24 hrs: 75% refund | 2-12 hrs: 50% refund | <2 hrs: Non-refundable.<br/>"
        "4. BusGo 24/7 Helpline: 1800-123-BUSGO (28746) | Email: support@busgo.com"
    )
    elements.append(Paragraph(terms, ParagraphStyle('Terms', parent=styles['Normal'], fontSize=7.5, leading=11, textColor=colors.HexColor('#64748b'))))

    doc.build(elements)
    booking.pdf_ticket = rel_path
    booking.save(update_fields=['pdf_ticket'])
    return rel_path


def calculate_refund_amount(booking):
    """
    Calculates refund amount and cancellation fee based on hours prior to departure.
    Rules:
    - > 24 hours: 10% fee, 90% refund
    - 12 to 24 hours: 25% fee, 75% refund
    - 2 to 12 hours: 50% fee, 50% refund
    - < 2 hours: 100% fee, 0% refund
    """
    import datetime

    # Build departure datetime and ensure it's timezone-aware
    departure_dt = datetime.datetime.combine(
        booking.schedule.departure_date,
        booking.schedule.departure_time
    )
    if departure_dt.tzinfo is None:
        departure_dt = timezone.make_aware(departure_dt, timezone.get_current_timezone())

    now = timezone.now()
    diff = departure_dt - now
    hours_left = diff.total_seconds() / 3600.0

    total = Decimal(str(booking.total_amount))

    if hours_left >= 24:
        fee_pct = Decimal('0.10')
    elif hours_left >= 12:
        fee_pct = Decimal('0.25')
    elif hours_left >= 2:
        fee_pct = Decimal('0.50')
    else:
        fee_pct = Decimal('1.00')

    cancellation_fee = (total * fee_pct).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    refund_amount = (total - cancellation_fee).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return cancellation_fee, refund_amount, int((fee_pct * 100).to_integral_value())
