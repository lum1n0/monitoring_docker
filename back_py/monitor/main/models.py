from django.db import models
from django.utils import timezone


class KubernetesCluster(models.Model):
    """Модель для хранения информации о Kubernetes кластерах"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Название кластера')
    config_path = models.CharField(max_length=255, blank=True, null=True, verbose_name='Путь к конфигу')
    api_server_url = models.URLField(verbose_name='URL API сервера')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Kubernetes Кластер'
        verbose_name_plural = 'Kubernetes Кластеры'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Namespace(models.Model):
    """Модель для хранения namespace в кластере"""
    cluster = models.ForeignKey(KubernetesCluster, on_delete=models.CASCADE, related_name='namespaces')
    name = models.CharField(max_length=100, verbose_name='Имя namespace')
    status = models.CharField(max_length=50, default='Active', verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Namespace'
        verbose_name_plural = 'Namespaces'
        unique_together = ['cluster', 'name']
        ordering = ['name']

    def __str__(self):
        return f"{self.cluster.name}/{self.name}"


class Pod(models.Model):
    """Модель для хранения информации о подах"""
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Running', 'Running'),
        ('Succeeded', 'Succeeded'),
        ('Failed', 'Failed'),
        ('Unknown', 'Unknown'),
    ]

    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE, related_name='pods')
    name = models.CharField(max_length=255, verbose_name='Имя пода')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, verbose_name='Статус')
    node_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Имя узла')
    pod_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP адрес пода')
    host_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP адрес хоста')
    restart_count = models.IntegerField(default=0, verbose_name='Количество перезапусков')
    created_at = models.DateTimeField(verbose_name='Дата создания')
    last_restart = models.DateTimeField(blank=True, null=True, verbose_name='Последний перезапуск')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Pod'
        verbose_name_plural = 'Pods'
        unique_together = ['namespace', 'name']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.namespace.name}/{self.name}"


class Container(models.Model):
    """Модель для хранения информации о контейнерах"""
    pod = models.ForeignKey(Pod, on_delete=models.CASCADE, related_name='containers')
    name = models.CharField(max_length=255, verbose_name='Имя контейнера')
    image = models.CharField(max_length=500, verbose_name='Образ')
    image_id = models.CharField(max_length=500, blank=True, null=True, verbose_name='ID образа')
    is_ready = models.BooleanField(default=False, verbose_name='Готов')
    restart_count = models.IntegerField(default=0, verbose_name='Количество перезапусков')
    state = models.CharField(max_length=50, verbose_name='Состояние')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Container'
        verbose_name_plural = 'Containers'
        unique_together = ['pod', 'name']
        ordering = ['name']

    def __str__(self):
        return f"{self.pod.name}/{self.name}"


class ContainerMetric(models.Model):
    """Модель для хранения метрик контейнеров"""
    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name='metrics')
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='Время измерения')
    cpu_usage = models.FloatField(default=0.0, verbose_name='Использование CPU (миллиядра)')
    memory_usage = models.BigIntegerField(default=0, verbose_name='Использование памяти (байты)')
    network_rx_bytes = models.BigIntegerField(default=0, verbose_name='Получено байт по сети')
    network_tx_bytes = models.BigIntegerField(default=0, verbose_name='Отправлено байт по сети')
    disk_read_bytes = models.BigIntegerField(default=0, verbose_name='Прочитано байт с диска')
    disk_write_bytes = models.BigIntegerField(default=0, verbose_name='Записано байт на диск')

    class Meta:
        verbose_name = 'Метрика контейнера'
        verbose_name_plural = 'Метрики контейнеров'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['container', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f"{self.container} - {self.timestamp}"


class Event(models.Model):
    """Модель для хранения событий Kubernetes"""
    EVENT_TYPES = [
        ('Normal', 'Normal'),
        ('Warning', 'Warning'),
        ('Error', 'Error'),
    ]

    cluster = models.ForeignKey(KubernetesCluster, on_delete=models.CASCADE, related_name='events')
    namespace = models.CharField(max_length=100, verbose_name='Namespace')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, verbose_name='Тип события')
    reason = models.CharField(max_length=255, verbose_name='Причина')
    message = models.TextField(verbose_name='Сообщение')
    involved_object_kind = models.CharField(max_length=50, verbose_name='Тип объекта')
    involved_object_name = models.CharField(max_length=255, verbose_name='Имя объекта')
    count = models.IntegerField(default=1, verbose_name='Количество')
    first_timestamp = models.DateTimeField(verbose_name='Первое появление')
    last_timestamp = models.DateTimeField(verbose_name='Последнее появление')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Событие'
        verbose_name_plural = 'События'
        ordering = ['-last_timestamp']
        indexes = [
            models.Index(fields=['cluster', '-last_timestamp']),
            models.Index(fields=['event_type', '-last_timestamp']),
        ]

    def __str__(self):
        return f"{self.event_type}: {self.reason} - {self.involved_object_name}"

# Добавьте после существующих моделей

class DockerHost(models.Model):
    """Модель для хранения информации о Docker хостах"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Название хоста')
    host_url = models.CharField(max_length=255, verbose_name='URL Docker хоста', 
                                help_text='Например: unix:///var/run/docker.sock или tcp://127.0.0.1:2375')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Docker Host'
        verbose_name_plural = 'Docker Hosts'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class DockerContainer(models.Model):
    """Модель для хранения информации о Docker контейнерах"""
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('restarting', 'Restarting'),
        ('removing', 'Removing'),
        ('exited', 'Exited'),
        ('dead', 'Dead'),
    ]

    host = models.ForeignKey(DockerHost, on_delete=models.CASCADE, related_name='containers')
    container_id = models.CharField(max_length=255, verbose_name='ID контейнера')  # Было 64
    name = models.CharField(max_length=255, verbose_name='Имя контейнера')
    image = models.CharField(max_length=500, verbose_name='Образ')
    image_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='ID образа')  # Было 64
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, verbose_name='Статус')
    state = models.CharField(max_length=50, verbose_name='Состояние')
    restart_count = models.IntegerField(default=0, verbose_name='Количество перезапусков')
    
    # Сетевые настройки
    ports = models.JSONField(default=dict, blank=True, verbose_name='Порты')
    networks = models.JSONField(default=list, blank=True, verbose_name='Сети')
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP адрес')
    
    # Временные метки
    created = models.DateTimeField(verbose_name='Дата создания контейнера')
    started_at = models.DateTimeField(blank=True, null=True, verbose_name='Время запуска')
    finished_at = models.DateTimeField(blank=True, null=True, verbose_name='Время остановки')
    
    # Метаданные
    labels = models.JSONField(default=dict, blank=True, verbose_name='Метки')
    command = models.TextField(blank=True, null=True, verbose_name='Команда')
    
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Docker Container'
        verbose_name_plural = 'Docker Containers'
        unique_together = ['host', 'container_id']
        ordering = ['-created']
        indexes = [
            models.Index(fields=['host', 'status']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.host.name}/{self.name}"



class DockerContainerMetric(models.Model):
    """Модель для хранения метрик Docker контейнеров"""
    container = models.ForeignKey(DockerContainer, on_delete=models.CASCADE, related_name='metrics')
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='Время измерения')
    
    # CPU метрики
    cpu_usage_percent = models.FloatField(default=0.0, verbose_name='Использование CPU (%)')
    cpu_system_usage = models.BigIntegerField(default=0, verbose_name='Системное использование CPU')
    cpu_total_usage = models.BigIntegerField(default=0, verbose_name='Общее использование CPU')
    
    # Память
    memory_usage = models.BigIntegerField(default=0, verbose_name='Использование памяти (байты)')
    memory_limit = models.BigIntegerField(default=0, verbose_name='Лимит памяти (байты)')
    memory_percent = models.FloatField(default=0.0, verbose_name='Использование памяти (%)')
    
    # Сеть
    network_rx_bytes = models.BigIntegerField(default=0, verbose_name='Получено байт по сети')
    network_tx_bytes = models.BigIntegerField(default=0, verbose_name='Отправлено байт по сети')
    network_rx_packets = models.BigIntegerField(default=0, verbose_name='Получено пакетов')
    network_tx_packets = models.BigIntegerField(default=0, verbose_name='Отправлено пакетов')
    
    # Диск
    block_read_bytes = models.BigIntegerField(default=0, verbose_name='Прочитано байт с диска')
    block_write_bytes = models.BigIntegerField(default=0, verbose_name='Записано байт на диск')

    class Meta:
        verbose_name = 'Метрика Docker контейнера'
        verbose_name_plural = 'Метрики Docker контейнеров'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['container', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f"{self.container} - {self.timestamp}"
