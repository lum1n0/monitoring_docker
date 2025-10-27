from rest_framework import serializers
from .models import KubernetesCluster, Namespace, Pod, Container, ContainerMetric, Event, DockerHost, DockerContainer, DockerContainerMetric


class KubernetesClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = KubernetesCluster
        fields = '__all__'


class NamespaceSerializer(serializers.ModelSerializer):
    cluster_name = serializers.CharField(source='cluster.name', read_only=True)
    pod_count = serializers.SerializerMethodField()

    class Meta:
        model = Namespace
        fields = ['id', 'cluster', 'cluster_name', 'name', 'status', 'pod_count', 'created_at', 'updated_at']

    def get_pod_count(self, obj):
        return obj.pods.count()


class ContainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Container
        fields = ['id', 'name', 'image', 'image_id', 'is_ready', 'restart_count', 'state', 'created_at', 'updated_at']


class PodSerializer(serializers.ModelSerializer):
    namespace_name = serializers.CharField(source='namespace.name', read_only=True)
    cluster_name = serializers.CharField(source='namespace.cluster.name', read_only=True)
    containers = ContainerSerializer(many=True, read_only=True)
    container_count = serializers.SerializerMethodField()

    class Meta:
        model = Pod
        fields = [
            'id', 'namespace', 'namespace_name', 'cluster_name', 'name', 'status', 
            'node_name', 'pod_ip', 'host_ip', 'restart_count', 'created_at', 
            'last_restart', 'updated_at', 'containers', 'container_count'
        ]

    def get_container_count(self, obj):
        return obj.containers.count()


class PodListSerializer(serializers.ModelSerializer):
    """Упрощенная версия для списков"""
    namespace_name = serializers.CharField(source='namespace.name', read_only=True)
    cluster_name = serializers.CharField(source='namespace.cluster.name', read_only=True)
    container_count = serializers.SerializerMethodField()

    class Meta:
        model = Pod
        fields = [
            'id', 'namespace_name', 'cluster_name', 'name', 'status', 
            'node_name', 'restart_count', 'created_at', 'container_count'
        ]

    def get_container_count(self, obj):
        return obj.containers.count()


class ContainerMetricSerializer(serializers.ModelSerializer):
    container_name = serializers.CharField(source='container.name', read_only=True)
    pod_name = serializers.CharField(source='container.pod.name', read_only=True)
    
    # Форматированные значения для удобства
    cpu_usage_cores = serializers.SerializerMethodField()
    memory_usage_mb = serializers.SerializerMethodField()

    class Meta:
        model = ContainerMetric
        fields = [
            'id', 'container', 'container_name', 'pod_name', 'timestamp',
            'cpu_usage', 'cpu_usage_cores', 'memory_usage', 'memory_usage_mb',
            'network_rx_bytes', 'network_tx_bytes', 'disk_read_bytes', 'disk_write_bytes'
        ]

    def get_cpu_usage_cores(self, obj):
        """Конвертация из миллиядер в ядра"""
        return round(obj.cpu_usage / 1000, 3)

    def get_memory_usage_mb(self, obj):
        """Конвертация из байт в мегабайты"""
        return round(obj.memory_usage / (1024 * 1024), 2)


class EventSerializer(serializers.ModelSerializer):
    cluster_name = serializers.CharField(source='cluster.name', read_only=True)
    time_since = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'cluster', 'cluster_name', 'namespace', 'event_type', 'reason',
            'message', 'involved_object_kind', 'involved_object_name', 'count',
            'first_timestamp', 'last_timestamp', 'time_since', 'created_at'
        ]

    def get_time_since(self, obj):
        """Время с последнего события"""
        from django.utils import timezone
        delta = timezone.now() - obj.last_timestamp
        if delta.days > 0:
            return f"{delta.days}д назад"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600}ч назад"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60}м назад"
        else:
            return "только что"


class ClusterStatsSerializer(serializers.Serializer):
    """Сериализатор для общей статистики кластера"""
    total_pods = serializers.IntegerField()
    running_pods = serializers.IntegerField()
    pending_pods = serializers.IntegerField()
    failed_pods = serializers.IntegerField()
    total_namespaces = serializers.IntegerField()
    total_containers = serializers.IntegerField()
    unique_nodes = serializers.IntegerField()
    recent_events = serializers.IntegerField()


# Добавьте в конец файла

class DockerHostSerializer(serializers.ModelSerializer):
    container_count = serializers.SerializerMethodField()
    running_containers = serializers.SerializerMethodField()

    class Meta:
        model = DockerHost
        fields = '__all__'

    def get_container_count(self, obj):
        return obj.containers.count()

    def get_running_containers(self, obj):
        return obj.containers.filter(status='running').count()


class DockerContainerSerializer(serializers.ModelSerializer):
    host_name = serializers.CharField(source='host.name', read_only=True)
    uptime = serializers.SerializerMethodField()
    memory_usage_mb = serializers.SerializerMethodField()

    class Meta:
        model = DockerContainer
        fields = '__all__'

    def get_uptime(self, obj):
        if obj.started_at and obj.status == 'running':
            from django.utils import timezone
            delta = timezone.now() - obj.started_at
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}д {hours}ч"
            elif hours > 0:
                return f"{hours}ч {minutes}м"
            else:
                return f"{minutes}м"
        return "N/A"

    def get_memory_usage_mb(self, obj):
        # Получаем последнюю метрику
        latest_metric = obj.metrics.first()
        if latest_metric:
            return round(latest_metric.memory_usage / (1024 * 1024), 2)
        return 0


class DockerContainerListSerializer(serializers.ModelSerializer):
    """Упрощенная версия для списков"""
    host_name = serializers.CharField(source='host.name', read_only=True)

    class Meta:
        model = DockerContainer
        fields = [
            'id', 'container_id', 'name', 'image', 'status', 'state',
            'host_name', 'ip_address', 'restart_count', 'created', 'started_at'
        ]


class DockerContainerMetricSerializer(serializers.ModelSerializer):
    container_name = serializers.CharField(source='container.name', read_only=True)

    class Meta:
        model = DockerContainerMetric
        fields = '__all__'


class UnifiedContainerSerializer(serializers.Serializer):
    """Унифицированный сериализатор для отображения контейнеров из разных источников"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    source = serializers.CharField()  # 'kubernetes' or 'docker'
    status = serializers.CharField()
    image = serializers.CharField()
    created_at = serializers.DateTimeField()
    restart_count = serializers.IntegerField()
    host_or_node = serializers.CharField()
    ip_address = serializers.CharField(allow_null=True)
