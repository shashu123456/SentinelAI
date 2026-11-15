import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
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
import './index.css';

const Landing = lazy(() => import('./pages/Landing'));
const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const NewScan = lazy(() => import('./pages/NewScan'));
const ScanResult = lazy(() => import('./pages/ScanResult'));
const ExecutionDetails = lazy(() => import('./pages/ExecutionDetails'));
const ScanLive = lazy(() => import('./pages/ScanLive'));
const SASTScan = lazy(() => import('./pages/SASTScan'));
const DepScan = lazy(() => import('./pages/DepScan'));
const Copilot = lazy(() => import('./pages/Copilot'));
const VulnerabilityExplorer = lazy(() => import('./pages/VulnerabilityExplorer'));
const AuditCenter = lazy(() => import('./pages/AuditCenter'));
const ReportCenter = lazy(() => import('./pages/ReportCenter'));
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

function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="loading-screen"><div className="spinner" /><p>Loading...</p></div>;
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" />;
}

function PublicRoute() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="loading-screen"><div className="spinner" /><p>Loading...</p></div>;
  return isAuthenticated ? <Navigate to="/dashboard" /> : <Outlet />;
}

function LandingRoute() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="loading-screen"><div className="spinner" /><p>Loading...</p></div>;
  return isAuthenticated ? <Navigate to="/dashboard" /> : <Outlet />;
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
      <MobileNav />
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
                    <Route element={<LandingRoute/>}>
                      <Route path="/" element={<Suspense fallback={<PageLoader/>}><Landing /></Suspense>} />
                    </Route>
                    <Route element={<PublicRoute/>}>
                      <Route path="/login" element={<Suspense fallback={<PageLoader/>}><Login /></Suspense>} />
                    </Route>
                    <Route element={<ProtectedRoute/>}>
                      <Route path="/dashboard" element={<Dashboard />} />
                      <Route path="/new-scan" element={<NewScan />} />
                      <Route path="/scan/:id" element={<ExecutionDetails />} />
                      <Route path="/live/:taskId" element={<ScanLive />} />
                      <Route path="/sast" element={<SASTScan />} />
                      <Route path="/deps" element={<DepScan />} />
                      <Route path="/copilot" element={<Copilot />} />
                      <Route path="/vulnerabilities" element={<VulnerabilityExplorer />} />
                      <Route path="/audit" element={<AuditCenter />} />
                      <Route path="/reports" element={<ReportCenter />} />
                      <Route path="/settings" element={<Settings />} />
                      <Route path="/health" element={<SystemHealth />} />
                      <Route path="/org/dashboard" element={<OrgDashboard />} />
                      <Route path="/org/teams" element={<TeamManagement />} />
                      <Route path="/org/api-keys" element={<ApiKeys />} />
                      <Route path="/org/settings" element={<OrgSettings />} />
                      <Route path="/org/invitations" element={<Invitations />} />
                      <Route path="/security-events" element={<SecurityEvents />} />
                      <Route path="/scheduled-scans" element={<ScheduledScans />} />
                      <Route path="/templates" element={<ScanTemplates />} />
                      <Route path="/policies" element={<PolicyEngine />} />
                      <Route path="/compliance" element={<Compliance />} />
                      <Route path="/webhooks" element={<WebhooksPage />} />
                      <Route path="/exports" element={<ExportCenter />} />
                      <Route path="/executive-report" element={<ExecutiveReport />} />
                      <Route path="/compare" element={<VersionCompare />} />
                      <Route path="/mobile" element={<ExecutiveMobile />} />
                    </Route>
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