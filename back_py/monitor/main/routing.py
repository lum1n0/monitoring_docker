from django.urls import path
from .consumers import DockerMetricsConsumer

websocket_urlpatterns = [
    path('ws/docker/metrics/', DockerMetricsConsumer.as_asgi()),
]
