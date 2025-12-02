from django.urls import path
from . import views

urlpatterns = [
    path("store/", views.store_user_certificate),
    path("storeca/", views.store_ca_certificate),
    path("get_ca_cert/", views.get_ca_certificate),
    path("get_ca_certificate/", views.get_ca_certificate),
    path('check_user/', views.check_user_exists, name='check_user'),
    path('get_user_cert/', views.get_user_certificate, name='get_user_cert'),
    path('challenge', views.request_challenge, name='request_challenge'),
    path('login_secure', views.login_secure, name='login_secure'),
]