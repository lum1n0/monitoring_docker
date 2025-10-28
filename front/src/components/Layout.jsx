import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Activity, Box, AlertCircle, Container, ChevronLeft, ChevronRight } from 'lucide-react';

function Layout() {
    const location = useLocation();
    const [collapsed, setCollapsed] = useState(false);

    const isActive = (path) => {
        return location.pathname === path ? 'active' : '';
    };

    return (
        <div className="app-container">
            <nav className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
                <div className="sidebar-header">
                    <h1>{!collapsed && 'K8s Monitor'}</h1>
                    <button
                        className="toggle-btn"
                        onClick={() => setCollapsed(!collapsed)}
                        title={collapsed ? 'Развернуть' : 'Свернуть'}
                    >
                        {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
                    </button>
                </div>
                <ul className="nav-menu">
                    <li className={isActive('/')}>
                        <Link to="/" title="Dashboard">
                            <Activity size={20} />
                            {!collapsed && <span>Dashboard</span>}
                        </Link>
                    </li>
                    <li className={isActive('/containers')}>
                        <Link to="/containers" title="Containers">
                            <Container size={20} />
                            {!collapsed && <span>Containers</span>}
                        </Link>
                    </li><li className={isActive('/error')}>
                        <Link to="/error" title="Containers">
                            <Container size={20} />
                            {!collapsed && <span>ContaContainerErrorsiners</span>}
                        </Link>
                    </li>
                    <li className={isActive('/pods')}>
                        <Link to="/pods" title="Pods">
                            <Box size={20} />
                            {!collapsed && <span>Pods</span>}
                        </Link>
                    </li>
                    <li className={isActive('/events')}>
                        <Link to="/events" title="Events">
                            <AlertCircle size={20} />
                            {!collapsed && <span>Events</span>}
                        </Link>
                    </li>
                </ul>
            </nav>
            <main className={`main-content ${collapsed ? 'sidebar-collapsed' : ''}`}>
                <Outlet />
            </main>
        </div>
    );
}

export default Layout;
