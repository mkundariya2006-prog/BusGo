import uuid
from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from buses.models import Bus, Seat
from routes.models import BusSchedule, BoardingPoint, DroppingPoint

class ScheduleSeatStatus(models.Model):
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('locked', 'Locked'),
        ('booked', 'Booked'),
    )

    schedule = models.ForeignKey(BusSchedule, on_delete=models.CASCADE, related_name='seat_statuses')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='schedule_statuses')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='available')
    locked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    booked_gender = models.CharField(max_length=10, blank=True, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('schedule', 'seat')
        indexes = [
            models.Index(fields=['schedule', 'status']),
        ]

    def is_currently_available(self):
        if self.status == 'available':
            return True
        if self.status == 'locked' and self.locked_until and self.locked_until < timezone.now():
            return True
        return False

    def get_effective_status(self):
        if self.status == 'booked':
            return 'booked'
        if self.status == 'locked':
            if self.locked_until and self.locked_until < timezone.now():
                return 'available'
            return 'locked'
        return 'available'

    @classmethod
    def lock_seats(cls, schedule, seat_ids, user, duration_minutes=10):
        """
        Concurrency-safe seat locking using select_for_update.
        Locks the given seats for the specified user.
        Raises ValueError if any seat is already booked or locked by someone else.
        """
        now = timezone.now()
        expiry = now + timedelta(minutes=duration_minutes)

        with transaction.atomic():
            statuses = cls.objects.select_for_update().filter(
                schedule=schedule,
                seat_id__in=seat_ids
            )
            
            # Create statuses if they don't exist yet
            existing_seat_ids = set(statuses.values_list('seat_id', flat=True))
            missing_seat_ids = set(seat_ids) - existing_seat_ids
            for s_id in missing_seat_ids:
                cls.objects.create(
                    schedule=schedule,
                    seat_id=s_id,
                    status='available'
                )
            
            # Refetch with lock
            statuses = list(cls.objects.select_for_update().filter(
                schedule=schedule,
                seat_id__in=seat_ids
            ))

            for s in statuses:
                if s.status == 'booked':
                    raise ValueError(f"Seat {s.seat.seat_number} is already booked.")
                if s.status == 'locked' and s.locked_until and s.locked_until > now:
                    if s.locked_by != user:
                        raise ValueError(f"Seat {s.seat.seat_number} is currently held by another customer. Please choose another seat.")

            # Update statuses to locked
            for s in statuses:
                s.status = 'locked'
                s.locked_by = user
                s.locked_until = expiry
                s.save()

            return statuses


class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )

    booking_id = models.CharField(max_length=20, unique=True, db_index=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    schedule = models.ForeignKey(BusSchedule, on_delete=models.CASCADE, related_name='bookings')
    boarding_point = models.ForeignKey(BoardingPoint, on_delete=models.SET_NULL, null=True, blank=True)
    dropping_point = models.ForeignKey(DroppingPoint, on_delete=models.SET_NULL, null=True, blank=True)
    
    total_seats = models.PositiveIntegerField(default=1)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    convenience_fee = models.DecimalField(max_digits=8, decimal_places=2, default=20.00)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    booking_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    
    qr_code_image = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    pdf_ticket = models.FileField(upload_to='tickets/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.booking_id:
            self.booking_id = 'BG' + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.booking_id} - {self.customer.username} ({self.schedule.route})"

    @property
    def seat_numbers_list(self):
        return list(self.passengers.values_list('seat__seat_number', flat=True))

    @property
    def seat_numbers_display(self):
        return ", ".join(self.seat_numbers_list)


class Passenger(models.Model):
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )
    ID_TYPE_CHOICES = (
        ('aadhaar', 'Aadhaar Card'),
        ('pan', 'PAN Card'),
        ('passport', 'Passport'),
        ('voter_id', 'Voter ID'),
        ('driving_license', 'Driving License'),
    )

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='passengers')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    id_type = models.CharField(max_length=30, choices=ID_TYPE_CHOICES, blank=True, default='aadhaar')
    id_number = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    seat_fare = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.name} - Seat {self.seat.seat_number}"


class Cancellation(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='cancellation')
    reason = models.TextField()
    cancellation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cancelled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cancellation for {self.booking.booking_id}"


class Refund(models.Model):
    STATUS_CHOICES = (
        ('initiated', 'Initiated'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    )

    cancellation = models.OneToOneField(Cancellation, on_delete=models.CASCADE, related_name='refund')
    refund_id = models.CharField(max_length=30, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processed')
    payment_method = models.CharField(max_length=50, default='Original Source (Card/UPI)')
    processed_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.refund_id:
            self.refund_id = 'RF' + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.refund_id} - ₹{self.amount} ({self.status})"


class Review(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.username} on {self.bus.bus_name}: {self.rating}★"
