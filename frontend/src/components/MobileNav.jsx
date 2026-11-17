import { useLocation, useNavigate } from 'react-router-dom';
import { Upload, FileText, ShieldCheck, FlaskConical } from 'lucide-react';
import './MobileNav.css';

// The golden path only: three primary destinations plus the quarantined Beta area.
const MOBILE_NAV_ITEMS = [
  { path: '/scans/new', label: 'New Scan', icon: Upload, match: 'exact' },
  { path: '/reports', label: 'Reports', icon: FileText },
  { path: '/coverage', label: 'Coverage', icon: ShieldCheck },
  { path: '/beta/dashboard', label: 'Beta', icon: FlaskConical, match: 'prefix' },
];

export default function MobileNav() {
  const location = useLocation();
  const navigate = useNavigate();

  const isActive = (item) => {
    if (item.match === 'exact') return location.pathname === item.path;
    if (item.match === 'prefix') return location.pathname.startsWith('/beta');
    return location.pathname.startsWith(item.path);
  };

  return (
    <nav className="mobile-bottom-nav" role="navigation" aria-label="Mobile navigation">
      {MOBILE_NAV_ITEMS.map(item => {
        const Icon = item.icon;
        const active = isActive(item);
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
