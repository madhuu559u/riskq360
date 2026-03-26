import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useThemeStore } from './stores/themeStore';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import { applyTheme } from './themes';
import { AppLayout } from './components/layout/AppLayout';
import { ChartList } from './components/charts/ChartList';
import { ChartViewer } from './components/viewer/ChartViewer';
import { DashboardPage } from './components/dashboard/DashboardPage';
import { ConfigPanel } from './components/config/ConfigPanel';
import { LoginPage } from './components/auth/LoginPage';

function RequireAuth({ children }: { children: React.ReactNode }) {
  const isAuth = sessionStorage.getItem('riskq360-auth') === 'true';
  if (!isAuth) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const { theme, isDarkMode } = useThemeStore();

  useKeyboardShortcuts();

  useEffect(() => {
    applyTheme(theme, isDarkMode);
  }, [theme, isDarkMode]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<ChartList />} />
        <Route path="/charts/:chartId" element={<ChartViewer />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/settings" element={<ConfigPanel />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
