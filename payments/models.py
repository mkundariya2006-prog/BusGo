import uuid
from django.db import models
from bookings.models import Booking

class Payment(models.Model):
    METHOD_CHOICES = (
        ('upi', 'UPI (Google Pay, PhonePe, Paytm)'),
        ('card', 'Credit / Debit Card'),
        ('netbanking', 'Net Banking'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    transaction_id = models.CharField(max_length=64, unique=True)
    payment_method = models.CharField(max_length=30, choices=METHOD_CHOICES, default='upi')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    card_last4 = models.CharField(max_length=4, blank=True)
    upi_id = models.CharField(max_length=100, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    gateway_response = models.TextField(blank=True, default='{"mock": true, "status": "APPROVED"}')
    
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = 'TXN' + uuid.uuid4().hex[:12].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_id} - ₹{self.amount} ({self.status})"
