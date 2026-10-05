from django.urls import path
from . import views

app_name = 'buses'

urlpatterns = [
    path('search/', views.search_buses_view, name='search'),
    path('schedule/<int:schedule_id>/seats/', views.get_schedule_seats_api, name='schedule_seats'),
]
