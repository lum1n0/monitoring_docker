// front/src/api/services.js (полный файл)
import axios from './axios';

// Auth
export const login = async (username, password) => {
  const response = await axios.post('/auth/login/', { username, password });
  return response.data; // { token: '...' }
};

export const logout = () => {
  localStorage.removeItem('token');
};

// Clusters
export const fetchClusters = async () => {
  const response = await axios.get('/clusters/');
  return response.data;
};

export const fetchClusterStats = async (clusterId) => {
  const response = await axios.get(`/clusters/${clusterId}/stats/`);
  return response.data;
};

export const fetchClusterHealth = async (clusterId) => {
  const response = await axios.get(`/clusters/${clusterId}/health/`);
  return response.data;
};

// Namespaces
export const fetchNamespaces = async (clusterId) => {
  const params = clusterId ? { cluster_id: clusterId } : {};
  const response = await axios.get('/namespaces/', { params });
  return response.data;
};

// Pods
export const fetchPods = async (filters = {}) => {
  const response = await axios.get('/pods/', { params: filters });
  return response.data;
};

export const fetchPodDetails = async (podId) => {
  const response = await axios.get(`/pods/${podId}/`);
  return response.data;
};

export const fetchPodLogs = async (podId, containerName = null, tail = 100) => {
  const params = { tail };
  if (containerName) params.container = containerName;
  const response = await axios.get(`/pods/${podId}/logs/`, { params });
  return response.data;
};

// Containers
export const fetchContainers = async (podId) => {
  const response = await axios.get('/containers/', { params: { pod: podId } });
  return response.data;
};

export const fetchContainerMetrics = async (containerId, hours = 1) => {
  const response = await axios.get(`/containers/${containerId}/metrics/`, {
    params: { hours },
  });
  return response.data;
};

// Events
export const fetchEvents = async (filters = {}) => {
  const response = await axios.get('/events/', { params: filters });
  return response.data;
};

// Sync
export const syncKubernetesData = async (clusterId) => {
  const response = await axios.post('/sync/', { cluster_id: clusterId });
  return response.data;
};

// Docker Hosts
export const fetchDockerHosts = async () => {
  const response = await axios.get('/docker/hosts/');
  return response.data;
};

export const fetchDockerHostInfo = async (hostId) => {
  const response = await axios.get(`/docker/hosts/${hostId}/info/`);
  return response.data;
};

export const fetchDockerHostStats = async (hostId) => {
  const response = await axios.get(`/docker/hosts/${hostId}/stats/`);
  return response.data;
};

export const fetchDockerHostHealth = async (hostId) => {
  const response = await axios.get(`/docker/hosts/${hostId}/health/`);
  return response.data;
};

// Docker Containers
export const fetchDockerContainers = async (filters = {}) => {
  const response = await axios.get('/docker/containers/', { params: filters });
  return response.data;
};

export const fetchDockerContainerDetails = async (containerId) => {
  const response = await axios.get(`/docker/containers/${containerId}/`);
  return response.data;
};

export const fetchDockerContainerLogs = async (containerId, tail = 100) => {
  const response = await axios.get(`/docker/containers/${containerId}/logs/`, {
    params: { tail },
  });
  return response.data;
};

export const fetchDockerContainerMetrics = async (containerId, hours = 1) => {
  const response = await axios.get(`/docker/containers/${containerId}/metrics/`, {
    params: { hours },
  });
  return response.data;
};

export const dockerContainerAction = async (containerId, action) => {
  const response = await axios.post(`/docker/containers/${containerId}/action/`, {
    action,
  });
  return response.data;
};

// Docker Sync
export const syncDockerData = async (hostId) => {
  const response = await axios.post('/docker/sync/', { host_id: hostId });
  return response.data;
};

// Unified views
export const fetchUnifiedContainers = async (filters = {}) => {
  const response = await axios.get('/unified/containers/', { params: filters });
  return response.data;
};

export const fetchUnifiedStats = async () => {
  const response = await axios.get('/unified/stats/');
  return response.data;
};
