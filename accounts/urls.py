from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('passengers/add/', views.add_saved_passenger_view, name='add_passenger'),
    path('passengers/<int:passenger_id>/delete/', views.delete_saved_passenger_view, name='delete_passenger'),
    path('password-change/', views.change_password_view, name='change_password'),
]
