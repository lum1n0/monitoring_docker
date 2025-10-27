# monitor/urls.py (полный файл)
from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', obtain_auth_token),  # возвращает {"token": "..."}
    path('api/', include('main.urls')),
]
