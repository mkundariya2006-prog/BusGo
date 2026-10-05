from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('select-seats/<int:schedule_id>/', views.select_seats_view, name='select_seats'),
    path('passenger-details/<int:schedule_id>/', views.passenger_details_view, name='passenger_details'),
    path('payment/<str:booking_id>/', views.payment_view, name='payment'),
    path('ticket/<str:booking_id>/', views.ticket_view, name='ticket'),
    path('ticket/<str:booking_id>/download/', views.download_ticket_pdf, name='download_ticket'),
    path('cancel/<str:booking_id>/', views.cancel_booking_view, name='cancel_booking'),
]
