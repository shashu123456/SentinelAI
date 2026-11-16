import { CheckCircle2, XCircle, ShieldCheck, Info } from 'lucide-react';
import './Coverage.css';

const SUPPORTED = [
  {
    label: 'OpenAPI / Swagger spec scanning',
    detail: 'Deterministic OWASP API Security Top 10 rules over .json, .yaml, .yml.',
  },
  {
    label: 'Dependency vulnerability scanning',
    detail: 'Known CVEs from live OSV.dev plus a curated fallback, for Python, npm and Maven manifests.',
  },
  {
    label: 'Source-file pattern scanning (SAST)',
    detail: 'Injection, XSS, hardcoded secrets, unsafe crypto, deserialization, path traversal, SSRF.',
  },
];

const NOT_SUPPORTED = [
  { label: 'Repository / full-project scanning', detail: 'Archive scans are capped at 200 files / 2 MB and return a partial report beyond that.' },
  { label: 'Live URL scanning', detail: 'SentinelAI reads an uploaded file; it never sends traffic to a target.' },
  { label: 'Automatic code fixing', detail: 'You get a fix instruction and evidence, not an applied patch.' },
  { label: 'Exploitation or fuzzing', detail: 'No proof-of-concept exploits, auth-bypass proofs or fuzzing.' },
];

export default function Coverage() {
  return (
    <div className="page-content coverage-page">
      <header className="coverage-header">
        <div className="coverage-badge"><ShieldCheck size={12} /> COVERAGE</div>
        <h1>What SentinelAI does</h1>
        <p className="coverage-sub">
          Three scanners, one upload box, deterministic scoring. Here is exactly what is
          supported and what is deliberately not.
        </p>
      </header>

      <section className="coverage-section" aria-labelledby="supported-h">
        <h2 id="supported-h">Supported</h2>
        <ul className="coverage-list">
          {SUPPORTED.map((item) => (
            <li key={item.label} className="coverage-item">
              <CheckCircle2 size={18} className="coverage-ok" aria-hidden="true" />
              <div>
                <strong>{item.label}</strong>
                <span>{item.detail}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="coverage-section" aria-labelledby="not-supported-h">
        <h2 id="not-supported-h">Not supported</h2>
        <ul className="coverage-list">
          {NOT_SUPPORTED.map((item) => (
            <li key={item.label} className="coverage-item">
              <XCircle size={18} className="coverage-no" aria-hidden="true" />
              <div>
                <strong>{item.label}</strong>
                <span>{item.detail}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="coverage-note" aria-labelledby="limits-h">
        <h2 id="limits-h"><Info size={16} /> Limits</h2>
        <ul>
          <li>Three input kinds only: an API spec, a dependency manifest, or a source file / small .zip.</li>
          <li>Uploads are capped at 5 MB. Large code scans return a partial report instead of timing out.</li>
          <li>Dependency data comes from OSV.dev and can lag the upstream advisory by up to an hour (cache TTL).</li>
          <li>SAST is pattern-based: false positives and false negatives are expected.</li>
          <li>AI agent prompt-injection probing is not enabled in this build.</li>
        </ul>
      </section>
    </div>
  );
}
