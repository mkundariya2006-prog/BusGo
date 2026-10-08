from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin/customers/', views.admin_customers_view, name='admin_customers'),
    path('admin/customers/<int:profile_id>/toggle-block/', views.admin_toggle_customer_block, name='admin_toggle_customer_block'),
    path('admin/operators/', views.admin_operators_view, name='admin_operators'),
    path('admin/buses/', views.admin_buses_view, name='admin_buses'),
    path('admin/routes/', views.admin_routes_view, name='admin_routes'),
    path('admin/schedules/', views.admin_schedules_view, name='admin_schedules'),
    path('admin/schedules/<int:schedule_id>/cancel/', views.admin_cancel_schedule_view, name='admin_cancel_schedule'),
    path('admin/bookings/', views.admin_bookings_view, name='admin_bookings'),
    path('admin/reports/', views.admin_reports_view, name='admin_reports'),
]
