import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom';
import { Analytics } from '@vercel/analytics/react';
import OperatorDashboard from './pages/OperatorDashboard';
import OperatorStats from './pages/OperatorStats';
import OperatorLogin from './pages/OperatorLogin';
import OperatorPlanning from './pages/OperatorPlanning';
import CitizenView from './pages/CitizenView';
import { LandingPage } from './pages/LandingPage';
import HealthBadge from './components/HealthBadge';
import { isOperatorAuthed } from './auth';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: false,
    },
  },
});

function RequireOperator({ children }: { children: React.ReactNode }) {
  if (!isOperatorAuthed()) {
    return <Navigate to="/operator/login" replace />;
  }
  return <>{children}</>;
}

function App() {
  const isCitizen = !!import.meta.env.VITE_CLEAR_CITIZEN_TOKEN;

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen flex flex-col font-sans bg-brutal-bg text-black">
          {/* Global Health Indicator */}
          <div className="fixed bottom-4 right-4 z-50 pointer-events-none">
            <HealthBadge />
          </div>

          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/operator/login" element={<OperatorLogin />} />
            <Route path="/operator" element={<RequireOperator><OperatorDashboard /></RequireOperator>} />
            <Route path="/operator/stats" element={<RequireOperator><OperatorStats /></RequireOperator>} />
            <Route path="/operator/planning" element={<RequireOperator><OperatorPlanning /></RequireOperator>} />
            {isCitizen && <Route path="/citizen" element={<CitizenView />} />}
            <Route
              path="*"
              element={
                <div className="flex items-center justify-center min-h-screen w-full p-4">
                  <div className="brutal-card p-12 text-center max-w-lg w-full bg-brutal-pink text-white border-[6px]">
                    <h2 className="text-8xl font-black uppercase mb-4 drop-shadow-[4px_4px_0_rgba(0,0,0,1)]">404</h2>
                    <p className="text-2xl font-bold mb-8">Page Not Found or Access Denied.</p>
                    <Link to="/" className="brutal-btn bg-white text-black text-xl inline-block">Return to Gateway</Link>
                  </div>
                </div>
              }
            />
          </Routes>
        </div>
      </BrowserRouter>
      <Analytics />
    </QueryClientProvider>
  );
}

export default App;
