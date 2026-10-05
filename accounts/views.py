from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import CustomerProfile, SavedPassenger
from .forms import CustomerRegistrationForm, CustomerLoginForm, CustomerProfileForm, SavedPassengerForm
from bookings.models import Booking
from routes.models import Route

def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            )
            CustomerProfile.objects.create(
                user=user,
                phone_number=form.cleaned_data['phone_number'],
                gender=form.cleaned_data['gender'],
                wallet_balance=1000.00,
                reward_points=100,
            )
            login(request, user)
            messages.success(request, f"Welcome to BusGo, {user.first_name or user.username}! Your account is ready.")
            return redirect('accounts:dashboard')
    else:
        form = CustomerRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('dashboard:admin_dashboard')
        elif hasattr(request.user, 'operator_profile'):
            return redirect('operators:operator_dashboard')
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = CustomerLoginForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # Check if input is email
            user_obj = None
            if '@' in username_or_email:
                user_obj = User.objects.filter(email__iexact=username_or_email).first()
            if not user_obj:
                user_obj = User.objects.filter(username__iexact=username_or_email).first()

            if user_obj:
                # Check if customer is blocked
                if hasattr(user_obj, 'customer_profile') and user_obj.customer_profile.is_blocked:
                    messages.error(request, "Your account has been deactivated. Please contact BusGo Support.")
                    return render(request, 'accounts/login.html', {'form': form})

                user = authenticate(request, username=user_obj.username, password=password)
                if user is not None:
                    login(request, user)
                    messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                    
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)

                    if user.is_staff or user.is_superuser:
                        return redirect('dashboard:admin_dashboard')
                    elif hasattr(user, 'operator_profile'):
                        return redirect('operators:operator_dashboard')
                    return redirect('accounts:dashboard')
                else:
                    messages.error(request, "Invalid username or password.")
            else:
                messages.error(request, "Account not found with this username or email.")
    else:
        form = CustomerLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been securely logged out.")
    return redirect('home')


@login_required
def dashboard_view(request):
    """
    Customer dashboard with bookings, wallet, reward points, matching user mockup 1.
    """
    profile, _ = CustomerProfile.objects.get_or_create(
        user=request.user,
        defaults={'wallet_balance': 1500.00, 'reward_points': 250}
    )

    bookings = Booking.objects.filter(customer=request.user).select_related(
        'schedule', 'schedule__route', 'schedule__route__origin', 'schedule__route__destination',
        'schedule__bus', 'schedule__bus__operator'
    ).order_by('-created_at')

    today = timezone.localdate()
    upcoming_bookings = [b for b in bookings if b.booking_status == 'confirmed' and b.schedule.departure_date >= today]
    completed_bookings = [b for b in bookings if b.booking_status == 'completed' or (b.booking_status == 'confirmed' and b.schedule.departure_date < today)]
    cancelled_bookings = [b for b in bookings if b.booking_status == 'cancelled']

    popular_routes = Route.objects.filter(is_active=True)[:6]

    context = {
        'profile': profile,
        'recent_bookings': bookings[:5],
        'upcoming_bookings': upcoming_bookings,
        'completed_bookings': completed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'popular_routes': popular_routes,
    }
    return render(request, 'accounts/dashboard.html', context)


@login_required
def profile_view(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save()
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            messages.success(request, "Your profile details have been updated successfully.")
            return redirect('accounts:profile')
    else:
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        }
        form = CustomerProfileForm(instance=profile, initial=initial_data)

    saved_passengers = profile.saved_passengers.all()
    passenger_form = SavedPassengerForm()

    context = {
        'form': form,
        'profile': profile,
        'saved_passengers': saved_passengers,
        'passenger_form': passenger_form,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def add_saved_passenger_view(request):
    if request.method == 'POST':
        profile = request.user.customer_profile
        form = SavedPassengerForm(request.POST)
        if form.is_valid():
            p = form.save(commit=False)
            p.customer = profile
            p.save()
            messages.success(request, f"Saved passenger {p.name} added.")
        else:
            messages.error(request, "Could not add passenger. Please check inputs.")
    return redirect('accounts:profile')


@login_required
def delete_saved_passenger_view(request, passenger_id):
    passenger = get_object_or_404(SavedPassenger, id=passenger_id, customer__user=request.user)
    passenger.delete()
    messages.success(request, "Saved passenger removed.")
    return redirect('accounts:profile')


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been updated securely.")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the error below.")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})
