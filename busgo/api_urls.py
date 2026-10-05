from django.urls import path
from . import api_views

app_name = 'api'

urlpatterns = [
    path('auth/login/', api_views.AuthLoginAPIView.as_view(), name='api_login'),
    path('auth/register/', api_views.AuthRegisterAPIView.as_view(), name='api_register'),
    path('buses/search/', api_views.BusSearchAPIView.as_view(), name='api_bus_search'),
    path('buses/<int:id>/', api_views.BusDetailAPIView.as_view(), name='api_bus_detail'),
    path('cities/', api_views.CitiesListAPIView.as_view(), name='api_cities'),
    path('routes/', api_views.RoutesListAPIView.as_view(), name='api_routes'),
    path('schedules/', api_views.SchedulesListAPIView.as_view(), name='api_schedules'),
    path('seats/<int:schedule_id>/', api_views.ScheduleSeatsAPIView.as_view(), name='api_schedule_seats'),
    path('bookings/', api_views.BookingsListCreateAPIView.as_view(), name='api_bookings'),
    path('bookings/<int:id>/', api_views.BookingDetailAPIView.as_view(), name='api_booking_detail'),
    path('bookings/<int:id>/cancel/', api_views.BookingCancelAPIView.as_view(), name='api_booking_cancel'),
    path('payments/', api_views.PaymentCreateAPIView.as_view(), name='api_payments'),
    path('tickets/<str:booking_id>/', api_views.TicketDetailAPIView.as_view(), name='api_ticket_detail'),
]
