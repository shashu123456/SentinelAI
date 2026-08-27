import { useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import './Breadcrumbs.css';

const ROUTE_NAMES = {
  dashboard: { label: 'Dashboard', icon: Home },
  'new-scan': { label: 'New Scan' },
  scan: { label: 'Scan Results' },
  live: { label: 'Live Scan' },
  sast: { label: 'SAST Analysis' },
  deps: { label: 'Dependencies' },
  copilot: { label: 'AI Copilot' },
  vulnerabilities: { label: 'Vulnerabilities' },
  reports: { label: 'Reports' },
  audit: { label: 'Audit Center' },
  settings: { label: 'Settings' },
  health: { label: 'System Health' },
};

export default function Breadcrumbs() {
  const location = useLocation();

  const crumbs = useMemo(() => {
    const parts = location.pathname.split('/').filter(Boolean);
    if (parts.length === 0) return [];

    const result = [];
    let path = '';

    for (const part of parts) {
      path += `/${part}`;
      const route = ROUTE_NAMES[part];

      // Skip numeric IDs in breadcrumb display — show as "Result #<id>"
      if (/^\d+$/.test(part) && result.length > 0) {
        const parentPath = result[result.length - 1]?.path;
        if (parentPath?.includes('scan')) {
          result.push({ label: `#${part}`, path, isLast: false });
          continue;
        }
      }

      if (route) {
        result.push({
          label: route.label,
          path,
          icon: route.icon,
          isLast: false,
        });
      } else {
        result.push({ label: part, path, isLast: false });
      }
    }

    if (result.length > 0) {
      result[result.length - 1].isLast = true;
    }

    return result;
  }, [location.pathname]);

  if (crumbs.length <= 1) return null;

  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <ol className="breadcrumbs-list">
        {crumbs.map((crumb, i) => (
          <li key={crumb.path} className="breadcrumbs-item">
            {i > 0 && <ChevronRight size={12} className="breadcrumbs-sep" />}
            {crumb.isLast ? (
              <span className="breadcrumbs-current" aria-current="page">
                {crumb.icon && <crumb.icon size={13} />}
                {crumb.label}
              </span>
            ) : (
              <Link to={crumb.path} className="breadcrumbs-link">
                {crumb.icon && <crumb.icon size={13} />}
                {crumb.label}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
