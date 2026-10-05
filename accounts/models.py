from django.db import models
from django.contrib.auth.models import User

class CustomerProfile(models.Model):
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone_number = models.CharField(max_length=15, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='male')
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=1500.00)
    store_credit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reward_points = models.IntegerField(default=350)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.phone_number})"


class SavedPassenger(models.Model):
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

    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='saved_passengers')
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    id_type = models.CharField(max_length=30, choices=ID_TYPE_CHOICES, default='aadhaar')
    id_number = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.gender}, {self.age})"
