from django.urls import path
from . import views

app_name = 'operators'

urlpatterns = [
    path('dashboard/', views.operator_dashboard_view, name='operator_dashboard'),
    path('buses/', views.operator_buses_view, name='operator_buses'),
    path('schedules/', views.operator_schedules_view, name='operator_schedules'),
    path('manifest/<int:schedule_id>/', views.operator_passenger_manifest_view, name='operator_manifest'),
]
