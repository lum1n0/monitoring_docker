# monitor/manage.py
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import subprocess

def ensure_superuser():
    try:
        import django
        django.setup()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        username = 'admin@gmail.com'
        email = 'admin@gmail.com'
        password = 'Admin123!'
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'is_superuser': True, 'is_staff': True, 'is_active': True}
        )
        if created:
            user.set_password(password)
            user.save()
        else:
            changed = False
            if not user.is_superuser or not user.is_staff:
                user.is_superuser = user.is_staff = True
                changed = True
            if user.email != email:
                user.email = email
                changed = True
            if changed:
                user.save()
    except Exception as e:
        # Не прерываем запуск сервера при ошибках
        print(f"Warning: could not ensure superuser: {e}")

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monitor.settings')

    if len(sys.argv) >= 2 and sys.argv[1] == 'runserver':
        if os.environ.get('INIT_ON_RUNSERVER_DONE') != '1':
            env = os.environ.copy()
            env['INIT_ON_RUNSERVER_DONE'] = '1'

            # Выполняем setup_docker --sync
            try:
                subprocess.run([sys.executable, sys.argv[0], 'setup_docker', '--sync'], check=False, env=env)
            except Exception as e:
                print(f"setup_docker failed: {e}")

            # Создаём суперпользователя
            ensure_superuser()

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
