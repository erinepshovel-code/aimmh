import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ChatProvider } from './contexts/ChatContext';
import { Toaster } from './components/ui/sonner';
import AuthPage from './pages/AuthPage';
import AuthCallback from './pages/AuthCallback';
import ChatPage from './pages/ChatPage';
import SettingsPage from './pages/SettingsPage';
import DashboardPage from './pages/DashboardPage';
import ConsolePage from './pages/ConsolePage';
import PricingPage from './pages/PricingPage';
import { HmmmDoctrineBar } from './components/HmmmDoctrineBar';
import './App.css';

class RouteErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    // eslint-disable-next-line no-console
    console.error('Route render error:', error);
  }

  handleReset = () => {
    localStorage.removeItem('multi_ai_hub_chat');
    window.location.href = '/chat';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background p-4" data-testid="route-error-boundary-state">
          <div className="w-full max-w-md rounded-lg border border-border bg-card p-4 space-y-3">
            <h1 className="text-base font-semibold" data-testid="route-error-boundary-title">We hit a loading error</h1>
            <p className="text-sm text-muted-foreground" data-testid="route-error-boundary-message">
              Please reset local chat cache and reopen Chat.
            </p>
            <button
              type="button"
              className="w-full rounded-md bg-primary text-primary-foreground h-10 text-sm"
              onClick={this.handleReset}
              data-testid="route-error-boundary-reset-btn"
            >
              Reset local chat cache
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }
  
  return isAuthenticated ? children : <Navigate to="/auth" replace />;
};

const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }
  
  return !isAuthenticated ? children : <Navigate to="/chat" replace />;
};

function AppRoutes() {
  const location = useLocation();
  
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  // Check for session_id in URL fragment synchronously (before useEffect)
  if (location.pathname === '/auth/callback' || location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }
  
  return (
    <Routes>
      <Route
        path="/auth"
        element={
          <PublicRoute>
            <AuthPage />
          </PublicRoute>
        }
      />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <SettingsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/console"
        element={
          <ProtectedRoute>
            <ConsolePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pricing"
        element={
          <ProtectedRoute>
            <PricingPage />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/chat" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <ChatProvider>
        <BrowserRouter>
          <div className="App pb-8">
            <RouteErrorBoundary>
              <AppRoutes />
            </RouteErrorBoundary>
            <Toaster position="top-right" theme="dark" />
            <HmmmDoctrineBar />
          </div>
        </BrowserRouter>
      </ChatProvider>
    </AuthProvider>
  );
}

export default App;
