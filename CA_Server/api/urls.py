from django.urls import path
from .views import store_user_certificate
from .views import store_ca_certificate
from .views import check_user_exists
from .views import get_user_certificate
urlpatterns = [
    path("store/", store_user_certificate),
    path("storeca/", store_ca_certificate),
    path('check_user/', check_user_exists, name='check_user'),
    path('get_user_cert/',get_user_certificate, name='get_user_cert'),
]
