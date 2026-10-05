from django.db import models
from buses.models import Bus

class City(models.Model):
    name = models.CharField(max_length=100, unique=True)
    district = models.CharField(max_length=100, blank=True, default='')
    state = models.CharField(max_length=100, default='Gujarat')
    is_popular = models.BooleanField(default=False)
    image_url = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name_plural = "Cities"
        ordering = ['name']

    def __str__(self):
        if self.district:
            return f"{self.name} ({self.district}), {self.state}"
        return f"{self.name}, {self.state}"


class Route(models.Model):
    origin = models.ForeignKey(City, on_delete=models.CASCADE, related_name='departures')
    destination = models.ForeignKey(City, on_delete=models.CASCADE, related_name='arrivals')
    distance_km = models.PositiveIntegerField(default=350)
    estimated_duration_hours = models.DecimalField(max_digits=4, decimal_places=1, default=6.5)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('origin', 'destination')
        ordering = ['origin__name', 'destination__name']

    def __str__(self):
        return f"{self.origin.name} → {self.destination.name}"


class BoardingPoint(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='boarding_points')
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='boarding_points')
    location_name = models.CharField(max_length=150)
    landmark = models.CharField(max_length=150, blank=True)
    time_offset_minutes = models.IntegerField(default=0, help_text="Minutes relative to departure time (e.g. 0, 15, 30)")
    contact_number = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['time_offset_minutes']

    def __str__(self):
        return f"{self.location_name} ({self.city.name})"


class DroppingPoint(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='dropping_points')
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='dropping_points')
    location_name = models.CharField(max_length=150)
    landmark = models.CharField(max_length=150, blank=True)
    time_offset_minutes = models.IntegerField(default=0, help_text="Minutes relative to arrival time")
    contact_number = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['time_offset_minutes']

    def __str__(self):
        return f"{self.location_name} ({self.city.name})"


class BusSchedule(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='schedules')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='schedules')
    departure_date = models.DateField(db_index=True)
    departure_time = models.TimeField()
    arrival_date = models.DateField()
    arrival_time = models.TimeField()
    base_price = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['departure_date', 'departure_time']

    def __str__(self):
        return f"{self.bus.bus_name} | {self.route} | {self.departure_date} {self.departure_time.strftime('%H:%M')}"

    @property
    def duration_display(self):
        import datetime
        dt1 = datetime.datetime.combine(self.departure_date, self.departure_time)
        dt2 = datetime.datetime.combine(self.arrival_date, self.arrival_time)
        diff = dt2 - dt1
        hours, remainder = divmod(int(diff.total_seconds()), 3600)
        minutes = remainder // 60
        return f"{hours}h {minutes}m"
