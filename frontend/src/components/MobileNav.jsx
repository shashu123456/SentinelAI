import { useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Upload, AlertTriangle, Bot, FileText,
} from 'lucide-react';
import './MobileNav.css';

const MOBILE_NAV_ITEMS = [
  { path: '/dashboard', label: 'Home', icon: LayoutDashboard },
  { path: '/new-scan', label: 'Scan', icon: Upload },
  { path: '/vulnerabilities', label: 'Alerts', icon: AlertTriangle },
  { path: '/copilot', label: 'AI', icon: Bot },
  { path: '/reports', label: 'Reports', icon: FileText },
];

export default function MobileNav() {
  const location = useLocation();
  const navigate = useNavigate();

  const isActive = (path) => {
    if (path === '/dashboard') return location.pathname === '/' || location.pathname === '/dashboard';
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="mobile-bottom-nav" role="navigation" aria-label="Mobile navigation">
      {MOBILE_NAV_ITEMS.map(item => {
        const Icon = item.icon;
        const active = isActive(item.path);
        return (
          <button
            key={item.path}
            className={`mobile-nav-item ${active ? 'active' : ''}`}
            onClick={() => navigate(item.path)}
            aria-label={item.label}
            aria-current={active ? 'page' : undefined}
            type="button"
          >
            <Icon size={20} strokeWidth={active ? 2.5 : 1.8} />
            <span className="mobile-nav-label">{item.label}</span>
            {active && <span className="mobile-nav-indicator" />}
          </button>
        );
      })}
    </nav>
  );
}
