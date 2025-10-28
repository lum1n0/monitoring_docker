// front/src/App.jsx (полный файл)
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ContainersPage from './pages/ContainersPage';
import DockerContainerDetails from './pages/DockerContainerDetails';
import ContainerErrors from './pages/ContainerErrors'
import PodsPage from './pages/PodsPage';
import PodDetails from './pages/PodDetails';
import DockerDashboard from './pages/DockerDashboard';
import EventsPage from './pages/EventsPage';
import Login from './pages/Login';

import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000,
    },
  },
});

function RequireAuth({ children }) {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route index element={<DockerDashboard />} />
            <Route path="containers" element={<ContainersPage />} />
             <Route path="error" element={<ContainerErrors />} />
            <Route path="containers/:id" element={<DockerContainerDetails />} />
            <Route path="pods" element={<PodsPage />} />
            <Route path="pods/:id" element={<PodDetails />} />
            <Route path="events" element={<EventsPage />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;