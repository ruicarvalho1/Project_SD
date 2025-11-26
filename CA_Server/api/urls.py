from django.urls import path
from .views import store_user_certificate

urlpatterns = [
    path("store/", store_user_certificate),
]
