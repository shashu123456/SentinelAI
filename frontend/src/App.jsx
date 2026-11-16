import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet, Link } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { OrgProvider } from './context/OrgContext';
import { ToastProvider } from './components/Toast';
import ErrorBoundary from './components/ErrorBoundary';
import Navbar from './components/Navbar';
import MobileNav from './components/MobileNav';
import OfflineIndicator from './components/OfflineIndicator';
import CommandPalette from './components/CommandPalette';
import { KeyboardShortcutsProvider } from './components/KeyboardShortcuts';
import Breadcrumbs from './components/Breadcrumbs';
import BetaBanner from './components/BetaBanner';
import './styles/tokens.css';
import './index.css';

const Landing = lazy(() => import('./pages/Landing'));
const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const NewScan = lazy(() => import('./pages/NewScan'));
const ExecutionDetails = lazy(() => import('./pages/ExecutionDetails'));
const ReportCenter = lazy(() => import('./pages/ReportCenter'));
const Coverage = lazy(() => import('./pages/Coverage'));
const AuthorizedUse = lazy(() => import('./pages/AuthorizedUse'));
const Privacy = lazy(() => import('./pages/Privacy'));
const ScanLive = lazy(() => import('./pages/ScanLive'));
const Copilot = lazy(() => import('./pages/Copilot'));
const VulnerabilityExplorer = lazy(() => import('./pages/VulnerabilityExplorer'));
const AuditCenter = lazy(() => import('./pages/AuditCenter'));
const Settings = lazy(() => import('./pages/Settings'));
const SystemHealth = lazy(() => import('./pages/SystemHealth'));
const OrgDashboard = lazy(() => import('./pages/OrgDashboard'));
const TeamManagement = lazy(() => import('./pages/TeamManagement'));
const ApiKeys = lazy(() => import('./pages/ApiKeys'));
const OrgSettings = lazy(() => import('./pages/OrgSettings'));
const Invitations = lazy(() => import('./pages/Invitations'));
const SecurityEvents = lazy(() => import('./pages/SecurityEvents'));
const ScheduledScans = lazy(() => import('./pages/ScheduledScans'));
const ScanTemplates = lazy(() => import('./pages/ScanTemplates'));
const PolicyEngine = lazy(() => import('./pages/PolicyEngine'));
const Compliance = lazy(() => import('./pages/Compliance'));
const WebhooksPage = lazy(() => import('./pages/Webhooks'));
const ExportCenter = lazy(() => import('./pages/ExportCenter'));
const ExecutiveReport = lazy(() => import('./pages/ExecutiveReport'));
const VersionCompare = lazy(() => import('./pages/VersionCompare'));
const ExecutiveMobile = lazy(() => import('./pages/ExecutiveMobile'));

function PageLoader() {
  return (
    <div className="page-loader">
      <div className="page-loader-spinner" />
    </div>
  );
}

function withSuspense(node) {
  return <Suspense fallback={<PageLoader />}>{node}</Suspense>;
}

function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="loading-screen"><div className="spinner" /><p>Loading...</p></div>;
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" />;
}

function PublicRoute() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="loading-screen"><div className="spinner" /><p>Loading...</p></div>;
  return isAuthenticated ? <Navigate to="/reports" /> : <Outlet />;
}

function LandingRoute() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="loading-screen"><div className="spinner" /><p>Loading...</p></div>;
  return isAuthenticated ? <Navigate to="/reports" /> : <Outlet />;
}

function Footer() {
  return (
    <footer className="app-footer">
      <span>SentinelAI — three scanners, one upload box.</span>
      <nav className="app-footer-links">
        <Link to="/coverage">Coverage</Link>
        <Link to="/authorized-use">Authorized use</Link>
        <Link to="/privacy">Privacy</Link>
      </nav>
    </footer>
  );
}

function AppLayout() {
  return (
    <div className="app-layout">
      <a href="#main-content" className="skip-to-content">Skip to main content</a>
      <OfflineIndicator />
      <Navbar />
      <main className="main-content" id="main-content" role="main">
        <Breadcrumbs />
        <Suspense fallback={<PageLoader />}>
          <Outlet />
        </Suspense>
      </main>
      <Footer />
      <MobileNav />
    </div>
  );
}

