from django.contrib import admin
from .models import (
    KubernetesCluster, Namespace, Pod, Container, ContainerMetric, Event,
    DockerHost, DockerContainer, DockerContainerMetric
)

@admin.register(KubernetesCluster)
class KubernetesClusterAdmin(admin.ModelAdmin):
    list_display = ['name', 'api_server_url', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']


@admin.register(Namespace)
class NamespaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'cluster', 'status', 'created_at']
    list_filter = ['cluster', 'status']
    search_fields = ['name']


@admin.register(Pod)
class PodAdmin(admin.ModelAdmin):
    list_display = ['name', 'namespace', 'status', 'node_name', 'restart_count', 'created_at']
    list_filter = ['status', 'namespace__cluster', 'namespace']
    search_fields = ['name', 'node_name']
    date_hierarchy = 'created_at'


@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ['name', 'pod', 'image', 'is_ready', 'restart_count', 'state']
    list_filter = ['is_ready', 'state', 'pod__namespace__cluster']
    search_fields = ['name', 'image']


@admin.register(ContainerMetric)
class ContainerMetricAdmin(admin.ModelAdmin):
    list_display = ['container', 'timestamp', 'cpu_usage', 'memory_usage']
    list_filter = ['timestamp', 'container__pod__namespace__cluster']
    date_hierarchy = 'timestamp'


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['involved_object_name', 'event_type', 'reason', 'namespace', 'count', 'last_timestamp']
    list_filter = ['event_type', 'cluster', 'namespace', 'involved_object_kind']
    search_fields = ['reason', 'message', 'involved_object_name']
    date_hierarchy = 'last_timestamp'



# Добавьте новые admin классы после существующих

@admin.register(DockerHost)
class DockerHostAdmin(admin.ModelAdmin):
    list_display = ['name', 'host_url', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'host_url', 'description']


@admin.register(DockerContainer)
class DockerContainerAdmin(admin.ModelAdmin):
    list_display = ['name', 'host', 'status', 'image', 'restart_count', 'created']
    list_filter = ['status', 'state', 'host']
    search_fields = ['name', 'container_id', 'image']
    date_hierarchy = 'created'


@admin.register(DockerContainerMetric)
class DockerContainerMetricAdmin(admin.ModelAdmin):
    list_display = ['container', 'timestamp', 'cpu_usage_percent', 'memory_percent']
    list_filter = ['timestamp', 'container__host']
    date_hierarchy = 'timestamp'
