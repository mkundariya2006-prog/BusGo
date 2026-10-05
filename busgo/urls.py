from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from buses.views import home_view

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', home_view, name='home'),
    path('accounts/', include('accounts.urls')),
    path('buses/', include('buses.urls')),
    path('bookings/', include('bookings.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('operators/', include('operators.urls')),
    path('api/', include('busgo.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
