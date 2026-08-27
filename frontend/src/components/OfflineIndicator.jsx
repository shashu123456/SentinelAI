import { useState, useEffect } from 'react';
import { WifiOff, Wifi } from 'lucide-react';
import './OfflineIndicator.css';

/**
 * Offline indicator that shows a banner when the user is offline
 * and a brief notification when they come back online.
 */
export default function OfflineIndicator() {
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [showReconnected, setShowReconnected] = useState(false);

  useEffect(() => {
    const handleOffline = () => {
      setIsOffline(true);
      setShowReconnected(false);
    };

    const handleOnline = () => {
      setIsOffline(false);
      setShowReconnected(true);
      setTimeout(() => setShowReconnected(false), 3000);
    };

    window.addEventListener('offline', handleOffline);
    window.addEventListener('online', handleOnline);

    return () => {
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('online', handleOnline);
    };
  }, []);

  if (isOffline) {
    return (
      <div className="offline-banner" role="alert" aria-live="assertive">
        <WifiOff size={14} />
        <span>You're offline — showing cached data</span>
      </div>
    );
  }

  if (showReconnected) {
    return (
      <div className="reconnected-banner" role="status" aria-live="polite">
        <Wifi size={14} />
        <span>Back online</span>
      </div>
    );
  }

  return null;
}
