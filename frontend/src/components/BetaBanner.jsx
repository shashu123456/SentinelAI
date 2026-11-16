import { FlaskConical } from 'lucide-react';
import { Link } from 'react-router-dom';

/** Shown only on /beta/* routes: these pages are outside the core workflow. */
export default function BetaBanner() {
  return (
    <div className="beta-banner" role="note">
      <FlaskConical size={15} aria-hidden="true" />
      <span>Beta — not part of the core workflow.</span>
      <Link to="/" className="beta-banner-link">Back to the app</Link>
    </div>
  );
}
