import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';
import OperatorDashboard from './pages/OperatorDashboard';
import CitizenView from './pages/CitizenView';
import HealthBadge from './components/HealthBadge';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: false,
    },
  },
});

function App() {
  const isOperator = !!import.meta.env.VITE_CLEAR_OPERATOR_TOKEN;
  const isCitizen = !!import.meta.env.VITE_CLEAR_CITIZEN_TOKEN;

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen flex flex-col font-sans text-slate-900">
          <header className="bg-slate-900 text-white p-4 flex items-center justify-between sticky top-0 z-50 shadow-md">
            <div className="flex items-center gap-6">
              <h1 className="text-xl font-bold tracking-tight">CLEAR</h1>
              <nav className="flex gap-4">
                {isOperator && (
                  <Link to="/operator" className="text-slate-300 hover:text-white transition-colors">
                    Operator Console
                  </Link>
                )}
                {isCitizen && (
                  <Link to="/citizen" className="text-slate-300 hover:text-white transition-colors">
                    Citizen Portal
                  </Link>
                )}
              </nav>
            </div>
            <HealthBadge />
          </header>

          <main className="flex-1 p-4 bg-slate-50 overflow-auto">
            <Routes>
              <Route path="/" element={<Navigate to={isOperator ? "/operator" : "/citizen"} />} />
              {isOperator && <Route path="/operator" element={<OperatorDashboard />} />}
              {isCitizen && <Route path="/citizen" element={<CitizenView />} />}
              <Route
                path="*"
                element={
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <h2 className="text-2xl font-bold text-slate-700">404 - Not Found</h2>
                      <p className="text-slate-500 mt-2">The page you are looking for does not exist or you lack permissions.</p>
                      <Link to="/" className="text-blue-500 hover:underline mt-4 inline-block">Go Home</Link>
                    </div>
                  </div>
                }
              />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
