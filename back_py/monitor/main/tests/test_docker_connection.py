import docker
import sys

print("=== Тестирование подключения к Docker ===\n")

# Тест 1: Проверка стандартного подключения
try:
    print("1. Попытка подключения через docker.from_env()...")
    client = docker.from_env()
    client.ping()
    print("✓ Подключение успешно!\n")
    
    # Получаем информацию
    info = client.info()
    version = client.version()
    
    print(f"Docker версия: {version.get('Version')}")
    print(f"API версия: {version.get('ApiVersion')}")
    print(f"ОС: {info.get('OperatingSystem')}")
    print(f"Контейнеры: {info.get('Containers')}")
    print(f"Запущено: {info.get('ContainersRunning')}")
    print(f"Остановлено: {info.get('ContainersStopped')}\n")
    
    # Список контейнеров
    print("Список контейнеров:")
    containers = client.containers.list(all=True)
    for container in containers:
        print(f"  - {container.name} ({container.status}): {container.image.tags}")
    
    print(f"\n✓ Найдено {len(containers)} контейнеров")
    
except Exception as e:
    print(f"✗ Ошибка подключения: {e}")
    print("\nВозможные причины:")
    print("1. Docker не запущен")
    print("2. Нет прав доступа к Docker socket")
    print("3. На Windows нужно использовать npipe или tcp")
    sys.exit(1)

# Тест 2: Альтернативные способы подключения для Windows
print("\n\n2. Тестирование альтернативных подключений...")

# Windows Named Pipe
try:
    print("   Попытка через Named Pipe (Windows)...")
    client_npipe = docker.DockerClient(base_url='npipe:////./pipe/docker_engine')
    client_npipe.ping()
    print("   ✓ Named Pipe работает!")
except Exception as e:
    print(f"   ✗ Named Pipe не работает: {e}")

# TCP (если Docker настроен на TCP)
try:
    print("   Попытка через TCP...")
    client_tcp = docker.DockerClient(base_url='tcp://127.0.0.1:2375')
    client_tcp.ping()
    print("   ✓ TCP работает!")
except Exception as e:
    print(f"   ✗ TCP не работает: {e}")

print("\n=== Тест завершен ===")
