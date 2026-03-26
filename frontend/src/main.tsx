import { StrictMode, Component } from 'react';
import type { ReactNode, ErrorInfo } from 'react';
import { createRoot } from 'react-dom/client';
import { MantineProvider, createTheme } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { ModalsProvider } from '@mantine/modals';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import '@mantine/dropzone/styles.css';
import '@mantine/spotlight/styles.css';
import '@mantine/charts/styles.css';
import '@mantine/dates/styles.css';

import './index.css';
import App from './App';

/* ========================================================================= */
/* Error Boundary — catches rendering errors and displays them               */
/* ========================================================================= */
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    console.error('[RiskQ360] Uncaught rendering error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: 40,
          fontFamily: '"Plus Jakarta Sans", -apple-system, sans-serif',
          maxWidth: 700,
          margin: '60px auto',
        }}>
          <h1 style={{ color: '#EF4444', fontSize: 24, marginBottom: 12 }}>
            Something went wrong
          </h1>
          <p style={{ color: '#6B7280', fontSize: 14, marginBottom: 20 }}>
            An error occurred while rendering the application. Check the browser console for details.
          </p>
          <pre style={{
            background: '#1F2937',
            color: '#F9FAFB',
            padding: 16,
            borderRadius: 8,
            fontSize: 12,
            overflow: 'auto',
            maxHeight: 300,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}>
            {this.state.error?.message}
            {'\n\n'}
            {this.state.error?.stack}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: 16,
              padding: '8px 20px',
              borderRadius: 8,
              border: 'none',
              background: '#3B82F6',
              color: '#FFFFFF',
              fontWeight: 600,
              fontSize: 14,
              cursor: 'pointer',
            }}
          >
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const mantineTheme = createTheme({
  fontFamily: '"Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  headings: {
    fontFamily: '"Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    fontWeight: '700',
  },
  primaryColor: 'blue',
  defaultRadius: 'md',
  cursorType: 'pointer',
  fontSizes: {
    xs: '11px',
    sm: '13px',
    md: '14px',
    lg: '16px',
    xl: '18px',
  },
  spacing: {
    xs: '6px',
    sm: '10px',
    md: '16px',
    lg: '24px',
    xl: '32px',
  },
  radius: {
    xs: '6px',
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '20px',
  },
  shadows: {
    xs: '0 1px 2px rgba(0,0,0,0.04)',
    sm: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
    md: '0 4px 6px rgba(0,0,0,0.05), 0 2px 4px rgba(0,0,0,0.04)',
    lg: '0 10px 25px rgba(0,0,0,0.08), 0 4px 10px rgba(0,0,0,0.04)',
    xl: '0 20px 50px rgba(0,0,0,0.12), 0 8px 20px rgba(0,0,0,0.06)',
  },
  components: {
    Button: {
      defaultProps: {
        radius: 'md',
      },
      styles: {
        root: {
          fontWeight: 600,
          transition: 'all 150ms cubic-bezier(0.4, 0, 0.2, 1)',
        },
      },
    },
    Card: {
      defaultProps: {
        radius: 'lg',
        shadow: 'sm',
        withBorder: true,
      },
      styles: {
        root: {
          backgroundColor: 'var(--mi-surface)',
          borderColor: 'var(--mi-border)',
        },
      },
    },
    TextInput: {
      defaultProps: {
        radius: 'md',
      },
    },
    Select: {
      defaultProps: {
        radius: 'md',
      },
    },
    Badge: {
      defaultProps: {
        radius: 'md',
        variant: 'light',
      },
      styles: {
        root: {
          fontWeight: 600,
          textTransform: 'none' as const,
        },
      },
    },
    Modal: {
      defaultProps: {
        radius: 'lg',
        overlayProps: {
          backgroundOpacity: 0.35,
          blur: 4,
        },
      },
    },
    ActionIcon: {
      defaultProps: {
        radius: 'md',
        variant: 'subtle',
      },
      styles: {
        root: {
          transition: 'all 150ms cubic-bezier(0.4, 0, 0.2, 1)',
        },
      },
    },
    Tooltip: {
      defaultProps: {
        radius: 'md',
        withArrow: true,
        arrowSize: 6,
        transitionProps: { transition: 'pop', duration: 200 },
      },
    },
    Tabs: {
      defaultProps: {
        radius: 'md',
      },
    },
    Skeleton: {
      defaultProps: {
        radius: 'md',
      },
    },
    Paper: {
      styles: {
        root: {
          backgroundColor: 'var(--mi-surface)',
        },
      },
    },
    Notification: {
      defaultProps: {
        radius: 'md',
      },
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <MantineProvider theme={mantineTheme} defaultColorScheme="auto">
          <ModalsProvider>
            <Notifications
              position="top-right"
              autoClose={4000}
              containerWidth={380}
            />
            <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
              <App />
            </BrowserRouter>
          </ModalsProvider>
        </MantineProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
);
