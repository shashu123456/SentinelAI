import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { scans } from '../services/api';
import { Upload, FileText, AlertCircle, Loader2, Shield, Terminal } from 'lucide-react';
import './NewScan.css';

export default function NewScan() {
  const [file, setFile] = useState(null);
  const [apiName, setApiName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [scanMode, setScanMode] = useState('live');
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const handleFile = (f) => {
    setError('');
    if (!f) return;

    const validExts = ['.json', '.yaml', '.yml'];
    const ext = '.' + f.name.split('.').pop().toLowerCase();

    if (!validExts.includes(ext)) {
      setError('Please upload a JSON or YAML file (.json, .yaml, .yml)');
      return;
    }

    if (f.size > 5 * 1024 * 1024) {
      setError('File size must be under 5MB');
      return;
    }

    setFile(f);
    if (!apiName) {
      setApiName(f.name.replace(/\.(json|yaml|yml)$/, ''));
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

    try {
      if (scanMode === 'live') {
        const result = await scans.uploadAsync(file, apiName, true);
        navigate(`/live/${result.task_id}`);
      } else {
        const result = await scans.upload(file, apiName);
        navigate(`/scan/${result.id}`);
      }
    } catch (err) {
      setError(err.message || 'Scan failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="page-content">
      <div className="new-scan-header">
        <h1>New Security Scan</h1>
        <p className="subtitle">Upload an OpenAPI/Swagger specification to analyze</p>
      </div>

      <div className="new-scan-card">
        <form onSubmit={handleSubmit}>
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
              accept=".json,.yaml,.yml"
              onChange={(e) => handleFile(e.target.files[0])}
              style={{ display: 'none' }}
            />

            {file ? (
              <div className="file-selected">
                <FileText size={40} />
                <div className="file-info">
                  <span className="file-name">{file.name}</span>
                  <span className="file-size">{(file.size / 1024).toFixed(1)} KB</span>
                </div>
                <button
                  type="button"
                  className="remove-file"
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                >
                  Remove
                </button>
              </div>
            ) : (
              <>
                <Upload size={48} className="upload-icon" />
                <h3>Drop your OpenAPI specification here</h3>
                <p>or click to browse files</p>
                <span className="file-types">Supports JSON and YAML (.json, .yaml, .yml) - Max 5MB</span>
              </>
            )}
          </div>

          <div className="form-group">
            <label>API Name (optional)</label>
            <input
              type="text"
              value={apiName}
              onChange={(e) => setApiName(e.target.value)}
              placeholder="e.g., User Service API"
            />
          </div>

          <div className="scan-mode-toggle">
            <label className="mode-option">
              <input
                type="radio"
                name="scanMode"
                value="live"
                checked={scanMode === 'live'}
                onChange={() => setScanMode('live')}
              />
              <div className="mode-card">
                <Terminal size={18} />
                <div>
                  <strong>Live Scan</strong>
                  <span>Real-time terminal view with progress tracking</span>
                </div>
              </div>
            </label>
            <label className="mode-option">
              <input
                type="radio"
                name="scanMode"
                value="instant"
                checked={scanMode === 'instant'}
                onChange={() => setScanMode('instant')}
              />
              <div className="mode-card">
                <Shield size={18} />
                <div>
                  <strong>Instant Scan</strong>
                  <span>Quick scan with immediate results</span>
                </div>
              </div>
            </label>
          </div>

          {error && (
            <div className="error-msg">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          <div className="scan-info">
            <h4>What will be scanned:</h4>
            <ul>
              <li>OWASP API Security Top 10 checks (API1-API10)</li>
              <li>Authentication & authorization analysis</li>
              <li>Object property exposure detection</li>
              <li>SSRF & business flow analysis</li>
              <li>AI-powered risk assessment</li>
            </ul>
          </div>

          <button
            type="submit"
            className="scan-btn"
            disabled={!file || uploading}
          >
            {uploading ? (
              <>
                <Loader2 size={16} className="spin" />
                {scanMode === 'live' ? 'Starting live scan...' : 'Scanning...'}
              </>
            ) : (
              <>
                {scanMode === 'live' ? <Terminal size={16} /> : <Shield size={16} />}
                {scanMode === 'live' ? 'Start Live Scan' : 'Start Instant Scan'}
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
