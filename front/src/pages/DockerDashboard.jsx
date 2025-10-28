import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';

function DockerDashboard() {
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const mountedRef = useRef(true);

  const [points, setPoints] = useState({ cpu: [], memory: [], netrx: [], nettx: [] });
  const [selectedContainer, setSelectedContainer] = useState('');
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const [hideMonitoring, setHideMonitoring] = useState(true);

const monitoringContainers = ['back_py-cadvisor', 'back_py-prometheus', 'back_py-grafana', 'back_py-db', 'back_py-redis', 'k8s_monitor_backend', 'k8s_monitor_db', 'k8s_monitor_frontend', 'k8s_monitor-cadvisor', 'k8s_monitor-prometheus', 'k8s_monitor-grafana', 'k8s_monitor-db', 'k8s_monitor-redis'];
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.log('WebSocket уже подключен или подключается');
      return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
      setError('Token не найден. Пожалуйста, войдите в систему.');
      return;
    }

    const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const q = new URLSearchParams({
      token,
      period: '5',
      ...(selectedContainer ? { container: selectedContainer } : {}),
    });

    const base = import.meta.env.DEV
      ? `${wsScheme}://localhost:8000`
      : `${wsScheme}://${window.location.host}`;

    const wsUrl = `${base}/ws/docker/metrics/?${q.toString()}`;

    console.log('Подключение к WebSocket:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        console.log('WebSocket подключен');
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (ev) => {
        if (!mountedRef.current) return;

        try {
          const payload = JSON.parse(ev.data);
          console.log('Получены данные:', payload);

          if (payload.error) {
            setError(payload.error);
            return;
          }

          const ts = payload.ts;

          setPoints((prev) => {
            const maxPoints = 60;

            return {
              cpu: [...prev.cpu, { ts, data: payload.cpu?.data || [] }].slice(-maxPoints),
              memory: [...prev.memory, { ts, data: payload.memory?.data || [] }].slice(-maxPoints),
              netrx: [...prev.netrx, { ts, data: payload.netrx?.data || [] }].slice(-maxPoints),
              nettx: [...prev.nettx, { ts, data: payload.nettx?.data || [] }].slice(-maxPoints),
            };
          });
        } catch (err) {
          console.error('Ошибка парсинга сообщения:', err);
        }
      };

      ws.onerror = (err) => {
        if (!mountedRef.current) return;
        console.error('WebSocket ошибка:', err);
        setError('Ошибка подключения WebSocket');
        setConnected(false);
      };

      ws.onclose = (event) => {
        if (!mountedRef.current) return;
        console.log('WebSocket закрыт:', event.code, event.reason);
        setConnected(false);

        if (mountedRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) {
              console.log('Попытка переподключения...');
              connectWebSocket();
            }
          }, 3000);
        }
      };
    } catch (err) {
      console.error('Ошибка создания WebSocket:', err);
      setError(err.message);
    }
  }, [selectedContainer]);

  useEffect(() => {
    mountedRef.current = true;
    setPoints({ cpu: [], memory: [], netrx: [], nettx: [] });

    const timer = setTimeout(() => {
      if (mountedRef.current) {
        connectWebSocket();
      }
    }, 100);

    return () => {
      mountedRef.current = false;
      clearTimeout(timer);

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }

      if (wsRef.current) {
        console.log('Закрытие WebSocket при размонтировании');
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [selectedContainer, connectWebSocket]);

  const filterMonitoringContainers = useCallback((data) => {
    if (!hideMonitoring) return data;

    return data.filter(item => {
      return !monitoringContainers.some(monContainer =>
        item.name.startsWith(monContainer)
      );
    });
  }, [hideMonitoring, monitoringContainers]);

  const transformData = useCallback((pointsArray) => {
    const timeSeriesMap = new Map();

    pointsArray.forEach(({ ts, data }) => {
      if (!timeSeriesMap.has(ts)) {
        timeSeriesMap.set(ts, { ts });
      }

      const point = timeSeriesMap.get(ts);
      const filteredData = filterMonitoringContainers(data || []);

      const topContainers = filteredData
        .sort((a, b) => b.value - a.value)
        .slice(0, 5);

      topContainers.forEach(({ name, value }) => {
        point[name] = (point[name] || 0) + value;
      });
    });

    return Array.from(timeSeriesMap.values()).sort((a, b) => a.ts - b.ts);
  }, [filterMonitoringContainers]);

  const cpuData = useMemo(() => transformData(points.cpu), [points.cpu, transformData]);
  const memData = useMemo(() => transformData(points.memory), [points.memory, transformData]);
  const rxData = useMemo(() => transformData(points.netrx), [points.netrx, transformData]);
  const txData = useMemo(() => transformData(points.nettx), [points.nettx, transformData]);

  const colors = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'];

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const CustomTooltip = ({ active, payload, label, formatter }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          backgroundColor: 'rgba(0,0,0,0.9)',
          padding: '12px',
          borderRadius: '8px',
          color: 'white',
          border: '1px solid #444'
        }}>
          <p style={{ margin: '0 0 8px 0', fontWeight: 'bold' }}>
            {new Date(label).toLocaleTimeString()}
          </p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color, margin: '4px 0' }}>
              {entry.name}: {formatter ? formatter(entry.value) : entry.value.toFixed(4)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const renderChart = (data, title, unit = '', formatter = null) => {
    if (!data || data.length === 0) {
      return (
        <div className="chart-card">
          <h3>{title}</h3>
          <p style={{ color: '#888', margin: 0 }}>Ожидание данных...</p>
        </div>
      );
    }

    const keys = Object.keys(data[0] || {}).filter((k) => k !== 'ts');

    if (keys.length === 0) {
      return (
        <div className="chart-card">
          <h3>{title}</h3>
          <p style={{ color: '#888', margin: 0 }}>Нет данных от контейнеров</p>
        </div>
      );
    }

    return (
      <div className="chart-card">
        <h3>{title}</h3>
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis
              dataKey="ts"
              tickFormatter={(t) => new Date(t).toLocaleTimeString()}
              stroke="#666"
              style={{ fontSize: '11px' }}
            />
            <YAxis
              tickFormatter={(v) => formatter ? formatter(v) : v.toFixed(2)}
              stroke="#666"
              style={{ fontSize: '11px' }}
            />
            <Tooltip content={<CustomTooltip formatter={formatter} />} />
            <Legend wrapperStyle={{ fontSize: '11px' }} />
            {keys.map((k, i) => (
              <Area
                key={k}
                dataKey={k}
                stackId="1"
                type="monotone"
                stroke={colors[i % 5]}
                fill={colors[i % 5]}
                fillOpacity={0.7}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    );
  };

  return (
    <div style={{ padding: 24, maxWidth: '1600px', margin: '0 auto', minHeight: '100vh' }}>
      <h1 style={{ marginBottom: 24 }}>Мониторинг Docker контейнеров</h1>

      <div style={{
        marginBottom: 24,
        padding: 20,
        backgroundColor: 'var(--bg-secondary)',
        borderRadius: 8,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 16,
        border: '1px solid var(--border-color)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <label style={{ fontWeight: 'bold' }}>Фильтр по контейнеру:</label>
          <input
            style={{
              padding: '10px 14px',
              borderRadius: 6,
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              minWidth: '250px'
            }}
            placeholder="имя контейнера (опционально)"
            value={selectedContainer}
            onChange={(e) => setSelectedContainer(e.target.value)}
          />

          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            cursor: 'pointer',
            padding: '8px 12px',
            backgroundColor: hideMonitoring ? 'var(--status-success-bg)' : 'var(--bg-primary)',
            borderRadius: 6,
            border: '1px solid var(--border-color)',
            transition: 'all 0.3s ease'
          }}>
            <input
              type="checkbox"
              checked={hideMonitoring}
              onChange={(e) => setHideMonitoring(e.target.checked)}
              style={{
                width: '18px',
                height: '18px',
                cursor: 'pointer',
                accentColor: 'var(--btn-success)'
              }}
            />
            <span style={{ fontSize: '14px', userSelect: 'none' }}>
              Скрыть контейнеры мониторинга
            </span>
          </label>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 12,
            height: 12,
            borderRadius: '50%',
            backgroundColor: connected ? 'var(--status-success)' : 'var(--btn-danger)',
            boxShadow: connected ? '0 0 8px var(--status-success)' : '0 0 8px var(--btn-danger)'
          }} />
          <span style={{ fontWeight: 'bold' }}>
            {connected ? 'Подключено' : 'Отключено'}
          </span>
        </div>
      </div>

      {hideMonitoring && (
        <div style={{
          marginBottom: 16,
          padding: 12,
          backgroundColor: 'var(--status-success-bg)',
          border: '1px solid var(--status-success)',
          borderRadius: 6,
          color: 'var(--status-success)',
          fontSize: '14px'
        }}>
          <strong>🔍 Фильтр активен:</strong> Скрыты контейнеры: cadvisor, prometheus, grafana, db, redis
        </div>
      )}

      {error && (
        <div style={{
          padding: 16,
          backgroundColor: 'var(--status-danger-bg)',
          border: '1px solid var(--btn-danger)',
          borderRadius: 8,
          marginBottom: 24,
          color: 'var(--btn-danger)'
        }}>
          <strong>Ошибка:</strong> {error}
        </div>
      )}

      {/* Сетка графиков 2x2 */}
      <div className="chart-grid">
        {renderChart(cpuData, 'CPU (ядра, топ-5 контейнеров)', 'cores')}
        {renderChart(memData, 'Память (топ-5 контейнеров)', 'bytes', formatBytes)}
        {renderChart(rxData, 'Получение (байт/с, топ-5)', 'bytes/s', formatBytes)}
        {renderChart(txData, 'Отправка (байт/с, топ-5)', 'bytes/s', formatBytes)}
      </div>
    </div>
  );
}

export default DockerDashboard;