/** Wraps every quarantined page with the beta banner. */
function BetaLayout() {
  return (
    <div className="beta-layout">
      <BetaBanner />
      <Suspense fallback={<PageLoader />}>
        <Outlet />
      </Suspense>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <OrgProvider>
            <ToastProvider>
              <BrowserRouter>
                <KeyboardShortcutsProvider>
                  <CommandPalette />
                  <Routes>
                    <Route element={<LandingRoute />}>
                      <Route path="/" element={withSuspense(<Landing />)} />
                    </Route>
                    <Route element={<PublicRoute />}>
                      <Route path="/login" element={withSuspense(<Login />)} />
                      <Route path="/signup" element={<Navigate to="/login" replace />} />
                    </Route>

                    <Route element={<ProtectedRoute />}>
                      <Route element={<AppLayout />}>
                        {/* ---- Golden path: the only primary pages ---- */}
                        <Route path="/scans/new" element={withSuspense(<NewScan />)} />
                        <Route path="/reports" element={withSuspense(<ReportCenter />)} />
                        <Route path="/coverage" element={withSuspense(<Coverage />)} />
                        <Route path="/scan/:id" element={withSuspense(<ExecutionDetails />)} />
                        <Route path="/authorized-use" element={withSuspense(<AuthorizedUse />)} />
                        <Route path="/privacy" element={withSuspense(<Privacy />)} />

                        {/* ---- Legacy aliases redirect into the golden path ---- */}
                        <Route path="/new-scan" element={<Navigate to="/scans/new" replace />} />
                        <Route path="/deps" element={<Navigate to="/scans/new?kind=deps" replace />} />
                        <Route path="/sast" element={<Navigate to="/scans/new?kind=code" replace />} />
                        <Route path="/dashboard" element={<Navigate to="/reports" replace />} />

                        {/* ---- Everything else is quarantined under /beta ---- */}
                        <Route path="/beta" element={<BetaLayout />}>
                          <Route index element={<Navigate to="/beta/dashboard" replace />} />
                          <Route path="dashboard" element={withSuspense(<Dashboard />)} />
                          <Route path="live/:taskId" element={withSuspense(<ScanLive />)} />
                          <Route path="copilot" element={withSuspense(<Copilot />)} />
                          <Route path="vulnerabilities" element={withSuspense(<VulnerabilityExplorer />)} />
                          <Route path="audit" element={withSuspense(<AuditCenter />)} />
                          <Route path="settings" element={withSuspense(<Settings />)} />
                          <Route path="health" element={withSuspense(<SystemHealth />)} />
                          <Route path="org/dashboard" element={withSuspense(<OrgDashboard />)} />
                          <Route path="org/teams" element={withSuspense(<TeamManagement />)} />
                          <Route path="org/api-keys" element={withSuspense(<ApiKeys />)} />
                          <Route path="org/settings" element={withSuspense(<OrgSettings />)} />
                          <Route path="org/invitations" element={withSuspense(<Invitations />)} />
                          <Route path="security-events" element={withSuspense(<SecurityEvents />)} />
                          <Route path="scheduled-scans" element={withSuspense(<ScheduledScans />)} />
                          <Route path="templates" element={withSuspense(<ScanTemplates />)} />
                          <Route path="policies" element={withSuspense(<PolicyEngine />)} />
                          <Route path="compliance" element={withSuspense(<Compliance />)} />
                          <Route path="webhooks" element={withSuspense(<WebhooksPage />)} />
                          <Route path="exports" element={withSuspense(<ExportCenter />)} />
                          <Route path="executive-report" element={withSuspense(<ExecutiveReport />)} />
                          <Route path="compare" element={withSuspense(<VersionCompare />)} />
                          <Route path="mobile" element={withSuspense(<ExecutiveMobile />)} />
                        </Route>
                      </Route>
                    </Route>

                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </KeyboardShortcutsProvider>
              </BrowserRouter>
            </ToastProvider>
          </OrgProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
