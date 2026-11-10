import './Timeline.css';

function Timeline({
  aiAnalysis,
  executionSteps,
  executionStatus,
  executionProgress
}) {
  const steps = [
    { id: 1, label: "Workflow Started", status: "completed", timeline: true },
    { id: 2, label: "Spec Parsing", status: "completed", timeline: true },
    { id: 3, label: "OWASP Scanning", status: "completed", timeline: true },
    { id: 4, label: "Risk Calculation", status: "completed", timeline: true },
    { id: 5, label: "AI Analysis", status: aiAnalysis ? "completed" : "running", timeline: true },
    { id: 6, label: "Executive Summary", status: aiAnalysis ? "completed" : "pending", timeline: true },
    { id: 7, label: "Technical Explanation", status: aiAnalysis ? "completed" : "pending", timeline: true },
    { id: 8, label: "Business Impact", status: aiAnalysis ? "completed" : "pending", timeline: true },
    { id: 9, label: "Mitigation Ready", status: aiAnalysis ? "completed" : "pending", timeline: true }
  ];
  if (executionSteps && executionSteps.length > 0) {
    const historySteps = executionSteps.map((t, i) => ({
      id: i + 1,
      label: getStepLabel(t.from, t.to),
      status: t.to === "completed" ? "completed" : t.to === "running" ? "running" : "pending",
      timeline: true
    }));
    steps.splice(4, 1, ...historySteps.slice(0, 5));
  }
  const getStepLabel = (from, to) => {
    const map = {
      initialized: "Workflow Started",
      running: "Scanning",
      completed: "Complete",
      failed: "Failed",
      cancelled: "Cancelled",
      timeout: "Timeout"
    };
    return map[to] || `${from} \u2192 ${to}`;
  };
  const progressBarStyle = {
    width: `${executionProgress}%`,
    transition: "width 0.3s ease"
  };
  return <div className="ai-mission-control">
      <div className="mission-header">
        <span className="mission-title">AI MISSION CONTROL</span>
        <span className="mission-status">{executionStatus}</span>
      </div>

      {
    /* Progress Bar */
  }
      <div className="progress-bar-container">
        <div className="progress-bar-fill" style={progressBarStyle} />
        <span className="progress-percentage">{executionProgress}%</span>
      </div>

      {
    /* Step Indicators */
  }
      <div className="mission-steps">
        {steps.map((step) => <div key={step.id} className="mission-step">
            <span className="step-dot" />
            <span className="step-label">{step.label}</span>
            <span className={`step-status ${step.status}`}>{step.status}</span>
            <span className="step-icon" />
          </div>)}
      </div>

      {
    /* AI Explainability Panel */
  }
      {aiAnalysis && <div className="mission-results">
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
                {aiAnalysis.references.map((ref, i) => <li key={i}>
                    {ref.name}{" "}{ref.cwe && <span>(CWE-{ref.cwe})</span>}
                    {ref.cvss && <span>(CVSS {ref.cvss})</span>}
                  </li>)}
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
        </div>}
    </div>;
}
export {
  Timeline as default
};
