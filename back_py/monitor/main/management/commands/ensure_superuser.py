# back_py/monitor/main/management/commands/ensure_superuser.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


class Command(BaseCommand):
    help = 'Создаёт суперпользователя admin@gmail.com:Admin123!'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput', '--no-input',
            action='store_true',
            help='Не запрашивать подтверждение',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = 'admin@gmail.com'
        email = 'admin@gmail.com'
        password = 'Admin123!'

        try:
            user = User.objects.get(username=username)
            if not user.is_superuser or not user.is_staff:
                user.is_superuser = True
                user.is_staff = True
                user.save()
                self.stdout.write(self.style.SUCCESS('✓ Суперпользователь обновлён'))
            else:
                self.stdout.write(self.style.WARNING('✓ Суперпользователь уже существует и активен'))
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_superuser=True,
                is_staff=True,
                is_active=True
            )
            try:
                user.full_clean()
            except ValidationError as e:
                self.stdout.write(self.style.ERROR(f'Ошибка валидации: {e}'))
                return
            self.stdout.write(self.style.SUCCESS('✓ Создан суперпользователь: admin@gmail.com'))
