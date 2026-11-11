import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { testimonials as testimonialsApi } from '../services/api';
import TiltCard from '../components/TiltCard';
import {
  Shield, Scan, Bot, FileCode, Package, Upload,
  ArrowRight, ChevronDown, Zap, Activity,
  CheckCircle2, AlertTriangle, Target, Globe,
  ArrowUpRight, Layers, Database, Terminal, Cpu, Fingerprint,
  Sun, Moon
} from 'lucide-react';
import './Landing.css';

// ─── Fade In on Scroll ──────────────────────────────────────────────
function FadeIn({ children, delay = 0, className = '' }) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`fade-in ${visible ? 'visible' : ''} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

// ─── Navigation ─────────────────────────────────────────────────────
function LandingNav() {
  const [scrolled, setScrolled] = useState(false);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav className={`landing-nav ${scrolled ? 'scrolled' : ''}`}>
      <div className="landing-nav-inner">
        <Link to="/" className="landing-nav-brand">
          <div className="landing-nav-logo">
            <Shield size={20} />
          </div>
          <span className="landing-nav-name">SENTINEL<span className="accent">AI</span></span>
        </Link>

        <div className="landing-nav-links">
          <a href="#features" className="landing-nav-link">Features</a>
          <a href="#how-it-works" className="landing-nav-link">How It Works</a>
          <a href="#stats" className="landing-nav-link">Coverage</a>
        </div>

        <div className="landing-nav-actions">
          <button className="landing-nav-theme" onClick={toggleTheme} title="Toggle theme">
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <Link to="/login" className="landing-nav-login">Sign In</Link>
          <Link to="/login" className="landing-nav-cta">
            Get Started
            <ArrowRight size={14} />
          </Link>
        </div>
      </div>
    </nav>
  );
}

// ─── Hero Section ───────────────────────────────────────────────────
function HeroSection() {
  // Generate floating particles once
  const particles = useRef(
    Array.from({ length: 24 }, (_, i) => ({
      id: i,
      left: `${Math.random() * 100}%`,
      size: 2 + Math.random() * 3,
      duration: 8 + Math.random() * 14,
      delay: Math.random() * 10,
      color: ['rgba(0,255,170,0.4)', 'rgba(0,212,255,0.3)', 'rgba(170,102,255,0.25)'][i % 3],
    }))
  ).current;

  return (
    <section className="hero">
      <div className="hero-bg">
        <div className="hero-grid" />
        <div className="hero-glow hero-glow-1" />
        <div className="hero-glow hero-glow-2" />
        <div className="hero-glow hero-glow-3" />
        <div className="hero-ambient hero-ambient-1" />
        <div className="hero-ambient hero-ambient-2" />
        <div className="hero-particles">
          {particles.map(p => (
            <div
              key={p.id}
              className="hero-particle"
              style={{
                left: p.left,
                width: p.size,
                height: p.size,
                background: p.color,
                animationDuration: `${p.duration}s`,
                animationDelay: `${p.delay}s`,
              }}
            />
          ))}
        </div>
      </div>

      <div className="hero-content">
        <FadeIn>
          <div className="hero-badge">
            <Zap size={12} />
            <span>AI-POWERED SECURITY PLATFORM</span>
          </div>
        </FadeIn>

        <FadeIn delay={100}>
          <h1 className="hero-title">
            Detect. Analyze.<br />
            <span className="gradient-text">Remediate.</span>
          </h1>
        </FadeIn>

        <FadeIn delay={200}>
          <p className="hero-subtitle">
            The complete application security platform that identifies vulnerabilities
            across your API surface, source code, and dependencies — then explains
            exactly how to fix them using AI.
          </p>
        </FadeIn>

        <FadeIn delay={300}>
          <div className="hero-actions">
            <Link to="/login" className="hero-btn-primary">
              Start Free Scan
              <ArrowRight size={16} />
            </Link>
            <a href="#how-it-works" className="hero-btn-secondary">
              See How It Works
              <ChevronDown size={16} />
            </a>
          </div>
        </FadeIn>

        <FadeIn delay={400}>
          <div className="hero-trust">
            <div className="hero-trust-engines">
              {['OWASP API Top 10', 'SAST', 'Dependency CVE', 'AI Copilot'].map((name) => (
                <span key={name} className="hero-trust-chip">{name}</span>
              ))}
            </div>
            <div className="hero-trust-text">
              One platform, <strong>four engines</strong>
            </div>
          </div>
        </FadeIn>
      </div>

      <div className="hero-visual">
        <FadeIn delay={500}>
          <div className="hero-radar">
            <div className="radar-rings">
              <div className="radar-ring ring-1" />
              <div className="radar-ring ring-2" />
              <div className="radar-ring ring-3" />
              <div className="radar-ring ring-4" />
            </div>
            <div className="radar-sweep" />
            <div className="radar-center">
              <Shield size={24} />
            </div>
            <div className="radar-blip blip-1">
              <div className="blip-dot critical" />
              <span className="blip-label">API1 — BOLA</span>
            </div>
            <div className="radar-blip blip-2">
              <div className="blip-dot high" />
              <span className="blip-label">API2 — Auth</span>
            </div>
            <div className="radar-blip blip-3">
              <div className="blip-dot medium" />
              <span className="blip-label">API7 — SSRF</span>
            </div>
            <div className="radar-blip blip-4">
              <div className="blip-dot low" />
              <span className="blip-label">API8 — Config</span>
            </div>
            <div className="radar-stats">
              <div className="radar-stat">
                <span className="radar-stat-lbl">SAMPLE SCAN</span>
              </div>
              <div className="radar-stat-divider" />
              <div className="radar-stat">
                <span className="radar-stat-val">47</span>
                <span className="radar-stat-lbl">Endpoints</span>
              </div>
              <div className="radar-stat-divider" />
              <div className="radar-stat">
                <span className="radar-stat-val">12</span>
                <span className="radar-stat-lbl">Findings</span>
              </div>
              <div className="radar-stat-divider" />
              <div className="radar-stat">
                <span className="radar-stat-val danger">72</span>
                <span className="radar-stat-lbl">Risk Score</span>
              </div>
            </div>
          </div>
        </FadeIn>
      </div>

      <div className="hero-scroll-indicator">
        <ChevronDown size={20} />
      </div>
    </section>
  );
}

// ─── Features Section ───────────────────────────────────────────────
const FEATURES = [
  {
    icon: Scan,
    title: 'API Security Scanner',
    description: 'Complete OpenAPI/Swagger analysis with OWASP Top 10 coverage. Discovers endpoints, validates schemas, and detects broken authentication, SSRF, and mass assignment.',
    color: '#00ffaa',
    tag: 'Core Engine',
  },
  {
    icon: FileCode,
    title: 'Static Analysis (SAST)',
    description: '48 security rules across Python, JavaScript, and Java. Detects SQL injection, XSS, hardcoded secrets, command injection, and unsafe deserialization.',
    color: '#aa66ff',
    tag: 'Code Analysis',
  },
  {
    icon: Package,
    title: 'Dependency Scanner',
    description: 'Cross-references your packages against known CVEs. Identifies vulnerable versions and recommends safe upgrades for Python, JavaScript, and Java ecosystems.',
    color: '#ff8800',
    tag: 'Supply Chain',
  },
  {
    icon: Bot,
    title: 'AI Security Copilot',
    description: 'Ask natural language questions about your security posture. Get vulnerability explanations, remediation code, and threat analysis powered by AI.',
    color: '#00d4ff',
    tag: 'Intelligence',
  },
  {
    icon: Shield,
    title: 'Risk Intelligence Engine',
    description: 'Composite risk scoring combining CVSS, confidence levels, and exposure analysis. Get security grades and prioritized remediation paths.',
    color: '#ff3355',
    tag: 'Scoring',
  },
  {
    icon: Layers,
    title: 'Professional Reports',
    description: 'Generate executive, technical, and compliance reports in PDF and JSON formats. Share findings with stakeholders and track remediation progress.',
    color: '#10b981',
    tag: 'Reporting',
  },
];

function FeaturesSection() {
  return (
    <section id="features" className="features-section">
      <div className="section-container">
        <FadeIn>
          <div className="section-badge">
            <Target size={12} />
            <span>PLATFORM CAPABILITIES</span>
          </div>
          <h2 className="section-title">
            Everything you need to<br />
            <span className="gradient-text">secure your applications</span>
          </h2>
          <p className="section-subtitle">
            A unified security platform that covers the entire attack surface —
            from API endpoints to source code to third-party dependencies.
          </p>
        </FadeIn>

        <div className="features-grid">
          {FEATURES.map((feature, i) => (
            <FadeIn key={feature.title} delay={i * 80}>
              <TiltCard intensity={6} glare>
                <div className="feature-card">
                  <div className="feature-card-glow" style={{ background: `${feature.color}08` }} />
                  <div className="feature-icon" style={{ color: feature.color, borderColor: `${feature.color}20` }}>
                    <feature.icon size={22} />
                  </div>
                  <div className="feature-tag" style={{ color: feature.color }}>{feature.tag}</div>
                  <h3 className="feature-title">{feature.title}</h3>
                  <p className="feature-desc">{feature.description}</p>
                  <div className="feature-arrow" style={{ color: feature.color }}>
                    <ArrowUpRight size={16} />
                  </div>
                </div>
              </TiltCard>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── How It Works ───────────────────────────────────────────────────
const STEPS = [
  {
    step: '01',
    icon: Upload,
    title: 'Upload Your Spec',
    description: 'Drop your OpenAPI/Swagger specification, source code files, or dependency manifests. We support JSON, YAML, and all major formats.',
    color: '#00ffaa',
  },
  {
    step: '02',
    icon: Cpu,
    title: 'AI-Powered Analysis',
    description: 'Our engines scan for OWASP Top 10 vulnerabilities, static code issues, and known CVEs. AI analyzes context and generates explanations.',
    color: '#00d4ff',
  },
  {
    step: '03',
    icon: Activity,
    title: 'Get Prioritized Results',
    description: 'Receive a comprehensive risk assessment with severity scores, confidence levels, and business impact analysis for every finding.',
    color: '#aa66ff',
  },
  {
    step: '04',
    icon: CheckCircle2,
    title: 'Fix & Remediate',
    description: 'Get AI-generated fix recommendations, secure code examples, and remediation guidance. Track progress until all issues are resolved.',
    color: '#10b981',
  },
];

function HowItWorksSection() {
  return (
    <section id="how-it-works" className="how-section">
      <div className="section-container">
        <FadeIn>
          <div className="section-badge">
            <Terminal size={12} />
            <span>HOW IT WORKS</span>
          </div>
          <h2 className="section-title">
            From upload to remediation<br />
            <span className="gradient-text">in four steps</span>
          </h2>
        </FadeIn>

        <div className="steps-grid">
          {STEPS.map((step, i) => (
            <FadeIn key={step.step} delay={i * 120}>
              <TiltCard intensity={5}>
                <div className="step-card">
                  <div className="step-number" style={{ color: step.color }}>{step.step}</div>
                  <div className="step-connector" style={{ background: `linear-gradient(180deg, ${step.color}30, transparent)` }} />
                  <div className="step-icon" style={{ color: step.color, borderColor: `${step.color}25` }}>
                    <step.icon size={24} />
                  </div>
                  <h3 className="step-title">{step.title}</h3>
                  <p className="step-desc">{step.description}</p>
                </div>
              </TiltCard>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Stats Section ──────────────────────────────────────────────────
function StatsSection() {
  return (
    <section id="stats" className="stats-section">
      <div className="section-container">
        <FadeIn>
          <div className="section-badge">
            <Database size={12} />
            <span>PLATFORM COVERAGE</span>
          </div>
          <h2 className="section-title">
            Built to cover<br />
            <span className="gradient-text">every layer</span>
          </h2>
        </FadeIn>

        <div className="stats-grid">
          <FadeIn delay={0}><TiltCard intensity={4}><div className="stat-card"><div className="stat-icon"><Scan size={24} /></div><div className="stat-label">OWASP API Top 10</div><div className="stat-sub">Endpoint-by-endpoint coverage</div></div></TiltCard></FadeIn>
          <FadeIn delay={100}><TiltCard intensity={4}><div className="stat-card"><div className="stat-icon"><AlertTriangle size={24} /></div><div className="stat-label">SAST Rules</div><div className="stat-sub">CWE-mapped, multi-language</div></div></TiltCard></FadeIn>
          <FadeIn delay={200}><TiltCard intensity={4}><div className="stat-card"><div className="stat-icon"><CheckCircle2 size={24} /></div><div className="stat-label">CVE Intelligence</div><div className="stat-sub">Python, JavaScript, Java</div></div></TiltCard></FadeIn>
          <FadeIn delay={300}><TiltCard intensity={4}><div className="stat-card"><div className="stat-icon"><Globe size={24} /></div><div className="stat-label">PDF + JSON Reports</div><div className="stat-sub">Executive and technical views</div></div></TiltCard></FadeIn>
        </div>
      </div>
    </section>
  );
}

// ─── Testimonials ───────────────────────────────────────────────────
function TestimonialsSection() {
  const [testimonials, setTestimonials] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    testimonialsApi.list()
      .then(data => setTestimonials(data))
      .catch(() => setTestimonials([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading || testimonials.length === 0) return null;

  return (
    <section id="testimonials" className="testimonials-section">
      <div className="section-container">
        <FadeIn>
          <div className="section-badge">
            <Fingerprint size={12} />
            <span>TRUSTED BY TEAMS</span>
          </div>
          <h2 className="section-title">
            Security teams<br />
            <span className="gradient-text">trust SentinelAI</span>
          </h2>
        </FadeIn>

        <div className="testimonials-grid">
          {testimonials.map((t, i) => (
            <FadeIn key={t.id} delay={i * 100}>
              <div className="testimonial-card">
                <div className="testimonial-quote">"{t.quote}"</div>
                <div className="testimonial-author">
                  <div className="testimonial-avatar">{t.avatar_letter}</div>
                  <div>
                    <div className="testimonial-name">{t.author_name}</div>
                    <div className="testimonial-role">{t.author_role}, {t.author_company}</div>
                  </div>
                </div>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── CTA Section ────────────────────────────────────────────────────
function CTASection() {
  return (
    <section className="cta-section">
      <div className="section-container">
        <FadeIn>
          <div className="cta-card">
            <div className="cta-glow" />
            <h2 className="cta-title">
              Ready to secure your<br />
              <span className="gradient-text">applications?</span>
            </h2>
            <p className="cta-subtitle">
              Start scanning in minutes. No credit card required.
            </p>
            <div className="cta-actions">
              <Link to="/login" className="cta-btn-primary">
                Start Free Scan
                <ArrowRight size={16} />
              </Link>
              <Link to="/login" className="cta-btn-secondary">
                Create Account
              </Link>
            </div>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}

// ─── Footer ─────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="landing-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <Link to="/" className="footer-logo">
            <Shield size={20} />
            <span>SENTINEL<span className="accent">AI</span></span>
          </Link>
          <p className="footer-tagline">
            AI-Powered Application Security Intelligence Platform
          </p>
        </div>

        <div className="footer-links">
          <div className="footer-col">
            <h4>Product</h4>
            <a href="#features">Features</a>
            <a href="#how-it-works">How It Works</a>
            <a href="#stats">Coverage</a>
            <Link to="/login">Get Started</Link>
          </div>
          <div className="footer-col">
            <h4>Capabilities</h4>
            <a href="#features">API Scanner</a>
            <a href="#features">SAST Analysis</a>
            <a href="#features">Dependency Scan</a>
            <a href="#features">AI Copilot</a>
          </div>
          <div className="footer-col">
            <h4>Access</h4>
            <Link to="/login">Sign In</Link>
            <Link to="/login">Create Account</Link>
          </div>
        </div>
      </div>

      <div className="footer-bottom">
        <span>© 2026 SentinelAI. All rights reserved.</span>
        <span className="footer-version">v1.0.0</span>
      </div>
    </footer>
  );
}

// ─── Main Landing Page ──────────────────────────────────────────────
export default function Landing() {
  return (
    <div className="landing-page">
      <LandingNav />
      <HeroSection />
      <FeaturesSection />
      <HowItWorksSection />
      <StatsSection />
      <TestimonialsSection />
      <CTASection />
      <Footer />
    </div>
  );
}
