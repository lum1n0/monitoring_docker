import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from django.conf import settings
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class KubernetesService:
    """Сервис для работы с Kubernetes API"""

    def __init__(self, cluster_config_path: Optional[str] = None):
        """
        Инициализация клиента Kubernetes
        
        Args:
            cluster_config_path: Путь к файлу конфигурации кластера
        """
        try:
            if settings.K8S_IN_CLUSTER:
                # Загрузка конфигурации из Pod (когда приложение запущено в кластере)
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes configuration")
            elif cluster_config_path:
                # Загрузка конфигурации из указанного файла
                config.load_kube_config(config_file=cluster_config_path)
                logger.info(f"Loaded Kubernetes configuration from {cluster_config_path}")
            else:
                # Загрузка конфигурации по умолчанию (~/.kube/config)
                config.load_kube_config()
                logger.info("Loaded default Kubernetes configuration")

            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.metrics_api = client.CustomObjectsApi()
            self.initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            self.initialized = False
            raise

    def get_cluster_info(self) -> Dict:
        """Получить информацию о кластере"""
        try:
            version = client.VersionApi().get_code()
            return {
                'version': version.git_version,
                'platform': version.platform,
                'initialized': self.initialized
            }
        except ApiException as e:
            logger.error(f"Error fetching cluster info: {e}")
            return {'error': str(e), 'initialized': False}

    def get_all_namespaces(self) -> List[Dict]:
        """Получить все namespace в кластере"""
        try:
            namespaces = self.core_v1.list_namespace()
            return [
                {
                    'name': ns.metadata.name,
                    'status': ns.status.phase,
                    'created': ns.metadata.creation_timestamp,
                    'labels': ns.metadata.labels or {},
                }
                for ns in namespaces.items
            ]
        except ApiException as e:
            logger.error(f"Error fetching namespaces: {e}")
            return []

    def get_all_pods(self, namespace: Optional[str] = None) -> List[Dict]:
        """
        Получить все поды в кластере или в конкретном namespace
        
        Args:
            namespace: Имя namespace (если None, то все поды)
        """
        try:
            if namespace:
                pods = self.core_v1.list_namespaced_pod(namespace=namespace)
            else:
                pods = self.core_v1.list_pod_for_all_namespaces()

            result = []
            for pod in pods.items:
                containers_info = []
                restart_count = 0

                if pod.status.container_statuses:
                    for container_status in pod.status.container_statuses:
                        restart_count += container_status.restart_count
                        
                        # Определение состояния контейнера
                        state = 'unknown'
                        if container_status.state.running:
                            state = 'running'
                        elif container_status.state.waiting:
                            state = 'waiting'
                        elif container_status.state.terminated:
                            state = 'terminated'

                        containers_info.append({
                            'name': container_status.name,
                            'image': container_status.image,
                            'image_id': container_status.image_id,
                            'ready': container_status.ready,
                            'restart_count': container_status.restart_count,
                            'state': state,
                        })

                pod_data = {
                    'name': pod.metadata.name,
                    'namespace': pod.metadata.namespace,
                    'status': pod.status.phase,
                    'node_name': pod.spec.node_name,
                    'pod_ip': pod.status.pod_ip,
                    'host_ip': pod.status.host_ip,
                    'created': pod.metadata.creation_timestamp,
                    'restart_count': restart_count,
                    'containers': containers_info,
                    'labels': pod.metadata.labels or {},
                }
                result.append(pod_data)

            return result

        except ApiException as e:
            logger.error(f"Error fetching pods: {e}")
            return []

    def get_pod_details(self, namespace: str, pod_name: str) -> Optional[Dict]:
        """
        Получить детальную информацию о конкретном поде
        
        Args:
            namespace: Имя namespace
            pod_name: Имя пода
        """
        try:
            pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            containers = []
            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    state = 'unknown'
                    if cs.state.running:
                        state = 'running'
                    elif cs.state.waiting:
                        state = 'waiting'
                    elif cs.state.terminated:
                        state = 'terminated'

                    containers.append({
                        'name': cs.name,
                        'image': cs.image,
                        'ready': cs.ready,
                        'restart_count': cs.restart_count,
                        'state': state,
                    })

            return {
                'name': pod.metadata.name,
                'namespace': pod.metadata.namespace,
                'status': pod.status.phase,
                'node_name': pod.spec.node_name,
                'pod_ip': pod.status.pod_ip,
                'host_ip': pod.status.host_ip,
                'created': pod.metadata.creation_timestamp,
                'labels': pod.metadata.labels or {},
                'containers': containers,
            }

        except ApiException as e:
            logger.error(f"Error fetching pod details: {e}")
            return None

    def get_pod_logs(self, namespace: str, pod_name: str, container_name: Optional[str] = None, 
                     tail_lines: int = 100) -> str:
        """
        Получить логи пода
        
        Args:
            namespace: Имя namespace
            pod_name: Имя пода
            container_name: Имя контейнера (если None, то первый контейнер)
            tail_lines: Количество последних строк
        """
        try:
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container_name,
                tail_lines=tail_lines
            )
            return logs
        except ApiException as e:
            logger.error(f"Error fetching pod logs: {e}")
            return f"Error: {str(e)}"

    def get_events(self, namespace: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        Получить события кластера
        
        Args:
            namespace: Имя namespace (если None, то все события)
            limit: Максимальное количество событий
        """
        try:
            if namespace:
                events = self.core_v1.list_namespaced_event(namespace=namespace, limit=limit)
            else:
                events = self.core_v1.list_event_for_all_namespaces(limit=limit)

            result = []
            for event in events.items:
                result.append({
                    'namespace': event.metadata.namespace,
                    'type': event.type,
                    'reason': event.reason,
                    'message': event.message,
                    'involved_object_kind': event.involved_object.kind,
                    'involved_object_name': event.involved_object.name,
                    'count': event.count or 1,
                    'first_timestamp': event.first_timestamp,
                    'last_timestamp': event.last_timestamp,
                })
            
            return result

        except ApiException as e:
            logger.error(f"Error fetching events: {e}")
            return []

    def get_nodes(self) -> List[Dict]:
        """Получить информацию о узлах кластера"""
        try:
            nodes = self.core_v1.list_node()
            result = []
            
            for node in nodes.items:
                # Статус узла
                conditions = {}
                if node.status.conditions:
                    for condition in node.status.conditions:
                        conditions[condition.type] = condition.status

                result.append({
                    'name': node.metadata.name,
                    'status': 'Ready' if conditions.get('Ready') == 'True' else 'NotReady',
                    'roles': self._get_node_roles(node.metadata.labels or {}),
                    'version': node.status.node_info.kubelet_version,
                    'os': node.status.node_info.os_image,
                    'kernel': node.status.node_info.kernel_version,
                    'capacity': {
                        'cpu': node.status.capacity.get('cpu'),
                        'memory': node.status.capacity.get('memory'),
                        'pods': node.status.capacity.get('pods'),
                    },
                    'allocatable': {
                        'cpu': node.status.allocatable.get('cpu'),
                        'memory': node.status.allocatable.get('memory'),
                        'pods': node.status.allocatable.get('pods'),
                    },
                    'conditions': conditions,
                    'created': node.metadata.creation_timestamp,
                })
            
            return result

        except ApiException as e:
            logger.error(f"Error fetching nodes: {e}")
            return []

    def _get_node_roles(self, labels: Dict) -> List[str]:
        """Извлечь роли узла из меток"""
        roles = []
        for label_key in labels:
            if label_key.startswith('node-role.kubernetes.io/'):
                role = label_key.replace('node-role.kubernetes.io/', '')
                roles.append(role)
        return roles if roles else ['worker']

    def get_pod_metrics(self, namespace: str, pod_name: str) -> Optional[Dict]:
        """
        Получить метрики пода через Metrics API
        Требует установленного metrics-server в кластере
        
        Args:
            namespace: Имя namespace
            pod_name: Имя пода
        """
        try:
            metrics = self.metrics_api.get_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods",
                name=pod_name
            )
            return metrics
        except ApiException as e:
            logger.warning(f"Error fetching pod metrics (metrics-server may not be installed): {e}")
            return None

    def get_all_pod_metrics(self, namespace: Optional[str] = None) -> List[Dict]:
        """
        Получить метрики всех подов
        
        Args:
            namespace: Имя namespace (если None, то все поды)
        """
        try:
            if namespace:
                metrics = self.metrics_api.list_namespaced_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    namespace=namespace,
                    plural="pods"
                )
            else:
                metrics = self.metrics_api.list_cluster_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    plural="pods"
                )
            
            return metrics.get('items', [])

        except ApiException as e:
            logger.warning(f"Error fetching pod metrics: {e}")
            return []
