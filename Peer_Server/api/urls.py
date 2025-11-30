from django.urls import path
from .views import register_peer
from .views import heartbeat
from .views import list_peers

urlpatterns = [
    path("register/", register_peer),
    path("heartbeat/", heartbeat),
    path("peers/", list_peers),
]
