from django.db import models
from django.contrib.auth.models import User

class BusOperator(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='operator_profile')
    company_name = models.CharField(max_length=150, unique=True)
    registration_number = models.CharField(max_length=50, unique=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=4.50)
    total_ratings = models.PositiveIntegerField(default=150)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, help_text="Percentage commission")
    logo = models.ImageField(upload_to='operator_logos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['company_name']

    def __str__(self):
        return f"{self.company_name} ({self.status})"
