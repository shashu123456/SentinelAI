import { ShieldAlert } from 'lucide-react';
import { Link } from 'react-router-dom';
import './Legal.css';

export default function AuthorizedUse() {
  return (
    <div className="page-content legal-page">
      <header className="legal-header">
        <div className="legal-badge"><ShieldAlert size={12} /> AUTHORIZED USE</div>
        <h1>Only scan what you are allowed to scan</h1>
      </header>

      <div className="legal-body">
        <p>
          SentinelAI is a scanning tool, not a license to test anything you can reach. By
          using it you agree that:
        </p>
        <ul>
          <li>You will only scan material you own, or that you have <strong>written permission</strong> to test.</li>
          <li>You will not use a finding to attack, disrupt, or access a system you are not authorised to touch.</li>
          <li>You are responsible for complying with the law and any contract that applies to the target.</li>
        </ul>
        <p>
          The first time you run a scan, you will be asked to confirm this. The confirmation
          is stored against your account with a timestamp and the acceptance version.
        </p>
        <p>
          <Link to="/new-scan">Back to New Scan</Link>
        </p>
      </div>
    </div>
  );
}
