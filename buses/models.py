from django.db import models
from operators.models import BusOperator

class BusType(models.Model):
    CATEGORY_CHOICES = (
        ('seater', 'Seater'),
        ('sleeper', 'Sleeper'),
        ('semi_sleeper', 'Semi-Sleeper'),
        ('seater_sleeper', 'Seater & Sleeper'),
    )

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='sleeper')
    is_ac = models.BooleanField(default=True)
    has_upper_deck = models.BooleanField(default=True)
    total_seats = models.PositiveIntegerField(default=36)
    layout_type = models.CharField(max_length=20, default='2+1', help_text="e.g. 2+2 or 2+1")

    def __str__(self):
        ac_str = "AC" if self.is_ac else "Non-AC"
        return f"{self.name} ({ac_str} {self.get_category_display()})"


class Bus(models.Model):
    operator = models.ForeignKey(BusOperator, on_delete=models.CASCADE, related_name='buses')
    bus_type = models.ForeignKey(BusType, on_delete=models.PROTECT, related_name='buses')
    bus_name = models.CharField(max_length=150)
    bus_number = models.CharField(max_length=30, unique=True)
    
    # Amenities
    has_wifi = models.BooleanField(default=True)
    has_charging = models.BooleanField(default=True)
    has_water = models.BooleanField(default=True)
    has_blanket = models.BooleanField(default=True)
    has_reading_light = models.BooleanField(default=True)
    has_cctv = models.BooleanField(default=True)
    has_emergency_exit = models.BooleanField(default=True)
    has_gps_tracking = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=4.6)
    total_reviews = models.PositiveIntegerField(default=85)
    image = models.ImageField(upload_to='buses/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Buses"
        ordering = ['-rating', 'bus_name']

    def __str__(self):
        return f"{self.bus_name} [{self.bus_number}] - {self.operator.company_name}"


class Seat(models.Model):
    DECK_CHOICES = (
        ('lower', 'Lower Deck'),
        ('upper', 'Upper Deck'),
    )
    SEAT_TYPE_CHOICES = (
        ('seater', 'Seater'),
        ('sleeper', 'Sleeper'),
    )

    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10)
    deck = models.CharField(max_length=10, choices=DECK_CHOICES, default='lower')
    seat_type = models.CharField(max_length=10, choices=SEAT_TYPE_CHOICES, default='sleeper')
    row = models.PositiveIntegerField(default=1)
    column = models.PositiveIntegerField(default=1)
    is_ladies_only = models.BooleanField(default=False)
    price_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default=1.00)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('bus', 'seat_number', 'deck')
        ordering = ['deck', 'row', 'column', 'seat_number']

    def __str__(self):
        return f"{self.bus.bus_name} - Seat {self.seat_number} ({self.deck})"
