import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { scans, account } from '../services/api';
import {
  Upload, FileText, AlertCircle, Loader2, Shield, Code, Package, FileJson
} from 'lucide-react';
import './NewScan.css';

const KINDS = {
  spec: {
    label: 'API Spec',
    icon: FileJson,
    extensions: ['.json', '.yaml', '.yml'],
    accept: '.json,.yaml,.yml',
    hint: 'JSON or YAML (.json, .yaml, .yml)',
    dropzone: 'Drop your OpenAPI/Swagger specification here',
    button: 'Scan API Spec',
    checks: [
      'OWASP API Security Top 10 checks (API1-API10)',
      'Authentication & authorization analysis',
      'Object property exposure detection',
      'SSRF & business flow analysis',
    ],
  },
  deps: {
    label: 'Dependencies',
    icon: Package,
    extensions: ['.txt', '.json', '.xml', '.in', '.lock', '.zip'],
    accept: '.txt,.json,.xml,.in,.lock,.zip',
    hint: 'requirements.txt, package.json, pom.xml or a .zip of manifests',
    dropzone: 'Drop your dependency manifest here',
    button: 'Scan Dependencies',
    checks: [
      'Known CVEs in pinned packages',
      'CWE mapping and CVSS score per finding',
      'Minimum safe version to upgrade to',
      'Python, JavaScript and Java manifests',
    ],
  },
  code: {
    label: 'Source Code',
    tile: 'SAST · Source Code',
    icon: Code,
    extensions: ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rb', '.php', '.zip'],
    accept: '.py,.js,.jsx,.ts,.tsx,.java,.go,.rb,.php,.zip',
    hint: 'source files or a .zip of a project',
    dropzone: 'Drop a source file or a project .zip here',
    button: 'Scan Source Code',
    checks: [
      'SQL injection, command injection, XSS patterns',
      'Hardcoded secrets and weak cryptography',
      'Unsafe deserialization, path traversal, SSRF',
      'CWE/OWASP mapping with line-level evidence',
    ],
  },
};

const KIND_ORDER = ['spec', 'deps', 'code'];

// Manifests whose extension alone is ambiguous (".json", ".xml") or that have
// no scannable extension at all (".txt", ".in", ".lock").
const DEP_MANIFESTS = [
  'package.json', 'package-lock.json', 'pom.xml', 'pipfile', 'pipfile.lock',
  'poetry.lock', 'composer.json', 'composer.lock', 'go.mod', 'gemfile.lock',
];

const MAX_FILE_BYTES = 5 * 1024 * 1024;

function baseName(name) {
  return (name || '').split(/[/\\]/).pop().toLowerCase();
}

/** Return the kind a file name belongs to, or null when it is ambiguous. */
export function detectKind(filename) {
  const name = baseName(filename);
  if (!name) return null;
  if (name.endsWith('.zip')) return 'code';
  if (DEP_MANIFESTS.includes(name)) return 'deps';
  if (/^requirements.*\.(txt|in)$/.test(name)) return 'deps';
  if (name.endsWith('.lock')) return 'deps';
  if (name.endsWith('.yaml') || name.endsWith('.yml')) return 'spec';
  if (name.endsWith('.json')) return 'spec';
  if (name.endsWith('.txt')) return 'deps';
  if (name.endsWith('.xml')) return 'deps';
  const ext = '.' + name.split('.').pop();
  if (KINDS.code.extensions.includes(ext)) return 'code';
  return null;
}

