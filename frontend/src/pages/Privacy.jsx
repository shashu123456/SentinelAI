import { Lock } from 'lucide-react';
import './Legal.css';

export default function Privacy() {
  return (
    <div className="page-content legal-page">
      <header className="legal-header">
        <div className="legal-badge"><Lock size={12} /> PRIVACY</div>
        <h1>What happens to what you upload</h1>
      </header>

      <div className="legal-body">
        <h2>Retention</h2>
        <ul>
          <li>The uploaded file is deleted from the server immediately after the scan completes.</li>
          <li>A stored copy of the parsed specification is deleted after <strong>24 hours</strong>.</li>
          <li>The scan record and its findings stay until you delete them, so Reports keeps working.</li>
        </ul>

        <h2>Redaction</h2>
        <p>
          Values under keys matching <code>key</code>, <code>token</code>, <code>secret</code>,
          <code>password</code>, <code>authorization</code>, <code>bearer</code> or
          <code>apiKey</code> are replaced with <code>***REDACTED***</code> before the
          specification is stored. The value is never logged.
        </p>

        <h2>Outbound calls</h2>
        <p>The only network calls SentinelAI makes on your behalf are:</p>
        <ul>
          <li><strong>api.osv.dev</strong> — to look up known dependency vulnerabilities.</li>
          <li>Nothing else. We never send traffic to a host you upload.</li>
        </ul>

        <h2>Deleting your data</h2>
        <p>
          Settings → “Delete my scan data” removes every scan and report on your account while
          keeping the account itself.
        </p>
      </div>
    </div>
  );
}
