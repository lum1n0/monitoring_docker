// ContainerErrors.jsx

import React, { useEffect, useState } from 'react';

function ContainerErrors({ containerId, containerType }) {
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchErrors = async () => {
    setLoading(true);
    const params = new URLSearchParams({
      container_id: containerId,
      container_type: containerType,
      ordering: '-timestamp',
    });
    const response = await fetch(`/api/container-errors/?${params}`);
    const data = await response.json();
    setErrors(data.results || []);
    setLoading(false);
  };

  useEffect(() => {
    if (containerId && containerType) {
      fetchErrors();
    }
  }, [containerId, containerType]);

  if (loading) return <p>Загрузка ошибок...</p>;

  if (!errors.length) return <p>Ошибок не найдено.</p>;

  return (
    <div>
      <h3>Ошибки контейнера</h3>
      <ul>
        {errors.map(error => (
          <li key={error.id}>
            <strong>{error.timestamp}</strong>: {error.short_description}
            <pre>{error.full_log}</pre>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default ContainerErrors;