export default function NewScan() {
  const [searchParams] = useSearchParams();
  const requestedKind = searchParams.get('kind');

  const [kind, setKind] = useState(
    requestedKind && KINDS[requestedKind] ? requestedKind : 'spec'
  );
  const [detected, setDetected] = useState(null);
  const [file, setFile] = useState(null);
  const [apiName, setApiName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [authorized, setAuthorized] = useState(false);
  const [accepted, setAccepted] = useState(true);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (requestedKind && KINDS[requestedKind]) setKind(requestedKind);
  }, [requestedKind]);

  // Has this account already accepted the authorized-use terms?
  useEffect(() => {
    account.authorizedUse()
      .then((state) => {
        if (state && state.accepted) {
          setAccepted(true);
          setAuthorized(true);
        } else {
          setAccepted(false);
        }
      })
      .catch(() => setAccepted(false));
  }, []);

  const active = KINDS[kind];
  const ActiveIcon = active.icon;

  const handleFile = (f) => {
    setError('');
    if (!f) return;

    if (f.size > MAX_FILE_BYTES) {
      setError('File size must be under 5MB');
      return;
    }

    const guessed = detectKind(f.name);
    let target = guessed || kind;

    if (!KINDS[target].extensions.some((ext) => f.name.toLowerCase().endsWith(ext))) {
      setError(
        `${f.name} is not a file this scanner reads. Allowed for ${KINDS[target].label}: ` +
        `${KINDS[target].extensions.join(', ')}`
      );
      return;
    }

    setDetected(guessed);
    setKind(target);
    setFile(f);
    if (!apiName) {
      setApiName(f.name.replace(/\.[^.]+$/, ''));
    }
  };

  const handleKindChange = (next) => {
    setKind(next);
    setDetected(null);
    setError('');
    if (file && !KINDS[next].extensions.some((ext) => file.name.toLowerCase().endsWith(ext))) {
      setFile(null);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    setUploading(true);
    setError('');

    if (!accepted && !authorized) {
      setError('Please confirm you are authorized to scan this material.');
      setUploading(false);
      return;
    }

    try {
      if (!accepted) {
        await account.acceptAuthorizedUse();
        setAccepted(true);
      }
      const result = await scans.upload(file, apiName, kind);
      navigate(`/scan/${result.id}`);
    } catch (err) {
      if (/authorization_required/i.test(err.message || '')) {
        setError('Please accept the authorized-use terms before scanning.');
        navigate('/authorized-use');
        return;
      }
      setError(err.message || 'Scan failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="page-content">
      <div className="new-scan-header">
        <h1>New Security Scan</h1>
        <p className="subtitle">
          These are the three scanners: API spec, dependencies, SAST. The file decides which engine runs.
        </p>
      </div>

      <div className="new-scan-card">
        <form onSubmit={handleSubmit}>
          <div className="scan-mode-toggle three" role="radiogroup" aria-label="Scanner">
            {KIND_ORDER.map((key) => {
              const Icon = KINDS[key].icon;
              return (
                <label key={key} className="mode-option">
                  <input
                    type="radio"
                    name="kind"
                    value={key}
                    checked={kind === key}
                    onChange={() => handleKindChange(key)}
                  />
                  <div className="mode-card">
                    <Icon size={18} />
                    <div>
                      <strong>{KINDS[key].tile || KINDS[key].label}</strong>
                      <span>{KINDS[key].hint}</span>
                    </div>
                  </div>
                </label>
              );
            })}
          </div>

          <div
            className={`dropzone ${dragActive ? 'active' : ''} ${file ? 'has-file' : ''}`}
            onClick={() => fileInputRef.current?.click()}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={active.accept}
              onChange={(e) => handleFile(e.target.files[0])}
              style={{ display: 'none' }}
            />

            {file ? (
              <div className="file-selected">
                <ActiveIcon size={40} />
                <div className="file-info">
                  <span className="file-name">{file.name}</span>
                  <span className="file-size">
                    {(file.size / 1024).toFixed(1)} KB · {active.label} scanner
                  </span>
                </div>
                <button
                  type="button"
                  className="remove-file"
                  onClick={(e) => { e.stopPropagation(); setFile(null); setDetected(null); }}
                >
                  Remove
                </button>
              </div>
            ) : (
              <>
                <Upload size={48} className="upload-icon" />
                <h3>{active.dropzone}</h3>
                <p>or click to browse files</p>
                <span className="file-types">Supports {active.hint} — Max 5MB</span>
              </>
            )}
          </div>

          {detected && (
            <div className="detected-kind">
              <Shield size={14} />
              Detected {KINDS[detected].label.toLowerCase()} — running the {KINDS[detected].label} scanner
            </div>
          )}

          {kind === 'spec' && (
            <div className="form-group">
              <label>API Name (optional)</label>
              <input
                type="text"
                value={apiName}
                onChange={(e) => setApiName(e.target.value)}
                placeholder="e.g., User Service API"
              />
            </div>
          )}

          {error && (
            <div className="error-msg">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          <div className="scan-info">
            <h4>What this scanner checks:</h4>
            <ul>
              {active.checks.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>

          <label className="authorized-check">
            <input
              type="checkbox"
              checked={authorized}
              onChange={(e) => setAuthorized(e.target.checked)}
              disabled={accepted}
            />
            <span>
              I am authorized to scan this material — I own it or have written permission to test it.
            </span>
          </label>

          <button
            type="submit"
            className="scan-btn"
            disabled={!file || uploading || (!accepted && !authorized)}
          >
            {uploading ? (
              <>
                <Loader2 size={16} className="spin" />
                {'Scanning...'}
              </>
            ) : (
              <>
                <FileText size={16} />
                {active.button}
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
