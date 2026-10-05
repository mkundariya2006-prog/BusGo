from django.db import models
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings

class Notification(models.Model):
    TYPE_CHOICES = (
        ('booking', 'Booking Update'),
        ('payment', 'Payment Update'),
        ('cancellation', 'Cancellation & Refund'),
        ('reminder', 'Journey Reminder'),
        ('operator', 'Operator Alert'),
        ('admin', 'Admin Notification'),
        ('system', 'System Message'),
    )

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='booking')
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"To {self.recipient.username}: {self.title}"


def notify_user(user, title, message, notification_type='system', link='', send_email_copy=True):
    """
    Creates an in-app notification and optionally dispatches an email via Django email backend.
    """
    notif = Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link
    )
    if send_email_copy and user.email:
        try:
            send_mail(
                subject=f"[BusGo] {title}",
                message=f"Hello {user.get_full_name() or user.username},\n\n{message}\n\nThank you for choosing BusGo!\nSafe Travels,\nTeam BusGo",
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@busgo.com'),
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass
    return notif
