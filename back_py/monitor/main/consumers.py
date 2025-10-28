import os, asyncio, httpx, time, json, logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

PROM_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

# ПРАВИЛЬНЫЕ запросы - убираем sum() для получения всех контейнеров
# Используем фильтр image!="" чтобы исключить системные процессы
CPU_QUERY = 'rate(container_cpu_usage_seconds_total{image!="",name!=""}[1m])'
MEM_QUERY = 'container_memory_working_set_bytes{image!="",name!=""}'
RX_QUERY = 'rate(container_network_receive_bytes_total{image!="",name!=""}[1m])'
TX_QUERY = 'rate(container_network_transmit_bytes_total{image!="",name!=""}[1m])'

class DockerMetricsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        qs = parse_qs(self.scope["query_string"].decode())
        token_key = qs.get("token", [None])[0]
        self.user = AnonymousUser()
        
        if token_key:
            try:
                token = await sync_to_async(Token.objects.select_related('user').get)(key=token_key)
                self.user = token.user
                logger.info(f"WebSocket authenticated: user={self.user.username}")
            except Token.DoesNotExist:
                logger.warning("Invalid WebSocket token")
        
        if not getattr(self.user, "is_authenticated", False):
            logger.warning("Unauthenticated WebSocket connection rejected")
            await self.close(code=4401)
            return
        
        self.container = qs.get("container", [None])[0]
        self.period = int(qs.get("period", [5])[0])
        
        logger.info(f"WebSocket connected: user={self.user.username}, container={self.container}, period={self.period}")
        
        await self.accept()
        self.task = asyncio.create_task(self.stream())
    
    async def disconnect(self, code):
        logger.info(f"WebSocket disconnected: code={code}")
        if hasattr(self, "task"):
            self.task.cancel()
    
    def _wrap_filter(self, q: str) -> str:
        """Добавляет фильтр по контейнеру если указан"""
        if not self.container:
            return q
        # Фильтруем по имени контейнера (используем regex для частичного совпадения)
        filter_str = f'name=~".*{self.container}.*"'
        # Заменяем существующий фильтр
        return q.replace('name!=""', filter_str)
    
    async def stream(self):
        async with httpx.AsyncClient(timeout=10) as client:
            iteration = 0
            while True:
                try:
                    iteration += 1
                    ts_ms = int(time.time() * 1000)
                    
                    logger.debug(f"Fetching metrics iteration {iteration}")
                    
                    # Параллельные запросы к Prometheus
                    responses = await asyncio.gather(
                        client.get(f"{PROM_URL}/api/v1/query", params={"query": self._wrap_filter(CPU_QUERY)}),
                        client.get(f"{PROM_URL}/api/v1/query", params={"query": self._wrap_filter(MEM_QUERY)}),
                        client.get(f"{PROM_URL}/api/v1/query", params={"query": self._wrap_filter(RX_QUERY)}),
                        client.get(f"{PROM_URL}/api/v1/query", params={"query": self._wrap_filter(TX_QUERY)}),
                        return_exceptions=True
                    )
                    
                    cpu, mem, rx, tx = responses
                    
                    def to_series(resp):
                        if isinstance(resp, Exception):
                            logger.error(f"Query error: {resp}")
                            return []
                        
                        try:
                            json_data = resp.json()
                            
                            # Проверка на ошибки от Prometheus
                            if json_data.get("status") != "success":
                                logger.error(f"Prometheus error: {json_data.get('error')}")
                                return []
                            
                            data = json_data.get("data", {}).get("result", [])
                            
                            result = []
                            for m in data:
                                metric = m.get("metric", {})
                                value = m.get("value", [None, 0])
                                
                                # Получаем имя контейнера из метки name
                                container_name = metric.get("name", "unknown")
                                
                                # Убираем путь если есть (например /system.slice/docker-xxx.scope -> docker-xxx)
                                if "/" in container_name:
                                    container_name = container_name.split("/")[-1]
                                
                                # Убираем .scope если есть
                                if container_name.endswith(".scope"):
                                    container_name = container_name[:-6]
                                
                                # Убираем docker- префикс и длинный хэш
                                if container_name.startswith("docker-"):
                                    container_name = container_name[7:]
                                    if len(container_name) > 12:
                                        container_name = container_name[:12]
                                
                                try:
                                    value_float = float(value[1]) if value and len(value) > 1 else 0.0
                                    
                                    # Пропускаем нулевые значения для сетевых метрик
                                    if value_float == 0:
                                        continue
                                    
                                    result.append({
                                        "name": container_name,
                                        "value": value_float,
                                    })
                                except (ValueError, IndexError, TypeError) as e:
                                    logger.warning(f"Error parsing value: {e}")
                                    continue
                            
                            return result
                        except Exception as e:
                            logger.error(f"Error parsing response: {e}")
                            return []
                    
                    cpu_data = to_series(cpu)
                    mem_data = to_series(mem)
                    rx_data = to_series(rx)
                    tx_data = to_series(tx)
                    
                    payload = {
                        "ts": ts_ms,
                        "cpu": {"data": cpu_data},
                        "memory": {"data": mem_data},
                        "netrx": {"data": rx_data},
                        "nettx": {"data": tx_data},
                    }
                    
                    # Логирование для отладки
                    total_metrics = len(cpu_data) + len(mem_data) + len(rx_data) + len(tx_data)
                    logger.info(f"Sending metrics: CPU={len(cpu_data)}, MEM={len(mem_data)}, RX={len(rx_data)}, TX={len(tx_data)}, total={total_metrics}")
                    
                    if iteration == 1:
                        # Показываем пример данных при первой итерации
                        logger.info(f"Sample data: {json.dumps(payload, indent=2)[:1000]}")
                    
                    await self.send(text_data=json.dumps(payload))
                    
                except asyncio.CancelledError:
                    logger.info("Stream task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Stream error: {e}", exc_info=True)
                    await self.send(text_data=json.dumps({"error": str(e)}))
                
                await asyncio.sleep(self.period)
