import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchEvents, fetchClusters } from '../api/services';
import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';
import { AlertCircle, AlertTriangle, Info } from 'lucide-react';

function EventsPage() {
    const [filters, setFilters] = useState({
        cluster: '',
        event_type: '',
        hours: '24',
    });

    const { data: clustersResponse, isLoading: clustersLoading } = useQuery({
        queryKey: ['clusters'],
        queryFn: fetchClusters,
    });

    // Безопасное извлечение массива кластеров
    const clusters = Array.isArray(clustersResponse)
        ? clustersResponse
        : (clustersResponse?.results || []);

    const { data: eventsResponse, isLoading: eventsLoading } = useQuery({
        queryKey: ['events', filters],
        queryFn: () => {
            const params = {};
            if (filters.cluster) params.cluster = filters.cluster;
            if (filters.event_type) params.event_type = filters.event_type;
            if (filters.hours) params.hours = filters.hours;
            return fetchEvents(params);
        },
    });

    // Безопасное извлечение массива событий
    const events = Array.isArray(eventsResponse)
        ? eventsResponse
        : (eventsResponse?.results || []);

    const getEventIcon = (type) => {
        switch (type) {
            case 'Error':
                return <AlertCircle size={20} className="icon-error" />;
            case 'Warning':
                return <AlertTriangle size={20} className="icon-warning" />;
            default:
                return <Info size={20} className="icon-info" />;
        }
    };

    const getEventColor = (type) => {
        const colors = {
            'Error': 'red',
            'Warning': 'yellow',
            'Normal': 'green',
        };
        return colors[type] || 'gray';
    };

    if (clustersLoading) {
        return <div className="loading">Загрузка...</div>;
    }

    return (
        <div className="events-page">
            <div className="page-header">
                <h1 className='main-title'>События</h1>
            </div>

            <div className="filters-section">
                <select
                    value={filters.cluster}
                    onChange={(e) => setFilters({ ...filters, cluster: e.target.value })}
                >
                    <option value="">Все кластеры</option>
                    {clusters.map((cluster) => (
                        <option key={cluster.id} value={cluster.id}>
                            {cluster.name}
                        </option>
                    ))}
                </select>

                <select
                    value={filters.event_type}
                    onChange={(e) => setFilters({ ...filters, event_type: e.target.value })}
                >
                    <option value="">Все типы</option>
                    <option value="Normal">Normal</option>
                    <option value="Warning">Warning</option>
                    <option value="Error">Error</option>
                </select>

                <select
                    value={filters.hours}
                    onChange={(e) => setFilters({ ...filters, hours: e.target.value })}
                >
                    <option value="1">Последний час</option>
                    <option value="6">Последние 6 часов</option>
                    <option value="24">Последние 24 часа</option>
                    <option value="168">Последняя неделя</option>
                </select>
            </div>

            {eventsLoading ? (
                <div className="loading">Загрузка событий...</div>
            ) : (
                <div className="events-list">
                    {events.length === 0 ? (
                        <div className="no-data">События не найдены</div>
                    ) : (
                        events.map((event) => (
                            <div key={event.id} className={`event-item ${getEventColor(event.event_type)}`}>
                                <div className="event-icon">
                                    {getEventIcon(event.event_type)}
                                </div>
                                <div className="event-content">
                                    <div className="event-header">
                                        <strong>{event.reason}</strong>
                                        <span className={`event-type ${getEventColor(event.event_type)}`}>
                                            {event.event_type}
                                        </span>
                                    </div>
                                    <div className="event-details">
                                        <span>{event.involved_object_kind}/{event.involved_object_name}</span>
                                        <span>•</span>
                                        <span>{event.namespace}</span>
                                        {event.count > 1 && (
                                            <>
                                                <span>•</span>
                                                <span className="event-count">×{event.count}</span>
                                            </>
                                        )}
                                    </div>
                                    <div className="event-message">{event.message}</div>
                                    <div className="event-time">
                                        {event.last_timestamp && formatDistanceToNow(new Date(event.last_timestamp), {
                                            addSuffix: true,
                                            locale: ru,
                                        })}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}

export default EventsPage;
