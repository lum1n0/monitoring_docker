from django.core.management.base import BaseCommand
from main.models import DockerHost, DockerContainer
from main.services.docker_service import DockerService
import sys


class Command(BaseCommand):
    help = 'Настройка Docker хоста с автоопределением и автосинхронизацией'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            default='auto',
            choices=['auto', 'env', 'npipe', 'unix', 'tcp'],
            help='Режим подключения к Docker'
        )
        parser.add_argument(
            '--url',
            type=str,
            help='Кастомный URL для подключения'
        )
        parser.add_argument(
            '--test-only',
            action='store_true',
            help='Только тестировать без создания/синхронизации'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Также синхронизировать контейнеры после настройки'
        )

    def handle(self, *args, **options):
        mode = options['mode']
        custom_url = options['url']
        test_only = options['test_only']
        do_sync = options['sync']
        
        self.stdout.write(self.style.WARNING('\n=== Настройка Docker хоста ===\n'))

        # Определяем URL
        docker_url = custom_url if custom_url else mode
        save_url = '' if docker_url in ['auto', 'env'] else docker_url
        
        # Тестирование подключения
        self.stdout.write('1. Тестирование подключения к Docker...')
        test_result = DockerService.test_connection(docker_url)
        
        if not test_result['success']:
            self.stdout.write(self.style.ERROR(f'✗ Ошибка: {test_result["error"]}'))
            sys.exit(1)
        
        self.stdout.write(self.style.SUCCESS('✓ Подключение успешно!'))
        self.stdout.write(f'   Платформа: {test_result["platform"]}')
        self.stdout.write(f'   Docker: {test_result["docker_version"]}')
        self.stdout.write(f'   Контейнеры: {test_result["containers"]} ({test_result["containers_running"]} запущено)\n')
        
        if test_only:
            self.stdout.write(self.style.SUCCESS('=== Тест завершен ==='))
            return

        # Создание/обновление хоста
        self.stdout.write('2. Настройка в базе данных...')
        try:
            host, created = DockerHost.objects.update_or_create(
                name='local-docker',
                defaults={
                    'host_url': save_url,
                    'description': f'Автоопределение ({test_result["platform"]})',
                    'is_active': True,
                }
            )
            
            action = 'Создан' if created else 'Обновлен'
            self.stdout.write(self.style.SUCCESS(f'✓ {action} хост: {host.name} (ID: {host.id})\n'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Ошибка: {e}'))
            sys.exit(1)

        # Автоматическая синхронизация
        if do_sync or created:
            self.stdout.write('3. Синхронизация контейнеров...')
            try:
                docker_service = DockerService(host.host_url)
                containers_data = docker_service.get_all_containers(all_containers=True)
                
                docker_container_ids = set()
                synced = 0
                
                for container_data in containers_data:
                    docker_container_ids.add(container_data['container_id'])
                    
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
                    synced += 1
                
                # Удаляем старые
                removed = DockerContainer.objects.filter(host=host).exclude(
                    container_id__in=docker_container_ids
                ).delete()[0]
                
                self.stdout.write(self.style.SUCCESS(f'✓ Синхронизировано: {synced}, Удалено: {removed}\n'))
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠ Синхронизация не удалась: {e}\n'))

        self.stdout.write(self.style.SUCCESS('=== Настройка завершена ==='))
