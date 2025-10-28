from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated
from .models import ContainerError
from .serializers import ContainerErrorSerializer

from .models import KubernetesCluster, Namespace, Pod, Container, ContainerMetric, Event
from .serializers import (
    KubernetesClusterSerializer, NamespaceSerializer, PodSerializer, 
    PodListSerializer, ContainerSerializer, ContainerMetricSerializer, 
    EventSerializer, ClusterStatsSerializer
)
from .services.kubernetes_service import KubernetesService

import logging

logger = logging.getLogger(__name__)



class ContainerErrorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для просмотра ошибок контейнеров с фильтрацией по контейнеру, типу, времени и уровню.
    """
    queryset = ContainerError.objects.all()
    serializer_class = ContainerErrorSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['container_name', 'container_id', 'source', 'short_description']
    ordering_fields = ['timestamp', 'container_name', 'level']
    permission_classes = [IsAuthenticated]  # При необходимости

    def get_queryset(self):
        queryset = super().get_queryset()
        container_type = self.request.query_params.get('container_type')
        container_id = self.request.query_params.get('container_id')
        level = self.request.query_params.get('level')
        source = self.request.query_params.get('source')
        if container_type:
            queryset = queryset.filter(container_type=container_type)
        if container_id:
            queryset = queryset.filter(container_id=container_id)
        if level:
            queryset = queryset.filter(level=level)
        if source:
            queryset = queryset.filter(source__icontains=source)
        return queryset



class KubernetesClusterViewSet(viewsets.ModelViewSet):
    """ViewSet для управления кластерами"""
    queryset = KubernetesCluster.objects.all()
    serializer_class = KubernetesClusterSerializer

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Получить статистику кластера"""
        cluster = self.get_object()
        
        # Считаем статистику
        namespaces = Namespace.objects.filter(cluster=cluster)
        pods = Pod.objects.filter(namespace__cluster=cluster)
        
        stats = {
            'total_pods': pods.count(),
            'running_pods': pods.filter(status='Running').count(),
            'pending_pods': pods.filter(status='Pending').count(),
            'failed_pods': pods.filter(status='Failed').count(),
            'total_namespaces': namespaces.count(),
            'total_containers': Container.objects.filter(pod__namespace__cluster=cluster).count(),
            'unique_nodes': pods.values('node_name').distinct().count(),
            'recent_events': Event.objects.filter(
                cluster=cluster,
                last_timestamp__gte=timezone.now() - timedelta(hours=1)
            ).count(),
        }
        
        serializer = ClusterStatsSerializer(stats)
        return Response(serializer.data)


class NamespaceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра namespace"""
    queryset = Namespace.objects.all()
    serializer_class = NamespaceSerializer
    filterset_fields = ['cluster', 'status']

    def get_queryset(self):
        queryset = super().get_queryset()
        cluster_id = self.request.query_params.get('cluster_id')
        if cluster_id:
            queryset = queryset.filter(cluster_id=cluster_id)
        return queryset


class PodViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра подов"""
    queryset = Pod.objects.select_related('namespace', 'namespace__cluster').prefetch_related('containers')
    filterset_fields = ['namespace', 'status', 'node_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return PodListSerializer
        return PodSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтры
        cluster_id = self.request.query_params.get('cluster_id')
        namespace_name = self.request.query_params.get('namespace_name')
        status = self.request.query_params.get('status')
        
        if cluster_id:
            queryset = queryset.filter(namespace__cluster_id=cluster_id)
        if namespace_name:
            queryset = queryset.filter(namespace__name=namespace_name)
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """Получить логи пода"""
        pod = self.get_object()
        container_name = request.query_params.get('container')
        tail_lines = int(request.query_params.get('tail', 100))
        
        try:
            k8s_service = KubernetesService()
            logs = k8s_service.get_pod_logs(
                namespace=pod.namespace.name,
                pod_name=pod.name,
                container_name=container_name,
                tail_lines=tail_lines
            )
            return Response({'logs': logs})
        except Exception as e:
            logger.error(f"Error fetching logs: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ContainerViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра контейнеров"""
    queryset = Container.objects.select_related('pod', 'pod__namespace')
    serializer_class = ContainerSerializer
    filterset_fields = ['pod', 'is_ready', 'state']

    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Получить метрики контейнера"""
        container = self.get_object()
        
        # Параметры временного диапазона
        hours = int(request.query_params.get('hours', 1))
        time_from = timezone.now() - timedelta(hours=hours)
        
        metrics = ContainerMetric.objects.filter(
            container=container,
            timestamp__gte=time_from
        ).order_by('timestamp')
        
        serializer = ContainerMetricSerializer(metrics, many=True)
        return Response(serializer.data)


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра событий"""
    queryset = Event.objects.select_related('cluster')
    serializer_class = EventSerializer
    filterset_fields = ['cluster', 'namespace', 'event_type', 'involved_object_kind']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтр по типу события
        event_type = self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # Фильтр по времени (последние N часов)
        hours = self.request.query_params.get('hours')
        if hours:
            time_from = timezone.now() - timedelta(hours=int(hours))
            queryset = queryset.filter(last_timestamp__gte=time_from)
        
        return queryset.order_by('-last_timestamp')


class SyncKubernetesDataView(APIView):
    """API для синхронизации данных из Kubernetes"""

    def post(self, request):
        """Синхронизировать данные из Kubernetes кластера"""
        cluster_id = request.data.get('cluster_id')
        
        if not cluster_id:
            return Response(
                {'error': 'cluster_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cluster = KubernetesCluster.objects.get(id=cluster_id, is_active=True)
        except KubernetesCluster.DoesNotExist:
            return Response(
                {'error': 'Cluster not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            k8s_service = KubernetesService(cluster.config_path if cluster.config_path else None)
            
            # Синхронизация namespaces
            namespaces_data = k8s_service.get_all_namespaces()
            synced_namespaces = 0
            
            for ns_data in namespaces_data:
                namespace, created = Namespace.objects.update_or_create(
                    cluster=cluster,
                    name=ns_data['name'],
                    defaults={
                        'status': ns_data['status'],
                    }
                )
                synced_namespaces += 1
            
            # Синхронизация подов
            pods_data = k8s_service.get_all_pods()
            synced_pods = 0
            synced_containers = 0
            
            for pod_data in pods_data:
                try:
                    namespace = Namespace.objects.get(
                        cluster=cluster,
                        name=pod_data['namespace']
                    )
                    
                    pod, created = Pod.objects.update_or_create(
                        namespace=namespace,
                        name=pod_data['name'],
                        defaults={
                            'status': pod_data['status'],
                            'node_name': pod_data['node_name'],
                            'pod_ip': pod_data['pod_ip'],
                            'host_ip': pod_data['host_ip'],
                            'restart_count': pod_data['restart_count'],
                            'created_at': pod_data['created'],
                        }
                    )
                    synced_pods += 1
                    
                    # Синхронизация контейнеров
                    for container_data in pod_data['containers']:
                        Container.objects.update_or_create(
                            pod=pod,
                            name=container_data['name'],
                            defaults={
                                'image': container_data['image'],
                                'image_id': container_data.get('image_id', ''),
                                'is_ready': container_data['ready'],
                                'restart_count': container_data['restart_count'],
                                'state': container_data['state'],
                            }
                        )
                        synced_containers += 1
                        
                except Exception as e:
                    logger.error(f"Error syncing pod {pod_data['name']}: {e}")
                    continue
            
            # Синхронизация событий
            events_data = k8s_service.get_events(limit=200)
            synced_events = 0
            
            for event_data in events_data:
                Event.objects.update_or_create(
                    cluster=cluster,
                    namespace=event_data['namespace'],
                    reason=event_data['reason'],
                    involved_object_name=event_data['involved_object_name'],
                    first_timestamp=event_data['first_timestamp'],
                    defaults={
                        'event_type': event_data['type'],
                        'message': event_data['message'],
                        'involved_object_kind': event_data['involved_object_kind'],
                        'count': event_data['count'],
                        'last_timestamp': event_data['last_timestamp'],
                    }
                )
                synced_events += 1
            
            return Response({
                'status': 'success',
                'synced': {
                    'namespaces': synced_namespaces,
                    'pods': synced_pods,
                    'containers': synced_containers,
                    'events': synced_events,
                }
            })
            
        except Exception as e:
            logger.error(f"Error syncing Kubernetes data: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClusterHealthView(APIView):
    """API для проверки здоровья кластера"""

    def get(self, request, cluster_id):
        """Получить информацию о здоровье кластера"""
        try:
            cluster = KubernetesCluster.objects.get(id=cluster_id, is_active=True)
            k8s_service = KubernetesService(cluster.config_path if cluster.config_path else None)
            
            # Получаем информацию о кластере
            cluster_info = k8s_service.get_cluster_info()
            
            # Получаем информацию об узлах
            nodes = k8s_service.get_nodes()
            
            # Статистика подов
            pods = Pod.objects.filter(namespace__cluster=cluster)
            pod_stats = {
                'total': pods.count(),
                'running': pods.filter(status='Running').count(),
                'pending': pods.filter(status='Pending').count(),
                'failed': pods.filter(status='Failed').count(),
                'unknown': pods.filter(status='Unknown').count(),
            }
            
            # Последние события с предупреждениями/ошибками
            recent_issues = Event.objects.filter(
                cluster=cluster,
                event_type__in=['Warning', 'Error'],
                last_timestamp__gte=timezone.now() - timedelta(hours=1)
            ).count()
            
            return Response({
                'cluster': {
                    'id': cluster.id,
                    'name': cluster.name,
                    'api_server': cluster.api_server_url,
                    'version': cluster_info.get('version', 'unknown'),
                },
                'nodes': {
                    'total': len(nodes),
                    'ready': len([n for n in nodes if n['status'] == 'Ready']),
                    'details': nodes,
                },
                'pods': pod_stats,
                'recent_issues': recent_issues,
                'status': 'healthy' if recent_issues == 0 and pod_stats['failed'] == 0 else 'degraded',
            })
            
        except KubernetesCluster.DoesNotExist:
            return Response(
                {'error': 'Cluster not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error checking cluster health: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Добавьте импорты в начало файла
from .models import (
    KubernetesCluster, Namespace, Pod, Container, ContainerMetric, Event,
    DockerHost, DockerContainer, DockerContainerMetric
)
from .serializers import (
    KubernetesClusterSerializer, NamespaceSerializer, PodSerializer, 
    PodListSerializer, ContainerSerializer, ContainerMetricSerializer, 
    EventSerializer, ClusterStatsSerializer,
    DockerHostSerializer, DockerContainerSerializer, DockerContainerListSerializer,
    DockerContainerMetricSerializer, UnifiedContainerSerializer
)
from .services.docker_service import DockerService

# Добавьте эти ViewSets после существующих


class DockerHostViewSet(viewsets.ModelViewSet):
    """ViewSet для управления Docker хостами"""
    queryset = DockerHost.objects.all()
    serializer_class = DockerHostSerializer

    @action(detail=True, methods=['get'])
    def info(self, request, pk=None):
        """Получить информацию о Docker хосте"""
        host = self.get_object()
        
        try:
            docker_service = DockerService(host.host_url)
            info = docker_service.get_docker_info()
            return Response(info)
        except Exception as e:
            logger.error(f"Error getting Docker info: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Получить статистику Docker хоста"""
        host = self.get_object()
        
        containers = DockerContainer.objects.filter(host=host)
        
        stats = {
            'total_containers': containers.count(),
            'running_containers': containers.filter(status='running').count(),
            'paused_containers': containers.filter(status='paused').count(),
            'exited_containers': containers.filter(status='exited').count(),
            'created_containers': containers.filter(status='created').count(),
        }
        
        return Response(stats)


class DockerContainerViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра Docker контейнеров"""
    queryset = DockerContainer.objects.select_related('host')
    filterset_fields = ['host', 'status', 'state']

    def get_serializer_class(self):
        if self.action == 'list':
            return DockerContainerListSerializer
        return DockerContainerSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтры
        host_id = self.request.query_params.get('host_id')
        status = self.request.query_params.get('status')
        
        if host_id:
            queryset = queryset.filter(host_id=host_id)
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """Получить логи Docker контейнера"""
        container = self.get_object()
        tail_lines = int(request.query_params.get('tail', 100))
        
        try:
            docker_service = DockerService(container.host.host_url)
            logs = docker_service.get_container_logs(
                container_id=container.container_id,
                tail=tail_lines
            )
            return Response({'logs': logs})
        except Exception as e:
            logger.error(f"Error fetching logs: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Получить статистику Docker контейнера"""
        container = self.get_object()
        
        try:
            docker_service = DockerService(container.host.host_url)
            stats = docker_service.get_container_stats(container.container_id)
            return Response(stats)
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Получить метрики Docker контейнера"""
        container = self.get_object()
        
        # Параметры временного диапазона
        hours = int(request.query_params.get('hours', 1))
        time_from = timezone.now() - timedelta(hours=hours)
        
        metrics = DockerContainerMetric.objects.filter(
            container=container,
            timestamp__gte=time_from
        ).order_by('timestamp')
        
        serializer = DockerContainerMetricSerializer(metrics, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def action(self, request, pk=None):
        """Выполнить действие с контейнером"""
        container = self.get_object()
        action_name = request.data.get('action')
        
        if not action_name:
            return Response(
                {'error': 'action is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        allowed_actions = ['start', 'stop', 'restart', 'pause', 'unpause']
        if action_name not in allowed_actions:
            return Response(
                {'error': f'Invalid action. Allowed: {", ".join(allowed_actions)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            docker_service = DockerService(container.host.host_url)
            result = docker_service.container_action(container.container_id, action_name)
            
            if result.get('success'):
                # Обновляем статус контейнера
                self._sync_single_container(container.host, container.container_id)
                return Response(result)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error performing action: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _sync_single_container(self, host, container_id):
        """Синхронизировать один контейнер"""
        try:
            docker_service = DockerService(host.host_url)
            container_data = docker_service.get_container_details(container_id)
            
            if container_data:
                DockerContainer.objects.update_or_create(
                    host=host,
                    container_id=container_data['container_id'],
                    defaults={
                        'name': container_data['name'],
                        'image': container_data['image'],
                        'image_id': container_data['image_id'],
                        'status': container_data['status'],
                        'state': container_data['state'],
                        'restart_count': container_data['restart_count'],
                        'ports': container_data['ports'],
                        'networks': container_data['networks'],
                        'ip_address': container_data['ip_address'],
                        'created': container_data['created'],
                        'started_at': container_data['started_at'],
                        'finished_at': container_data['finished_at'],
                        'labels': container_data['labels'],
                    }
                )
        except Exception as e:
            logger.error(f"Error syncing container: {e}")


class SyncDockerDataView(APIView):
    """API для синхронизации данных из Docker"""

    def post(self, request):
        """Синхронизировать данные из Docker хоста"""
        host_id = request.data.get('host_id')
        
        if not host_id:
            return Response(
                {'error': 'host_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            host = DockerHost.objects.get(id=host_id, is_active=True)
        except DockerHost.DoesNotExist:
            return Response(
                {'error': 'Docker host not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            docker_service = DockerService(host.host_url)
            
            # Синхронизация контейнеров
            containers_data = docker_service.get_all_containers(all_containers=True)
            synced_containers = 0
            
            # Получаем ID всех контейнеров из Docker
            docker_container_ids = set()
            
            for container_data in containers_data:
                docker_container_ids.add(container_data['container_id'])
                
                container, created = DockerContainer.objects.update_or_create(
                    host=host,
                    container_id=container_data['container_id'],
                    defaults={
                        'name': container_data['name'],
                        'image': container_data['image'],
                        'image_id': container_data['image_id'],
                        'status': container_data['status'],
                        'state': container_data['state'],
                        'restart_count': container_data['restart_count'],
                        'ports': container_data['ports'],
                        'networks': container_data['networks'],
                        'ip_address': container_data['ip_address'],
                        'created': container_data['created'],
                        'started_at': container_data['started_at'],
                        'finished_at': container_data['finished_at'],
                        'labels': container_data['labels'],
                    }
                )
                synced_containers += 1
                
                # Собираем метрики для запущенных контейнеров
                if container_data['status'] == 'running':
                    try:
                        stats = docker_service.get_container_stats(container_data['container_id'])
                        if stats:
                            DockerContainerMetric.objects.create(
                                container=container,
                                **stats
                            )
                    except Exception as e:
                        logger.warning(f"Could not collect stats for {container.name}: {e}")
            
            # Удаляем контейнеры, которых больше нет в Docker
            removed_count = DockerContainer.objects.filter(host=host).exclude(
                container_id__in=docker_container_ids
            ).delete()[0]
            
            return Response({
                'status': 'success',
                'synced': {
                    'containers': synced_containers,
                    'removed': removed_count,
                }
            })
            
        except Exception as e:
            logger.error(f"Error syncing Docker data: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DockerHostHealthView(APIView):
    """API для проверки здоровья Docker хоста"""

    def get(self, request, host_id):
        """Получить информацию о здоровье Docker хоста"""
        try:
            host = DockerHost.objects.get(id=host_id, is_active=True)
            docker_service = DockerService(host.host_url)
            
            # Получаем информацию о хосте
            host_info = docker_service.get_docker_info()
            
            # Статистика контейнеров
            containers = DockerContainer.objects.filter(host=host)
            container_stats = {
                'total': containers.count(),
                'running': containers.filter(status='running').count(),
                'paused': containers.filter(status='paused').count(),
                'exited': containers.filter(status='exited').count(),
                'restarting': containers.filter(status='restarting').count(),
            }
            
            # Определяем статус здоровья
            health_status = 'healthy'
            if container_stats['restarting'] > 0:
                health_status = 'warning'
            if not host_info.get('initialized'):
                health_status = 'unhealthy'
            
            return Response({
                'host': {
                    'id': host.id,
                    'name': host.name,
                    'url': host.host_url,
                    'docker_version': host_info.get('docker_version'),
                    'os': host_info.get('os'),
                },
                'system': {
                    'cpus': host_info.get('cpus'),
                    'memory': host_info.get('memory'),
                    'architecture': host_info.get('architecture'),
                },
                'containers': container_stats,
                'images': host_info.get('images', 0),
                'status': health_status,
            })
            
        except DockerHost.DoesNotExist:
            return Response(
                {'error': 'Docker host not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error checking Docker host health: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UnifiedContainersView(APIView):
    """API для получения всех контейнеров из Kubernetes и Docker"""

    def get(self, request):
        """Получить объединенный список контейнеров"""
        unified_containers = []
        
        # Получаем Kubernetes контейнеры
        k8s_containers = Container.objects.select_related(
            'pod', 'pod__namespace', 'pod__namespace__cluster'
        ).all()
        
        for container in k8s_containers:
            unified_containers.append({
                'id': f'k8s-{container.id}',
                'name': container.name,
                'source': 'kubernetes',
                'status': container.state,
                'image': container.image,
                'created_at': container.created_at,
                'restart_count': container.restart_count,
                'host_or_node': container.pod.node_name or 'N/A',
                'ip_address': container.pod.pod_ip,
                'cluster_or_host': container.pod.namespace.cluster.name,
                'namespace': container.pod.namespace.name,
                'pod': container.pod.name,
            })
        
        # Получаем Docker контейнеры
        docker_containers = DockerContainer.objects.select_related('host').all()
        
        for container in docker_containers:
            unified_containers.append({
                'id': f'docker-{container.id}',
                'name': container.name,
                'source': 'docker',
                'status': container.status,
                'image': container.image,
                'created_at': container.created,
                'restart_count': container.restart_count,
                'host_or_node': container.host.name,
                'ip_address': container.ip_address,
                'cluster_or_host': container.host.name,
            })
        
        # Фильтрация
        source_filter = request.query_params.get('source')
        status_filter = request.query_params.get('status')
        
        if source_filter:
            unified_containers = [c for c in unified_containers if c['source'] == source_filter]
        
        if status_filter:
            unified_containers = [c for c in unified_containers if status_filter.lower() in c['status'].lower()]
        
        # Сортировка по дате создания
        unified_containers.sort(key=lambda x: x['created_at'], reverse=True)
        
        return Response({
            'count': len(unified_containers),
            'results': unified_containers
        })


class UnifiedStatsView(APIView):
    """API для получения общей статистики по всем источникам"""

    def get(self, request):
        """Получить общую статистику"""
        
        # Kubernetes статистика
        k8s_clusters = KubernetesCluster.objects.filter(is_active=True).count()
        k8s_pods = Pod.objects.count()
        k8s_containers = Container.objects.count()
        k8s_running = Pod.objects.filter(status='Running').count()
        
        # Docker статистика
        docker_hosts = DockerHost.objects.filter(is_active=True).count()
        docker_containers = DockerContainer.objects.count()
        docker_running = DockerContainer.objects.filter(status='running').count()
        
        # Общая статистика
        total_containers = k8s_containers + docker_containers
        total_running = k8s_running + docker_running
        
        return Response({
            'kubernetes': {
                'clusters': k8s_clusters,
                'pods': k8s_pods,
                'containers': k8s_containers,
                'running': k8s_running,
            },
            'docker': {
                'hosts': docker_hosts,
                'containers': docker_containers,
                'running': docker_running,
            },
            'total': {
                'sources': k8s_clusters + docker_hosts,
                'containers': total_containers,
                'running': total_running,
                'percentage_running': round((total_running / total_containers * 100) if total_containers > 0 else 0, 2),
            }
        })
