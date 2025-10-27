from django.core.management.base import BaseCommand
from main.models import DockerHost, DockerContainer, DockerContainerMetric
from main.services.docker_service import DockerService
from django.utils import timezone


class Command(BaseCommand):
    help = 'Синхронизировать контейнеры из Docker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--host-id',
            type=int,
            help='ID конкретного Docker хоста для синхронизации'
        )
        parser.add_argument(
            '--skip-metrics',
            action='store_true',
            help='Пропустить сбор метрик (быстрее)'
        )

    def handle(self, *args, **options):
        host_id = options.get('host_id')
        skip_metrics = options.get('skip_metrics', False)
        
        self.stdout.write(self.style.WARNING('\n=== Синхронизация Docker контейнеров ===\n'))

        # Получаем хосты для синхронизации
        if host_id:
            docker_hosts = DockerHost.objects.filter(id=host_id, is_active=True)
            if not docker_hosts.exists():
                self.stdout.write(self.style.ERROR(f'✗ Docker хост с ID {host_id} не найден!'))
                return
        else:
            docker_hosts = DockerHost.objects.filter(is_active=True)
        
        if not docker_hosts.exists():
            self.stdout.write(self.style.ERROR('✗ Активные Docker хосты не найдены!'))
            self.stdout.write('Сначала выполните: python manage.py setup_docker')
            return
        
        self.stdout.write(f'Найдено Docker хостов: {docker_hosts.count()}\n')
        
        total_synced = 0
        total_removed = 0
        total_metrics = 0
        
        for host in docker_hosts:
            self.stdout.write(f'📦 Синхронизация: {host.name}')
            self.stdout.write(f'   URL: {host.host_url if host.host_url else "(автоопределение)"}')
            
            try:
                docker_service = DockerService(host.host_url)
                
                # Получаем все контейнеры из Docker
                containers_data = docker_service.get_all_containers(all_containers=True)
                self.stdout.write(f'   Найдено в Docker: {len(containers_data)} контейнеров')
                
                # Получаем ID всех контейнеров из Docker
                docker_container_ids = set()
                synced_count = 0
                metrics_count = 0
                
                for container_data in containers_data:
                    docker_container_ids.add(container_data['container_id'])
                    
                    try:
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
                        synced_count += 1
                        
                        status_emoji = '✅' if container_data['status'] == 'running' else '⏸️' if container_data['status'] == 'paused' else '⏹️'
                        action = '+ Создан' if created else '↻ Обновлен'
                        self.stdout.write(f'   {status_emoji} {action}: {container.name} ({container_data["status"]})')
                        
                        # Собираем метрики для запущенных контейнеров
                        if not skip_metrics and container_data['status'] == 'running':
                            try:
                                stats = docker_service.get_container_stats(container_data['container_id'])
                                if stats:
                                    DockerContainerMetric.objects.create(
                                        container=container,
                                        timestamp=stats['timestamp'],
                                        cpu_usage_percent=stats['cpu_usage_percent'],
                                        cpu_system_usage=stats['cpu_system_usage'],
                                        cpu_total_usage=stats['cpu_total_usage'],
                                        memory_usage=stats['memory_usage'],
                                        memory_limit=stats['memory_limit'],
                                        memory_percent=stats['memory_percent'],
                                        network_rx_bytes=stats['network_rx_bytes'],
                                        network_tx_bytes=stats['network_tx_bytes'],
                                        network_rx_packets=stats['network_rx_packets'],
                                        network_tx_packets=stats['network_tx_packets'],
                                        block_read_bytes=stats['block_read_bytes'],
                                        block_write_bytes=stats['block_write_bytes'],
                                    )
                                    metrics_count += 1
                            except Exception as e:
                                self.stdout.write(self.style.WARNING(f'      ⚠ Метрики недоступны для {container.name}: {str(e)[:50]}'))
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'   ✗ Ошибка синхронизации {container_data["name"]}: {e}'))
                        continue
                
                # Удаляем контейнеры, которых больше нет в Docker
                removed = DockerContainer.objects.filter(host=host).exclude(
                    container_id__in=docker_container_ids
                )
                removed_count = removed.count()
                
                if removed_count > 0:
                    self.stdout.write(f'   🗑️  Удаление {removed_count} устаревших записей...')
                    for container in removed:
                        self.stdout.write(f'      - Удален: {container.name}')
                    removed.delete()
                
                total_synced += synced_count
                total_removed += removed_count
                total_metrics += metrics_count
                
                self.stdout.write(self.style.SUCCESS(
                    f'   ✓ Синхронизировано: {synced_count} | Удалено: {removed_count} | Метрики: {metrics_count}\n'
                ))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ✗ Ошибка подключения: {e}\n'))

        # Итоговая статистика
        self.stdout.write(self.style.SUCCESS('=== Синхронизация завершена ==='))
        self.stdout.write(f'📊 Статистика:')
        self.stdout.write(f'   Контейнеров синхронизировано: {total_synced}')
        self.stdout.write(f'   Контейнеров удалено: {total_removed}')
        self.stdout.write(f'   Метрик собрано: {total_metrics}')
        
        # Проверяем результат в БД
        self.stdout.write(f'\n📈 Текущее состояние БД:')
        total_containers = DockerContainer.objects.count()
        running_containers = DockerContainer.objects.filter(status='running').count()
        self.stdout.write(f'   Всего в БД: {total_containers} контейнеров')
        self.stdout.write(f'   Запущено: {running_containers} контейнеров')
