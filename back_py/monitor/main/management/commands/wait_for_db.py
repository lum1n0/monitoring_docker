from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
import time

class Command(BaseCommand):
    help = 'Ждёт, пока база станет доступной'

    def add_arguments(self, parser):
        parser.add_argument('--timeout', type=int, default=60, help='Макс. время ожидания (сек)')

    def handle(self, *args, **options):
        timeout = options['timeout']
        start = time.time()
        while (time.time() - start) < timeout:
            try:
                connections['default'].cursor()
                self.stdout.write(self.style.SUCCESS('✓ База доступна'))
                return
            except OperationalError:
                self.stdout.write('База недоступна, ждём...')
                time.sleep(1)
        self.stdout.write(self.style.ERROR('✗ База не отвечает'))
        exit(1)
