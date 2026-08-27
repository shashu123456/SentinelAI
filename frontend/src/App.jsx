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
import './App.css';

const Landing = lazy(() => import('./pages/Landing'));
const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const NewScan = lazy(() => import('./pages/NewScan'));
const ScanResult = lazy(() => import('./pages/ScanResult'));
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
      <OfflineIndicator />
      <Navbar />
      <main className="main-content">
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
    <ErrorBoundary>        <ThemeProvider>
      <AuthProvider>
      <OrgProvider>
        <ToastProvider>
          <BrowserRouter>
            <KeyboardShortcutsProvider>
            <CommandPalette />
            <Routes>
              <Route element={<LandingRoute />}>
                <Route path="/" element={<Suspense fallback={<PageLoader />}><Landing /></Suspense>} />
              </Route>
              <Route element={<PublicRoute />}>
                <Route path="/login" element={<Suspense fallback={<PageLoader />}><Login /></Suspense>} />
              </Route>
              <Route element={<ProtectedRoute />}>
                <Route element={<AppLayout />}>
                  <Route path="/dashboard" element={<ErrorBoundary pageLevel><Dashboard /></ErrorBoundary>} />
                  <Route path="/new-scan" element={<ErrorBoundary pageLevel><NewScan /></ErrorBoundary>} />
                  <Route path="/scan/:id" element={<ErrorBoundary pageLevel><ScanResult /></ErrorBoundary>} />
                  <Route path="/live/:taskId" element={<ErrorBoundary pageLevel><ScanLive /></ErrorBoundary>} />
                  <Route path="/sast" element={<ErrorBoundary pageLevel><SASTScan /></ErrorBoundary>} />
                  <Route path="/deps" element={<ErrorBoundary pageLevel><DepScan /></ErrorBoundary>} />
                  <Route path="/copilot" element={<ErrorBoundary pageLevel><Copilot /></ErrorBoundary>} />
                  <Route path="/vulnerabilities" element={<ErrorBoundary pageLevel><VulnerabilityExplorer /></ErrorBoundary>} />
                  <Route path="/audit" element={<ErrorBoundary pageLevel><AuditCenter /></ErrorBoundary>} />
                  <Route path="/reports" element={<ErrorBoundary pageLevel><ReportCenter /></ErrorBoundary>} />
                  <Route path="/settings" element={<ErrorBoundary pageLevel><Settings /></ErrorBoundary>} />
                  <Route path="/health" element={<ErrorBoundary pageLevel><SystemHealth /></ErrorBoundary>} />
                  <Route path="/org/dashboard" element={<ErrorBoundary pageLevel><OrgDashboard /></ErrorBoundary>} />
                  <Route path="/org/teams" element={<ErrorBoundary pageLevel><TeamManagement /></ErrorBoundary>} />
                  <Route path="/org/api-keys" element={<ErrorBoundary pageLevel><ApiKeys /></ErrorBoundary>} />
                  <Route path="/org/settings" element={<ErrorBoundary pageLevel><OrgSettings /></ErrorBoundary>} />
                  <Route path="/org/invitations" element={<ErrorBoundary pageLevel><Invitations /></ErrorBoundary>} />
                  <Route path="/security-events" element={<ErrorBoundary pageLevel><SecurityEvents /></ErrorBoundary>} />
                  <Route path="/scheduled-scans" element={<ErrorBoundary pageLevel><ScheduledScans /></ErrorBoundary>} />
                  <Route path="/templates" element={<ErrorBoundary pageLevel><ScanTemplates /></ErrorBoundary>} />
                  <Route path="/policies" element={<ErrorBoundary pageLevel><PolicyEngine /></ErrorBoundary>} />
                  <Route path="/compliance" element={<ErrorBoundary pageLevel><Compliance /></ErrorBoundary>} />
                  <Route path="/webhooks" element={<ErrorBoundary pageLevel><WebhooksPage /></ErrorBoundary>} />
                  <Route path="/exports" element={<ErrorBoundary pageLevel><ExportCenter /></ErrorBoundary>} />
                  <Route path="/executive-report" element={<ErrorBoundary pageLevel><ExecutiveReport /></ErrorBoundary>} />
                  <Route path="/compare" element={<ErrorBoundary pageLevel><VersionCompare /></ErrorBoundary>} />
                  <Route path="/mobile" element={<ErrorBoundary pageLevel><ExecutiveMobile /></ErrorBoundary>} />
                </Route>
              </Route>
              <Route path="*" element={<Navigate to="/" />} />
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
