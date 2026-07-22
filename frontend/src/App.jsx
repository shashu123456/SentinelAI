import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './components/Toast';
import ErrorBoundary from './components/ErrorBoundary';
import Navbar from './components/Navbar';
import './App.css';

const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const NewScan = lazy(() => import('./pages/NewScan'));
const ScanResult = lazy(() => import('./pages/ScanResult'));
const ScanLive = lazy(() => import('./pages/ScanLive'));
const SASTScan = lazy(() => import('./pages/SASTScan'));
const DepScan = lazy(() => import('./pages/DepScan'));
const Copilot = lazy(() => import('./pages/Copilot'));

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

function AppLayout() {
  return (
    <div className="app-layout">
      <Navbar />
      <main className="main-content">
        <Suspense fallback={<PageLoader />}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter>
            <Routes>
              <Route element={<PublicRoute />}>
                <Route path="/login" element={<Suspense fallback={<PageLoader />}><Login /></Suspense>} />
              </Route>
              <Route element={<ProtectedRoute />}>
                <Route element={<AppLayout />}>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/new-scan" element={<NewScan />} />
                  <Route path="/scan/:id" element={<ScanResult />} />
                  <Route path="/live/:taskId" element={<ScanLive />} />
                  <Route path="/sast" element={<SASTScan />} />
                  <Route path="/deps" element={<DepScan />} />
                  <Route path="/copilot" element={<Copilot />} />
                </Route>
              </Route>
              <Route path="*" element={<Navigate to="/dashboard" />} />
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
