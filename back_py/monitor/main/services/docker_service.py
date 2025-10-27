import logging
import docker
from docker.errors import DockerException, NotFound, APIError
from typing import Dict, List, Optional
from datetime import datetime
import platform
import os

logger = logging.getLogger(__name__)


class DockerService:
    """Универсальный сервис для работы с Docker API на разных платформах"""

    # Предопределенные варианты подключения
    CONNECTION_MODES = {
        'auto': None,  # Автоопределение
        'env': None,  # Через переменные окружения
        'npipe': 'npipe:////./pipe/docker_engine',  # Windows Named Pipe
        'unix': 'unix:///var/run/docker.sock',  # Unix socket
        'tcp': 'tcp://127.0.0.1:2375',  # TCP (небезопасно)
    }

    def __init__(self, base_url: Optional[str] = None):
        """
        Инициализация клиента Docker с автоматическим определением платформы
        
        Args:
            base_url: URL для подключения к Docker daemon
                     None или '' - автоопределение (рекомендуется)
                     'auto' - автоопределение на основе платформы
                     'env' - использовать docker.from_env()
                     'npipe:////./pipe/docker_engine' - Windows Named Pipe
                     'unix:///var/run/docker.sock' - Unix socket
                     'tcp://127.0.0.1:2375' - TCP подключение
        """
        self.base_url = base_url
        self.platform = platform.system().lower()
        self.connection_method = None
        
        try:
            self._initialize_client(base_url)
            
            # Проверка подключения
            self.client.ping()
            self.initialized = True
            
            logger.info(
                f"Successfully connected to Docker "
                f"(platform: {self.platform}, method: {self.connection_method})"
            )
            
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.initialized = False
            raise

    def _initialize_client(self, base_url: Optional[str]):
        """Инициализация клиента с умным определением способа подключения"""
        
        # Случай 1: Пустой или None - полное автоопределение
        if not base_url or base_url == '' or base_url == 'auto':
            self.connection_method = 'auto-detected'
            self.client = self._auto_detect_connection()
            self.api_client = self.client.api
            return
        
        # Случай 2: Явное указание 'env'
        if base_url == 'env':
            self.connection_method = 'environment'
            self.client = docker.from_env()
            self.api_client = self.client.api
            return
        
        # Случай 3: Конкретный URL
        self.connection_method = f'custom ({base_url})'
        self.client = docker.DockerClient(base_url=base_url)
        self.api_client = self.client.api

    def _auto_detect_connection(self):
        """
        Автоматическое определение оптимального способа подключения
        на основе платформы и доступности
        """
        
        # Пробуем стандартное подключение через переменные окружения
        try:
            client = docker.from_env()
            client.ping()
            logger.info("Auto-detected: docker.from_env()")
            return client
        except DockerException as e:
            logger.debug(f"docker.from_env() failed: {e}")
        
        # Пробуем платформо-специфичные способы
        if self.platform == 'windows':
            return self._try_windows_connections()
        elif self.platform in ['linux', 'darwin']:  # Linux или macOS
            return self._try_unix_connections()
        else:
            raise DockerException(
                f"Unsupported platform: {self.platform}. "
                "Please specify base_url explicitly."
            )

    def _try_windows_connections(self):
        """Попытка подключения на Windows в порядке приоритета"""
        
        # 1. Named Pipe (стандартный для Docker Desktop)
        try:
            client = docker.DockerClient(base_url='npipe:////./pipe/docker_engine')
            client.ping()
            logger.info("Auto-detected: Windows Named Pipe")
            return client
        except DockerException as e:
            logger.debug(f"Named Pipe failed: {e}")
        
        # 2. TCP (если настроен)
        try:
            client = docker.DockerClient(base_url='tcp://127.0.0.1:2375')
            client.ping()
            logger.warning(
                "Auto-detected: TCP connection. "
                "This is insecure for production!"
            )
            return client
        except DockerException as e:
            logger.debug(f"TCP failed: {e}")
        
        raise DockerException(
            "Could not connect to Docker on Windows. "
            "Please ensure Docker Desktop is running."
        )

    def _try_unix_connections(self):
        """Попытка подключения на Unix-подобных системах"""
        
        # Стандартный Unix socket
        socket_paths = [
            'unix:///var/run/docker.sock',  # Стандартный путь
            'unix:///run/docker.sock',  # Альтернативный путь
        ]
        
        for socket_path in socket_paths:
            # Проверяем существование файла
            file_path = socket_path.replace('unix://', '')
            if os.path.exists(file_path):
                try:
                    client = docker.DockerClient(base_url=socket_path)
                    client.ping()
                    logger.info(f"Auto-detected: {socket_path}")
                    return client
                except DockerException as e:
                    logger.debug(f"{socket_path} failed: {e}")
        
        raise DockerException(
            "Could not connect to Docker socket. "
            "Please ensure Docker is running and you have permissions."
        )

    @classmethod
    def test_connection(cls, base_url: Optional[str] = None) -> Dict:
        """
        Тестирование подключения без создания экземпляра
        
        Returns:
            Dict с информацией о результате подключения
        """
        try:
            service = cls(base_url)
            info = service.get_docker_info()
            return {
                'success': True,
                'platform': service.platform,
                'connection_method': service.connection_method,
                'docker_version': info.get('docker_version'),
                'api_version': info.get('api_version'),
                'containers': info.get('containers'),
                'containers_running': info.get('containers_running'),
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'platform': platform.system().lower(),
            }

    def get_connection_info(self) -> Dict:
        """Получить информацию о текущем подключении"""
        return {
            'platform': self.platform,
            'connection_method': self.connection_method,
            'base_url': self.base_url,
            'initialized': self.initialized,
        }

    def get_docker_info(self) -> Dict:
        """Получить информацию о Docker хосте"""
        try:
            info = self.client.info()
            version = self.client.version()
            return {
                'docker_version': version.get('Version'),
                'api_version': version.get('ApiVersion'),
                'os': info.get('OperatingSystem'),
                'architecture': info.get('Architecture'),
                'cpus': info.get('NCPU'),
                'memory': info.get('MemTotal'),
                'containers': info.get('Containers'),
                'containers_running': info.get('ContainersRunning'),
                'containers_paused': info.get('ContainersPaused'),
                'containers_stopped': info.get('ContainersStopped'),
                'images': info.get('Images'),
                'initialized': self.initialized,
                'connection_info': self.get_connection_info(),
            }
        except DockerException as e:
            logger.error(f"Error fetching Docker info: {e}")
            return {
                'error': str(e),
                'initialized': False,
                'connection_info': self.get_connection_info(),
            }

    def get_all_containers(self, all_containers: bool = True) -> List[Dict]:
        """
        Получить все контейнеры
        
        Args:
            all_containers: Если True, возвращает все контейнеры, иначе только запущенные
        """
        try:
            containers = self.client.containers.list(all=all_containers)
            result = []
            
            for container in containers:
                container_info = self._parse_container_info(container)
                result.append(container_info)
            
            return result
        except DockerException as e:
            logger.error(f"Error fetching containers: {e}")
            return []

    def get_container_details(self, container_id: str) -> Optional[Dict]:
        """
        Получить детальную информацию о конкретном контейнере
        
        Args:
            container_id: ID или имя контейнера
        """
        try:
            container = self.client.containers.get(container_id)
            return self._parse_container_info(container, detailed=True)
        except NotFound:
            logger.error(f"Container {container_id} not found")
            return None
        except DockerException as e:
            logger.error(f"Error fetching container details: {e}")
            return None

    def _parse_container_info(self, container, detailed: bool = False) -> Dict:
        """Парсинг информации о контейнере"""
        attrs = container.attrs
        
        # Базовая информация
        info = {
            'container_id': container.id,
            'short_id': container.short_id,
            'name': container.name,
            'image': container.image.tags[0] if container.image.tags else container.image.id,
            'image_id': container.image.id,
            'status': container.status,
            'state': attrs['State']['Status'],
            'created': attrs['Created'],
            'started_at': attrs['State'].get('StartedAt'),
            'finished_at': attrs['State'].get('FinishedAt'),
            'restart_count': attrs['RestartCount'],
            'labels': attrs['Config'].get('Labels', {}),
        }

        # Сетевая информация
        networks = attrs.get('NetworkSettings', {}).get('Networks', {})
        network_list = []
        ip_address = None
        
        for network_name, network_data in networks.items():
            network_list.append(network_name)
            if not ip_address:
                ip_address = network_data.get('IPAddress')
        
        info['networks'] = network_list
        info['ip_address'] = ip_address

        # Порты
        ports = attrs.get('NetworkSettings', {}).get('Ports', {})
        port_mappings = {}
        for container_port, host_bindings in ports.items():
            if host_bindings:
                port_mappings[container_port] = [
                    f"{binding['HostIp']}:{binding['HostPort']}" 
                    for binding in host_bindings
                ]
        info['ports'] = port_mappings

        if detailed:
            # Дополнительная детальная информация
            info['command'] = attrs['Config'].get('Cmd', [])
            info['entrypoint'] = attrs['Config'].get('Entrypoint', [])
            info['env'] = attrs['Config'].get('Env', [])
            info['working_dir'] = attrs['Config'].get('WorkingDir')
            info['mounts'] = [
                {
                    'type': mount['Type'],
                    'source': mount['Source'],
                    'destination': mount['Destination'],
                    'mode': mount.get('Mode', ''),
                    'rw': mount.get('RW', True),
                }
                for mount in attrs.get('Mounts', [])
            ]

        return info

    def get_container_stats(self, container_id: str) -> Optional[Dict]:
        """
        Получить статистику контейнера
        
        Args:
            container_id: ID или имя контейнера
        """
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # Парсинг статистики
            cpu_stats = stats['cpu_stats']
            precpu_stats = stats['precpu_stats']
            memory_stats = stats['memory_stats']
            networks = stats.get('networks', {})
            blkio_stats = stats.get('blkio_stats', {})

            # Расчёт CPU usage
            cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
            system_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']
            cpu_percent = 0.0
            
            if system_delta > 0 and cpu_delta > 0:
                cpu_count = cpu_stats.get('online_cpus', len(cpu_stats['cpu_usage'].get('percpu_usage', [1])))
                cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0

            # Память
            memory_usage = memory_stats.get('usage', 0)
            memory_limit = memory_stats.get('limit', 1)
            memory_percent = (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0.0

            # Сеть
            network_rx_bytes = 0
            network_tx_bytes = 0
            network_rx_packets = 0
            network_tx_packets = 0
            
            for network_data in networks.values():
                network_rx_bytes += network_data.get('rx_bytes', 0)
                network_tx_bytes += network_data.get('tx_bytes', 0)
                network_rx_packets += network_data.get('rx_packets', 0)
                network_tx_packets += network_data.get('tx_packets', 0)

            # Диск I/O
            block_read_bytes = 0
            block_write_bytes = 0
            
            for io_stat in blkio_stats.get('io_service_bytes_recursive', []):
                if io_stat['op'] == 'Read':
                    block_read_bytes += io_stat['value']
                elif io_stat['op'] == 'Write':
                    block_write_bytes += io_stat['value']

            return {
                'timestamp': datetime.now(),
                'cpu_usage_percent': round(cpu_percent, 2),
                'cpu_system_usage': cpu_stats['system_cpu_usage'],
                'cpu_total_usage': cpu_stats['cpu_usage']['total_usage'],
                'memory_usage': memory_usage,
                'memory_limit': memory_limit,
                'memory_percent': round(memory_percent, 2),
                'network_rx_bytes': network_rx_bytes,
                'network_tx_bytes': network_tx_bytes,
                'network_rx_packets': network_rx_packets,
                'network_tx_packets': network_tx_packets,
                'block_read_bytes': block_read_bytes,
                'block_write_bytes': block_write_bytes,
            }
        except NotFound:
            logger.error(f"Container {container_id} not found")
            return None
        except DockerException as e:
            logger.error(f"Error fetching container stats: {e}")
            return None

    def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        """
        Получить логи контейнера
        
        Args:
            container_id: ID или имя контейнера
            tail: Количество последних строк
        """
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=tail, timestamps=True).decode('utf-8')
            return logs
        except NotFound:
            logger.error(f"Container {container_id} not found")
            return f"Container {container_id} not found"
        except DockerException as e:
            logger.error(f"Error fetching container logs: {e}")
            return f"Error: {str(e)}"

    def get_images(self) -> List[Dict]:
        """Получить список образов"""
        try:
            images = self.client.images.list()
            result = []
            
            for image in images:
                result.append({
                    'id': image.id,
                    'short_id': image.short_id,
                    'tags': image.tags,
                    'size': image.attrs.get('Size', 0),
                    'created': image.attrs.get('Created'),
                })
            
            return result
        except DockerException as e:
            logger.error(f"Error fetching images: {e}")
            return []

    def get_networks(self) -> List[Dict]:
        """Получить список сетей"""
        try:
            networks = self.client.networks.list()
            result = []
            
            for network in networks:
                result.append({
                    'id': network.id,
                    'short_id': network.short_id,
                    'name': network.name,
                    'driver': network.attrs.get('Driver'),
                    'scope': network.attrs.get('Scope'),
                    'containers': list(network.attrs.get('Containers', {}).keys()),
                })
            
            return result
        except DockerException as e:
            logger.error(f"Error fetching networks: {e}")
            return []

    def get_volumes(self) -> List[Dict]:
        """Получить список томов"""
        try:
            volumes = self.client.volumes.list()
            result = []
            
            for volume in volumes:
                result.append({
                    'name': volume.name,
                    'driver': volume.attrs.get('Driver'),
                    'mountpoint': volume.attrs.get('Mountpoint'),
                    'created': volume.attrs.get('CreatedAt'),
                })
            
            return result
        except DockerException as e:
            logger.error(f"Error fetching volumes: {e}")
            return []

    def container_action(self, container_id: str, action: str) -> Dict:
        """
        Выполнить действие с контейнером
        
        Args:
            container_id: ID или имя контейнера
            action: start, stop, restart, pause, unpause, kill, remove
        """
        try:
            container = self.client.containers.get(container_id)
            
            if action == 'start':
                container.start()
            elif action == 'stop':
                container.stop()
            elif action == 'restart':
                container.restart()
            elif action == 'pause':
                container.pause()
            elif action == 'unpause':
                container.unpause()
            elif action == 'kill':
                container.kill()
            elif action == 'remove':
                container.remove(force=True)
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
            
            return {'success': True, 'action': action, 'container_id': container_id}
        except NotFound:
            return {'success': False, 'error': f'Container {container_id} not found'}
        except APIError as e:
            return {'success': False, 'error': str(e)}
