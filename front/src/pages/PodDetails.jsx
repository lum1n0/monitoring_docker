import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { fetchPods, fetchClusters, fetchNamespaces } from '../api/services';
import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';
import { Search, Filter } from 'lucide-react';

function PodsPage() {
    const navigate = useNavigate();
    const [filters, setFilters] = useState({
        cluster_id: '',
        namespace_name: '',
        status: '',
        search: '',
    });

    const { data: clustersResponse } = useQuery({
        queryKey: ['clusters'],
        queryFn: fetchClusters,
    });

    const clusters = clustersResponse?.results || clustersResponse || [];

    const { data: namespacesResponse } = useQuery({
        queryKey: ['namespaces', filters.cluster_id],
        queryFn: () => fetchNamespaces(filters.cluster_id),
        enabled: !!filters.cluster_id,
    });

    const namespaces = namespacesResponse?.results || namespacesResponse || [];

    const { data: podsResponse, isLoading } = useQuery({
        queryKey: ['pods', filters],
        queryFn: () => {
            const params = {};
            if (filters.cluster_id) params.cluster_id = filters.cluster_id;
            if (filters.namespace_name) params.namespace_name = filters.namespace_name;
            if (filters.status) params.status = filters.status;
            return fetchPods(params);
        },
    });

    const pods = podsResponse?.results || podsResponse || [];

    // Фильтрация по поиску на клиенте
    const filteredPods = pods.filter(pod => 
        !filters.search || 
        pod.name.toLowerCase().includes(filters.search.toLowerCase()) ||
        pod.namespace_name.toLowerCase().includes(filters.search.toLowerCase())
    );

    const getStatusColor = (status) => {
        const colors = {
            'Running': 'green',
            'Pending': 'yellow',
            'Succeeded': 'blue',
            'Failed': 'red',
            'Unknown': 'gray',
        };
        return colors[status] || 'gray';
    };

    return (
        <div className="pods-page">
            <div className="page-header">
                <h1 className='main-title'>Поды</h1>
            </div>

            <div className="filters-section">
                <div className="search-box">
                    <Search size={20} />
                    <input
                        type="text"
                        placeholder="Поиск по имени или namespace..."
                        value={filters.search}
                        onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                    />
                </div>

                <div className="filters-row">
                    <Filter size={20} />
                    <select
                        value={filters.cluster_id}
                        onChange={(e) => setFilters({ ...filters, cluster_id: e.target.value, namespace_name: '' })}
                    >
                        <option value="">Все кластеры</option>
                        {clusters.map((cluster) => (
                            <option key={cluster.id} value={cluster.id}>
                                {cluster.name}
                            </option>
                        ))}
                    </select>

                    {filters.cluster_id && (
                        <select
                            value={filters.namespace_name}
                            onChange={(e) => setFilters({ ...filters, namespace_name: e.target.value })}
                        >
                            <option value="">Все namespaces</option>
                            {namespaces.map((ns) => (
                                <option key={ns.id} value={ns.name}>
                                    {ns.name}
                                </option>
                            ))}
                        </select>
                    )}

                    <select
                        value={filters.status}
                        onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                    >
                        <option value="">Все статусы</option>
                        <option value="Running">Running</option>
                        <option value="Pending">Pending</option>
                        <option value="Failed">Failed</option>
                        <option value="Succeeded">Succeeded</option>
                        <option value="Unknown">Unknown</option>
                    </select>
                </div>
            </div>

            {isLoading ? (
                <div className="loading">Загрузка подов...</div>
            ) : (
                <div className="table-container">
                    <table className="pods-table">
                        <thead>
                            <tr>
                                <th>Имя</th>
                                <th>Namespace</th>
                                <th>Кластер</th>
                                <th>Статус</th>
                                <th>Узел</th>
                                <th>Контейнеры</th>
                                <th>Перезапуски</th>
                                <th>Создан</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredPods.length === 0 ? (
                                <tr>
                                    <td colSpan="8" className="no-data">
                                        Поды не найдены
                                    </td>
                                </tr>
                            ) : (
                                filteredPods.map((pod) => (
                                    <tr
                                        key={pod.id}
                                        onClick={() => navigate(`/pods/${pod.id}`)}
                                        className="clickable"
                                    >
                                        <td className="pod-name">{pod.name}</td>
                                        <td>{pod.namespace_name}</td>
                                        <td>{pod.cluster_name}</td>
                                        <td>
                                            <span className={`status-badge ${getStatusColor(pod.status)}`}>
                                                {pod.status}
                                            </span>
                                        </td>
                                        <td>{pod.node_name || 'N/A'}</td>
                                        <td>{pod.container_count}</td>
                                        <td>
                                            {pod.restart_count > 0 ? (
                                                <span className="restart-count warning">
                                                    {pod.restart_count}
                                                </span>
                                            ) : (
                                                pod.restart_count
                                            )}
                                        </td>
                                        <td>
                                            {formatDistanceToNow(new Date(pod.created_at), {
                                                addSuffix: true,
                                                locale: ru,
                                            })}
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

export default PodsPage;
