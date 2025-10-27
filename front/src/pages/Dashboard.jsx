import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchClusters, fetchClusterStats, fetchClusterHealth, syncKubernetesData } from '../api/services';
import { Activity, Database, Server, AlertTriangle, RefreshCw } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';

function Dashboard() {
    const [selectedCluster, setSelectedCluster] = useState(null);
    const [syncing, setSyncing] = useState(false);
    const [metrics, setMetrics] = useState({
        cpu: [],
        memory: [],
        network: [],
        pods: []
    });
    const ws = useRef(null);

    const { data: clustersResponse, isLoading: clustersLoading } = useQuery({
        queryKey: ['clusters'],
        queryFn: fetchClusters,
    });

    const clusters = clustersResponse?.results || clustersResponse || [];

    const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery({
        queryKey: ['clusterStats', selectedCluster],
        queryFn: () => fetchClusterStats(selectedCluster),
        enabled: !!selectedCluster,
    });

    const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useQuery({
        queryKey: ['clusterHealth', selectedCluster],
        queryFn: () => fetchClusterHealth(selectedCluster),
        enabled: !!selectedCluster,
    });

    // WebSocket подключение
    useEffect(() => {
        if (!selectedCluster) return;

        const token = localStorage.getItem('token');
        const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${wsScheme}://${window.location.host}/ws/metrics/?token=${token}&cluster_id=${selectedCluster}`;

        ws.current = new WebSocket(wsUrl);

        ws.current.onmessage = (event) => {
            try {
                const payload = JSON.parse(event.data);
                console.log('WebSocket data received:', payload);
                
                setMetrics(prev => ({
                    cpu: [...prev.cpu.slice(-59), ...(payload.cpu?.data || [])].slice(-60),
                    memory: [...prev.memory.slice(-59), ...(payload.memory?.data || [])].slice(-60),
                    network: [...prev.network.slice(-59), ...(payload.network?.data || [])].slice(-60),
                    pods: [...prev.pods.slice(-59), ...(payload.pods?.data || [])].slice(-60)
                }));
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        ws.current.onopen = () => {
            console.log('WebSocket connected');
        };

        ws.current.onclose = () => {
            console.log('WebSocket disconnected');
        };

        ws.current.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, [selectedCluster]);

    useEffect(() => {
        if (clusters.length > 0 && !selectedCluster) {
            setSelectedCluster(clusters[0].id);
        }
    }, [clusters, selectedCluster]);

    const handleSync = async () => {
        if (!selectedCluster) return;
        
        setSyncing(true);
        try {
            await syncKubernetesData(selectedCluster);
            await refetchStats();
            await refetchHealth();
            alert('Данные успешно синхронизированы!');
        } catch (error) {
            alert('Ошибка синхронизации: ' + error.message);
        } finally {
            setSyncing(false);
        }
    };

    if (clustersLoading) {
        return <div className="loading">Загрузка кластеров...</div>;
    }

    // if (clusters.length === 0) {
    //     return (
    //         <div className="empty-state">
    //             <h2>Кластеры не найдены</h2>
    //             <p>Добавьте кластер через админ-панель Django</p>
    //             <a href="http://backend:8000/admin" target="_blank" rel="noopener noreferrer">
    //                 Открыть админ-панель
    //             </a>
    //         </div>
    //     );
    // }

    return (
        <div className="dashboard">
            <div className="dashboard-header">
                <h1>Мониторинг Kubernetes</h1>
                <div className="cluster-selector">
                    <select 
                        value={selectedCluster || ''} 
                        onChange={(e) => setSelectedCluster(Number(e.target.value))}
                    >
                        {clusters.map((cluster) => (
                            <option key={cluster.id} value={cluster.id}>
                                {cluster.name}
                            </option>
                        ))}
                    </select>
                    <button 
                        onClick={handleSync} 
                        disabled={syncing}
                        className="sync-button"
                    >
                        <RefreshCw size={16} className={syncing ? 'spinning' : ''} />
                        {syncing ? 'Синхронизация...' : 'Синхронизировать'}
                    </button>
                </div>
            </div>

            {statsLoading || healthLoading ? (
                <div className="loading">Загрузка данных...</div>
            ) : (
                <>
                    <div className="metrics-grid">
                        <MetricCard
                            icon={<Activity size={24} />}
                            title="Всего подов"
                            value={stats?.total_pods || 0}
                            color="blue"
                        />
                        <MetricCard
                            icon={<Server size={24} />}
                            title="Запущенные поды"
                            value={stats?.running_pods || 0}
                            color="green"
                        />
                        <MetricCard
                            icon={<Database size={24} />}
                            title="Namespaces"
                            value={stats?.total_namespaces || 0}
                            color="purple"
                        />
                        <MetricCard
                            icon={<AlertTriangle size={24} />}
                            title="Недавние проблемы"
                            value={health?.recent_issues || 0}
                            color="orange"
                        />
                    </div>

                    {/* Графики метрик в реальном времени */}
                    <div className="metrics-charts">
                        <h2>Метрики в реальном времени</h2>
                        
                        <div className="chart-grid">
                            {/* График использования CPU */}
                            <div className="chart-card">
                                <h3>Использование CPU (%)</h3>
                                <ResponsiveContainer width="100%" height={200}>
                                    <AreaChart data={metrics.cpu}>
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis 
                                            dataKey="timestamp" 
                                            tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                                        />
                                        <YAxis domain={[0, 100]} />
                                        <Tooltip 
                                            labelFormatter={(value) => `Время: ${new Date(value).toLocaleTimeString()}`}
                                            formatter={(value) => [`${value}%`, 'CPU']}
                                        />
                                        <Legend />
                                        <Area 
                                            type="monotone" 
                                            dataKey="value" 
                                            stroke="#8884d8" 
                                            fill="#8884d8" 
                                            fillOpacity={0.3}
                                            name="CPU Usage"
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>

                            {/* График использования памяти */}
                            <div className="chart-card">
                                <h3>Использование памяти (MB)</h3>
                                <ResponsiveContainer width="100%" height={200}>
                                    <AreaChart data={metrics.memory}>
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis 
                                            dataKey="timestamp" 
                                            tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                                        />
                                        <YAxis />
                                        <Tooltip 
                                            labelFormatter={(value) => `Время: ${new Date(value).toLocaleTimeString()}`}
                                            formatter={(value) => [`${value} MB`, 'Memory']}
                                        />
                                        <Legend />
                                        <Area 
                                            type="monotone" 
                                            dataKey="value" 
                                            stroke="#82ca9d" 
                                            fill="#82ca9d" 
                                            fillOpacity={0.3}
                                            name="Memory Usage"
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>

                            {/* График сетевой активности */}
                            <div className="chart-card">
                                <h3>Сетевая активность (KB/s)</h3>
                                <ResponsiveContainer width="100%" height={200}>
                                    <LineChart data={metrics.network}>
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis 
                                            dataKey="timestamp" 
                                            tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                                        />
                                        <YAxis />
                                        <Tooltip 
                                            labelFormatter={(value) => `Время: ${new Date(value).toLocaleTimeString()}`}
                                        />
                                        <Legend />
                                        <Line 
                                            type="monotone" 
                                            dataKey="in" 
                                            stroke="#ff7300" 
                                            name="Network In"
                                            strokeWidth={2}
                                        />
                                        <Line 
                                            type="monotone" 
                                            dataKey="out" 
                                            stroke="#387908" 
                                            name="Network Out"
                                            strokeWidth={2}
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>

                            {/* График количества подов */}
                            <div className="chart-card">
                                <h3>Количество подов</h3>
                                <ResponsiveContainer width="100%" height={200}>
                                    <LineChart data={metrics.pods}>
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis 
                                            dataKey="timestamp" 
                                            tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                                        />
                                        <YAxis />
                                        <Tooltip 
                                            labelFormatter={(value) => `Время: ${new Date(value).toLocaleTimeString()}`}
                                        />
                                        <Legend />
                                        <Line 
                                            type="monotone" 
                                            dataKey="total" 
                                            stroke="#8884d8" 
                                            name="Total Pods"
                                            strokeWidth={2}
                                        />
                                        <Line 
                                            type="monotone" 
                                            dataKey="running" 
                                            stroke="#82ca9d" 
                                            name="Running Pods"
                                            strokeWidth={2}
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>

                    {health && (
                        <div className="health-section">
                            <h2>Здоровье кластера</h2>
                            <div className="health-card">
                                <div className="health-status">
                                    <span className={`status-badge ${health.status}`}>
                                        {health.status === 'healthy' ? 'Здоров' : 'Проблемы'}
                                    </span>
                                </div>
                                <div className="health-details">
                                    <div className="health-item">
                                        <strong>Узлы:</strong> {health.nodes?.ready || 0}/{health.nodes?.total || 0} готовы
                                    </div>
                                    <div className="health-item">
                                        <strong>Версия:</strong> {health.cluster?.version || 'N/A'}
                                    </div>
                                    <div className="health-item">
                                        <strong>API Server:</strong> {health.cluster?.api_server || 'N/A'}
                                    </div>
                                </div>
                            </div>

                            {health.nodes?.details && health.nodes.details.length > 0 && (
                                <div className="nodes-list">
                                    <h3>Узлы кластера</h3>
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Имя</th>
                                                <th>Статус</th>
                                                <th>Роли</th>
                                                <th>Версия</th>
                                                <th>CPU</th>
                                                <th>Память</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {health.nodes.details.map((node, index) => (
                                                <tr key={index}>
                                                    <td>{node.name}</td>
                                                    <td>
                                                        <span className={`status-badge ${node.status === 'Ready' ? 'healthy' : 'degraded'}`}>
                                                            {node.status}
                                                        </span>
                                                    </td>
                                                    <td>{node.roles?.join(', ') || 'worker'}</td>
                                                    <td>{node.version}</td>
                                                    <td>{node.capacity?.cpu || 'N/A'}</td>
                                                    <td>{node.capacity?.memory || 'N/A'}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    )}

                    {stats && (
                        <div className="pods-summary">
                            <h2>Сводка по подам</h2>
                            <div className="summary-grid">
                                <div className="summary-item running">
                                    <div className="summary-value">{stats.running_pods}</div>
                                    <div className="summary-label">Running</div>
                                </div>
                                <div className="summary-item pending">
                                    <div className="summary-value">{stats.pending_pods}</div>
                                    <div className="summary-label">Pending</div>
                                </div>
                                <div className="summary-item failed">
                                    <div className="summary-value">{stats.failed_pods}</div>
                                    <div className="summary-label">Failed</div>
                                </div>
                                <div className="summary-item">
                                    <div className="summary-value">{stats.total_containers}</div>
                                    <div className="summary-label">Containers</div>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

function MetricCard({ icon, title, value, color }) {
    return (
        <div className={`metric-card ${color}`}>
            <div className="metric-icon">{icon}</div>
            <div className="metric-content">
                <div className="metric-value">{value}</div>
                <div className="metric-title">{title}</div>
            </div>
        </div>
    );
}

export default Dashboard;