import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { 
    fetchUnifiedContainers, 
    fetchUnifiedStats,
    fetchDockerHosts,
    fetchClusters,
    syncDockerData,
    syncKubernetesData,
    dockerContainerAction
} from '../api/services';
import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';
import { Search, Filter, Play, Square, RotateCw, Pause, RefreshCw } from 'lucide-react';

function ContainersPage() {
    const navigate = useNavigate();
    const [filters, setFilters] = useState({
        source: '',
        status: '',
        search: '',
    });
    const [actionLoading, setActionLoading] = useState({});

    const { data: statsData } = useQuery({
        queryKey: ['unifiedStats'],
        queryFn: fetchUnifiedStats,
        refetchInterval: 30000, // Обновление каждые 30 секунд
    });

    const { data: containersResponse, isLoading: containersLoading, refetch: refetchContainers } = useQuery({
        queryKey: ['unifiedContainers', filters],
        queryFn: () => {
            const params = {};
            if (filters.source) params.source = filters.source;
            if (filters.status) params.status = filters.status;
            return fetchUnifiedContainers(params);
        },
        refetchInterval: 30000,
    });

    const { data: dockerHostsResponse } = useQuery({
        queryKey: ['dockerHosts'],
        queryFn: fetchDockerHosts,
    });

    const { data: clustersResponse } = useQuery({
        queryKey: ['clusters'],
        queryFn: fetchClusters,
    });

    const dockerHosts = Array.isArray(dockerHostsResponse) 
        ? dockerHostsResponse 
        : (dockerHostsResponse?.results || []);

    const clusters = Array.isArray(clustersResponse)
        ? clustersResponse
        : (clustersResponse?.results || []);

    const containers = containersResponse?.results || [];

    // Фильтрация по поиску на клиенте
    const filteredContainers = containers.filter(container => 
        !filters.search || 
        container.name?.toLowerCase().includes(filters.search.toLowerCase()) ||
        container.image?.toLowerCase().includes(filters.search.toLowerCase())
    );

    const getStatusColor = (status) => {
        const statusLower = status?.toLowerCase() || '';
        if (statusLower.includes('running')) return 'green';
        if (statusLower.includes('paused')) return 'yellow';
        if (statusLower.includes('pending') || statusLower.includes('created')) return 'blue';
        if (statusLower.includes('exited') || statusLower.includes('failed')) return 'red';
        return 'gray';
    };

    const handleContainerAction = async (container, action) => {
        if (container.source !== 'docker') {
            alert('Управление доступно только для Docker контейнеров');
            return;
        }

        const containerId = container.id.replace('docker-', '');
        setActionLoading({ ...actionLoading, [container.id]: action });

        try {
            await dockerContainerAction(containerId, action);
            await refetchContainers();
            alert(`Действие "${action}" выполнено успешно`);
        } catch (error) {
            alert(`Ошибка: ${error.message}`);
        } finally {
            setActionLoading({ ...actionLoading, [container.id]: null });
        }
    };

    const handleSync = async () => {
        try {
            // Синхронизируем Docker хосты
            for (const host of dockerHosts) {
                await syncDockerData(host.id);
            }

            // Синхронизируем Kubernetes кластеры
            for (const cluster of clusters) {
                await syncKubernetesData(cluster.id);
            }

            await refetchContainers();
            alert('Данные успешно синхронизированы!');
        } catch (error) {
            alert('Ошибка синхронизации: ' + error.message);
        }
    };

    const renderActionButtons = (container) => {
        if (container.source !== 'docker') {
            return <span className="text-muted">N/A</span>;
        }

        const loading = actionLoading[container.id];
        const status = container.status?.toLowerCase();

        return (
            <div className="action-buttons">
                {status === 'running' && (
                    <>
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                handleContainerAction(container, 'stop');
                            }}
                            disabled={loading}
                            className="action-btn stop"
                            title="Остановить"
                        >
                            <Square size={14} />
                        </button>
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                handleContainerAction(container, 'restart');
                            }}
                            disabled={loading}
                            className="action-btn restart"
                            title="Перезапустить"
                        >
                            <RotateCw size={14} />
                        </button>
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                handleContainerAction(container, 'pause');
                            }}
                            disabled={loading}
                            className="action-btn pause"
                            title="Приостановить"
                        >
                            <Pause size={14} />
                        </button>
                    </>
                )}
                {(status === 'exited' || status === 'created') && (
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            handleContainerAction(container, 'start');
                        }}
                        disabled={loading}
                        className="action-btn start"
                        title="Запустить"
                    >
                        <Play size={14} />
                    </button>
                )}
                {status === 'paused' && (
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            handleContainerAction(container, 'unpause');
                        }}
                        disabled={loading}
                        className="action-btn start"
                        title="Возобновить"
                    >
                        <Play size={14} />
                    </button>
                )}
            </div>
        );
    };

    const handleRowClick = (container) => {
        if (container.source === 'kubernetes') {
            const podId = container.pod_id || container.id.replace('k8s-', '');
            navigate(`/pods/${podId}`);
        } else if (container.source === 'docker') {
            const containerId = container.id.replace('docker-', '');
            navigate(`/containers/${containerId}`);
        }
    };

    return (
        <div className="containers-page">
            <div className="page-header">
                <h1 className='main-title'>Все контейнеры</h1>
                <button onClick={handleSync} className="sync-button">
                    <RefreshCw size={16} />
                    Синхронизировать
                </button>
            </div>

            {/* Статистика */}
            {statsData && (
                <div className="stats-overview">
                    <div className="stat-group">
                        <h3>Kubernetes</h3>
                        <div className="stat-items">
                            <div className="stat-item">
                                <span className="stat-label">Кластеры:</span>
                                <span className="stat-value">{statsData.kubernetes?.clusters || 0}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Контейнеры:</span>
                                <span className="stat-value">{statsData.kubernetes?.containers || 0}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Запущено:</span>
                                <span className="stat-value green">{statsData.kubernetes?.running || 0}</span>
                            </div>
                        </div>
                    </div>
                    <div className="stat-group">
                        <h3>Docker</h3>
                        <div className="stat-items">
                            <div className="stat-item">
                                <span className="stat-label">Хосты:</span>
                                <span className="stat-value">{statsData.docker?.hosts || 0}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Контейнеры:</span>
                                <span className="stat-value">{statsData.docker?.containers || 0}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Запущено:</span>
                                <span className="stat-value green">{statsData.docker?.running || 0}</span>
                            </div>
                        </div>
                    </div>
                    <div className="stat-group total">
                        <h3>Всего</h3>
                        <div className="stat-items">
                            <div className="stat-item">
                                <span className="stat-label">Контейнеры:</span>
                                <span className="stat-value">{statsData.total?.containers || 0}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Запущено:</span>
                                <span className="stat-value green">{statsData.total?.running || 0}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Активность:</span>
                                <span className="stat-value">{statsData.total?.percentage_running || 0}%</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Фильтры */}
            <div className="filters-section">
                <div className="search-box">
                    <Search size={20} />
                    <input
                        type="text"
                        placeholder="Поиск по имени или образу..."
                        value={filters.search}
                        onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                    />
                </div>

                <div className="filters-row">
                    <Filter size={20} />
                    <select
                        value={filters.source}
                        onChange={(e) => setFilters({ ...filters, source: e.target.value })}
                    >
                        <option value="">Все источники</option>
                        <option value="kubernetes">Kubernetes</option>
                        <option value="docker">Docker</option>
                    </select>

                    <select
                        value={filters.status}
                        onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                    >
                        <option value="">Все статусы</option>
                        <option value="running">Running</option>
                        <option value="paused">Paused</option>
                        <option value="exited">Exited</option>
                        <option value="created">Created</option>
                    </select>
                </div>
            </div>

            {/* Таблица контейнеров */}
            {containersLoading ? (
                <div className="loading">Загрузка контейнеров...</div>
            ) : (
                <div className="table-container">
                    <table className="containers-table">
                        <thead>
                            <tr>
                                <th>Имя</th>
                                <th>Источник</th>
                                <th>Статус</th>
                                <th>Образ</th>
                                <th>Хост/Узел</th>
                                <th>IP</th>
                                <th>Перезапуски</th>
                                <th>Создан</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredContainers.length === 0 ? (
                                <tr>
                                    <td colSpan="9" className="no-data">
                                        Контейнеры не найдены
                                    </td>
                                </tr>
                            ) : (
                                filteredContainers.map((container) => (
                                    <tr
                                        key={container.id}
                                        onClick={() => handleRowClick(container)}
                                        className="clickable"
                                    >
                                        <td className="container-name">{container.name}</td>
                                        <td>
                                            <span className={`source-badge ${container.source}`}>
                                                {container.source === 'kubernetes' ? 'K8s' : 'Docker'}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`status-badge ${getStatusColor(container.status)}`}>
                                                {container.status}
                                            </span>
                                        </td>
                                        <td className="image-name">{container.image}</td>
                                        <td>{container.host_or_node || 'N/A'}</td>
                                        <td>{container.ip_address || 'N/A'}</td>
                                        <td>
                                            {container.restart_count > 0 ? (
                                                <span className="restart-count warning">
                                                    {container.restart_count}
                                                </span>
                                            ) : (
                                                container.restart_count || 0
                                            )}
                                        </td>
                                        <td>
                                            {container.created_at && formatDistanceToNow(new Date(container.created_at), {
                                                addSuffix: true,
                                                locale: ru,
                                            })}
                                        </td>
                                        <td onClick={(e) => e.stopPropagation()}>
                                            {renderActionButtons(container)}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

export default ContainersPage;
