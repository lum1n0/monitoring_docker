# main/urls.py (полный файл)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    KubernetesClusterViewSet, NamespaceViewSet, PodViewSet,
    ContainerViewSet, EventViewSet, SyncKubernetesDataView, ClusterHealthView,
    DockerHostViewSet, DockerContainerViewSet, SyncDockerDataView, DockerHostHealthView,
    UnifiedContainersView, UnifiedStatsView
)

router = DefaultRouter()
# Kubernetes routes
router.register(r'clusters', KubernetesClusterViewSet, basename='cluster')
router.register(r'namespaces', NamespaceViewSet, basename='namespace')
router.register(r'pods', PodViewSet, basename='pod')
router.register(r'containers', ContainerViewSet, basename='container')
router.register(r'events', EventViewSet, basename='event')
# Docker routes
router.register(r'docker/hosts', DockerHostViewSet, basename='docker-host')
router.register(r'docker/containers', DockerContainerViewSet, basename='docker-container')

urlpatterns = [
    path('', include(router.urls)),

    # Kubernetes sync
    path('sync/', SyncKubernetesDataView.as_view(), name='sync-k8s-data'),
    path('clusters/<int:pk>/health/', ClusterHealthView.as_view(), name='cluster-health'),

    # Docker sync
    path('docker/sync/', SyncDockerDataView.as_view(), name='sync-docker-data'),
    path('docker/hosts/<int:pk>/health/', DockerHostHealthView.as_view(), name='docker-host-health'),

    # Unified views
    path('unified/containers/', UnifiedContainersView.as_view(), name='unified-containers'),
    path('unified/stats/', UnifiedStatsView.as_view(), name='unified-stats'),
]
