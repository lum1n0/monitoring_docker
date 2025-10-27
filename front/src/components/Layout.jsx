import { Outlet, Link, useLocation } from 'react-router-dom';
import { Activity, Box, AlertCircle, Container } from 'lucide-react';

function Layout() {
    const location = useLocation();

    const isActive = (path) => {
        return location.pathname === path ? 'active' : '';
    };

    return (
        <div className="app-container">
            <nav className="sidebar">
                <div className="sidebar-header">
                    <h1>K8s Monitor</h1>
                </div>
                <ul className="nav-menu">
                    <li className={isActive('/')}>
                        <Link to="/">
                            <Activity size={20} />
                            <span>Dashboard</span>
                        </Link>
                    </li>
                    <li className={isActive('/containers')}>
                        <Link to="/containers">
                            <Container size={20} />
                            <span>Containers</span>
                        </Link>
                    </li>
                    <li className={isActive('/pods')}>
                        <Link to="/pods">
                            <Box size={20} />
                            <span>Pods</span>
                        </Link>
                    </li>
                    <li className={isActive('/events')}>
                        <Link to="/events">
                            <AlertCircle size={20} />
                            <span>Events</span>
                        </Link>
                    </li>
                </ul>
            </nav>
            <main className="main-content">
                <Outlet />
            </main>
        </div>
    );
}

export default Layout;
