import React from 'react';
import { Shield, Clock, Llm, Code2, Zap, TrendingUp, FileText, Settings } from 'lucide-react';

/* ── Execution Step Renderer ──────────────────────────────────── */
type StepRender = {
  id: number;
  label: string;
  status: 'completed' | 'running' | 'pending';
  timeline?: boolean; // show in timeline view
};

/* ── AI Explainability ────────────────────────────────────────── */
type AiExplainability = {
  executive_summary: string;
  technical_explanation: string;
  business_impact: string;
  attack_scenario: string;
  recommended_mitigation: string;
  confidence: number;
  references: Array<{name: string; cwe?: string; cvss?: number}>;
  reasoning: string;
};

/* ── AI Mission Control Component ─────────────────────────────── */
export default function Timeline({
  aiAnalysis,
  executionSteps,
  executionStatus,
  executionProgress
}) {
  /* Build steps from execution transition history if available */
  const steps: StepRender[] = [
    { id: 1, label: 'Workflow Started', status: 'completed', timeline: true },
    { id: 2, label: 'Spec Parsing', status: 'completed', timeline: true },
    { id: 3, label: 'OWASP Scanning', status: 'completed', timeline: true },
    { id: 4, label: 'Risk Calculation', status: 'completed', timeline: true },
    { id: 5, label: 'AI Analysis', status: aiAnalysis ? 'completed' : 'running', timeline: true },
    { id: 6, label: 'Executive Summary', status: aiAnalysis ? 'completed' : 'pending', timeline: true },
    { id: 7, label: 'Technical Explanation', status: aiAnalysis ? 'completed' : 'pending', timeline: true },
    { id: 8, label: 'Business Impact', status: aiAnalysis ? 'completed' : 'pending', timeline: true },
    { id: 9, label: 'Mitigation Ready', status: aiAnalysis ? 'completed' : 'pending', timeline: true },
  ];

  /* Override steps from execution transition history */
  if (executionSteps && executionSteps.length > 0) {
    const historySteps = executionSteps.map((t: any, i: number) => ({
      id: i + 1,
      label: getStepLabel(t.from, t.to),
      status: t.to === 'completed' ? 'completed' : t.to === 'running' ? 'running' : 'pending',
      timeline: true,
    }));
    /* Replace steps with history, but keep AI step at position 5 */
    steps.splice(4, 1, ...historySteps.slice(0, 5));
  }

  /* Get human-readable step label from state transition */
  const getStepLabel = (from: string, to: string) => {
    const map: Record<string, string> = {
      initialized: 'Workflow Started',
      running: 'Scanning',
      completed: 'Complete',
      failed: 'Failed',
      cancelled: 'Cancelled',
      timeout: 'Timeout',
    };
    return map[to] || `${from} → ${to}`;
  };

  /* Progress bar styling */
  const progressBarStyle = {
    width: `${executionProgress}%`,
    transition: 'width 0.3s ease'
  };

  return (
    <div className="ai-mission-control">
      <div className="mission-header">
        <span className="mission-title">AI MISSION CONTROL</span>
        <span className="mission-status">{executionStatus}</span>
      </div>

      {/* Progress Bar */}
      <div className="progress-bar-container">
        <div className="progress-bar-fill" style={progressBarStyle} />
        <span className="progress-percentage">{executionProgress}%</span>
      </div>

      {/* Step Indicators */}
      <div className="mission-steps">
        {steps.map((step) => (
          <div key={step.id} className="mission-step">
            <span className="step-dot" />
            <span className="step-label">{step.label}</span>
            <span className={`step-status ${step.status}`}>{step.status}</span>
            <span className="step-icon" />
          </div>
        ))}
      </div>

      {/* AI Explainability Panel */}
      {aiAnalysis && (
        <div className="mission-results">
          <div className="results-header">
            <span className="results-title">AI Analysis Generated</span>
            <span className="results-confidence">
              Confidence: {aiAnalysis.confidence}%
            </span>
          </div>

          <div className="results-content">
            <div className="result-section">
              <h4>Evidence</h4>
              <p>{aiAnalysis.executive_summary}</p>
            </div>

            <div className="result-section">
              <h4>Reasoning</h4>
              <p>{aiAnalysis.reasoning}</p>
            </div>

            <div className="result-section">
              <h4>Evidence References</h4>
              <ul>
                {aiAnalysis.references.map((ref, i) => (
                  <li key={i}>
                    {ref.name}{' '}{ref.cwe && <span>(CWE-{ref.cwe})</span>}
                    {ref.cvss && <span>(CVSS {ref.cvss})</span>}
                  </li>
                ))}
              </ul>
            </div>

            <div className="result-section">
              <h4>Risk Assessment</h4>
              <p>{aiAnalysis.business_impact}</p>
            </div>

            <div className="result-section">
              <h4>Attack Scenario</h4>
              <p>{aiAnalysis.attack_scenario}</p>
            </div>

            <div className="result-section">
              <h4>Recommended Mitigation</h4>
              <p>{aiAnalysis.recommended_mitigation}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Styles ───────────────────────────────────────────────────── */
ai-mission-control {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  font-family: system-ui, -apple-system, sans-serif;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}

.mission-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.mission-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
}

.mission-status {
  font-size: 0.875rem;
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  white-space: nowrap;
}

.status-idle {
  background: #e5e7eb;
  color: #6b7280;
}

.status-running {
  background: #fffbeb;
  color: #f59e0b;
}

.status-completed {
  background: #d1e7dd;
  color: #059669;
}

.status-failed {
  background: #fecaca;
  color: #b91c1c;
}

.status-pending {
  background: #e5e7eb;
  color: #6b7280;
}

/* Progress Bar */
.progress-bar-container {
  width: 100%;
  height: 8px;
  background: #f3f4f6;
  border-radius: 9999px;
  overflow: hidden;
  margin: 1rem 0;
}

.progress-bar-fill {
  height: 100%;
  background: #3b82f6;
  width: 0%;
  transition: width 0.3s ease;
}

.progress-percentage {
  position: absolute;
  right: 1rem;
  font-size: 0.75rem;
  color: #6b7280;
  top: 50%;
  transform: translateY(-50%);
}

/* Mission Steps */
.mission-steps {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin: 1rem 0;
}

.mission-step {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
  font-size: 0.75rem;
}

.mission-step:last-child {
  border: none;
}

.step-dot {
  flex: 0 0 6px;
  height: 6px;
  border-radius: 50%;
  background: #9ca3af;
  margin-right: 0.25rem;
}

.step-label {
  flex: 1;
  color: #6b7280;
}

.step-status {
  padding: 0.125rem 0.25rem;
  border-radius: 9999px;
  font-size: 0.65rem;
  font-weight: 500;
  white-space: nowrap;
}

.status-completed {
  background: #d1e7dd;
  color: #059669;
}

.status-running {
  background: #fffbeb;
  color: #f59e0b;
}

.status-pending {
  background: #e5e7eb;
  color: #6b7280;
  opacity: 0.5;
}

/* AI Explainability */
.mission-results {
  background: #f8fafc;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  padding: 1.5rem;
  margin-top: 2rem;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.results-title {
  font-size: 1rem;
  font-weight: 500;
  color: #1f2937;
}

.results-confidence {
  font-size: 0.75rem;
  color: #6b7280;
}

.results-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.result-section {
  display: flex;
  flex-direction: column;
}

.result-section h4 {
  font-size: 0.75rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.25rem;
}

.result-section p {
  font-size: 0.875rem;
  color: #4b5563;
  line-height: 1.4;
}

.result-section ul {
  margin: 0;
  padding-left: 1rem;
}

.result-section li {
  margin-bottom: 0.25rem;
  font-size: 0.8rem;
  color: #4b5563;
}