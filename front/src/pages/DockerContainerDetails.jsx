import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
    fetchDockerContainerDetails, 
    fetchDockerContainerLogs,
    dockerContainerAction 
} from '../api/services';
import { ArrowLeft, Download, Play, Square, RotateCw, Pause } from 'lucide-react';
import { format } from 'date-fns';

function DockerContainerDetails() {
    const { id: containerId } = useParams(); // Исправлено
    const navigate = useNavigate();
    const [tailLines, setTailLines] = useState(100);
    const [actionLoading, setActionLoading] = useState(false);

    // Используем containerId в запросах
    const { data: container, isLoading: containerLoading, refetch } = useQuery({
        queryKey: ['dockerContainerDetails', containerId],
        queryFn: () => fetchDockerContainerDetails(containerId),
    });

    const { data: logsData, isLoading: logsLoading, refetch: refetchLogs } = useQuery({
        queryKey: ['dockerContainerLogs', containerId, tailLines],
        queryFn: () => fetchDockerContainerLogs(containerId, tailLines),
        enabled: !!container,
    });

    const handleAction = async (action) => {
        setActionLoading(true);
        try {
            await dockerContainerAction(containerId, action);
            await refetch();
            alert(`Действие "${action}" выполнено успешно`);
        } catch (error) {
            alert(`Ошибка: ${error.message}`);
        } finally {
            setActionLoading(false);
        }
    };

    const downloadLogs = () => {
        const logs = logsData?.logs || '';
        const blob = new Blob([logs], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${container.name}-logs.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    if (containerLoading) {
        return <div className="loading">Загрузка информации о контейнере...</div>;
    }

    if (!container) {
        return <div className="error">Контейнер не найден</div>;
    }

    return (
        <div className="container-details">
            <div className="page-header">
                <button onClick={() => navigate('/containers')} className="back-button">
                    <ArrowLeft size={20} />
                    Назад
                </button>
                <h1 className='title-docker'>{container.name}</h1>
            </div>

            {/* Действия с контейнером */}
            <div className="container-actions">
                {container.status === 'running' && (
                    <>
                        <button 
                            onClick={() => handleAction('stop')} 
                            disabled={actionLoading}
                            className="action-button stop"
                        >
                            <Square size={16} />
                            Остановить
                        </button>
                        <button 
                            onClick={() => handleAction('restart')} 
                            disabled={actionLoading}
                            className="action-button restart"
                        >
                            <RotateCw size={16} />
                            Перезапустить
                        </button>
                        <button 
                            onClick={() => handleAction('pause')} 
                            disabled={actionLoading}
                            className="action-button pause"
                        >
                            <Pause size={16} />
                            Приостановить
                        </button>
                    </>
                )}
                {(container.status === 'exited' || container.status === 'created') && (
                    <button 
                        onClick={() => handleAction('start')} 
                        disabled={actionLoading}
                        className="action-button start"
                    >
                        <Play size={16} />
                        Запустить
                    </button>
                )}
                {container.status === 'paused' && (
                    <button 
                        onClick={() => handleAction('unpause')} 
                        disabled={actionLoading}
                        className="action-button start"
                    >
                        <Play size={16} />
                        Возобновить
                    </button>
                )}
            </div>

            <div className="details-grid">
                <div className="detail-card">
                    <h2>Основная информация</h2>
                    <div className="detail-item">
                        <strong>ID:</strong> {container.container_id?.slice(0, 12)}
                    </div>
                    <div className="detail-item">
                        <strong>Хост:</strong> {container.host_name}
                    </div>
                    <div className="detail-item">
                        <strong>Статус:</strong>
                        <span className={`status-badge ${container.status}`}>
                            {container.status}
                        </span>
                    </div>
                    <div className="detail-item">
                        <strong>Образ:</strong> {container.image}
                    </div>
                    <div className="detail-item">
                        <strong>IP адрес:</strong> {container.ip_address || 'N/A'}
                    </div>
                    <div className="detail-item">
                        <strong>Перезапуски:</strong> {container.restart_count}
                    </div>
                    <div className="detail-item">
                        <strong>Создан:</strong> {format(new Date(container.created), 'dd.MM.yyyy HH:mm:ss')}
                    </div>
                    {container.started_at && (
                        <div className="detail-item">
                            <strong>Запущен:</strong> {format(new Date(container.started_at), 'dd.MM.yyyy HH:mm:ss')}
                        </div>
                    )}
                    {container.uptime && (
                        <div className="detail-item">
                            <strong>Время работы:</strong> {container.uptime}
                        </div>
                    )}
                </div>

                <div className="detail-card">
                    <h2>Сеть</h2>
                    {container.networks && container.networks.length > 0 ? (
                        <>
                            <div className="detail-item">
                                <strong>Сети:</strong> {container.networks.join(', ')}
                            </div>
                        </>
                    ) : (
                        <p>Нет сетевых подключений</p>
                    )}
                    {container.ports && Object.keys(container.ports).length > 0 ? (
                        <div className="detail-item">
                            <strong>Порты:</strong>
                            <ul className="ports-list">
                                {Object.entries(container.ports).map(([containerPort, hostBindings]) => (
                                    <li key={containerPort}>
                                        {containerPort} → {hostBindings ? hostBindings.join(', ') : 'не привязан'}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ) : (
                        <div className="detail-item">
                            <strong>Порты:</strong> Нет проброшенных портов
                        </div>
                    )}
                </div>
            </div>

            <div className="logs-section">
                <div className="logs-header">
                    <h2>Логи</h2>
                    <div className="logs-controls">
                        <select
                            value={tailLines}
                            onChange={(e) => setTailLines(Number(e.target.value))}
                        >
                            <option value={50}>50 строк</option>
                            <option value={100}>100 строк</option>
                            <option value={500}>500 строк</option>
                            <option value={1000}>1000 строк</option>
                        </select>
                        <button onClick={() => refetchLogs()} disabled={logsLoading}>
                            Обновить
                        </button>
                        <button onClick={downloadLogs} disabled={!logsData?.logs}>
                            <Download size={16} />
                            Скачать
                        </button>
                    </div>
                </div>
                <div className="logs-container">
                    {logsLoading ? (
                        <div className="loading">Загрузка логов...</div>
                    ) : (
                        <pre className="logs-content">
                            {logsData?.logs || 'Логи отсутствуют'}
                        </pre>
                    )}
                </div>
            </div>
        </div>
    );
}

export default DockerContainerDetails;
