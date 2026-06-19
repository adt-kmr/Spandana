import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Lock } from 'lucide-react';
import { setOperatorToken, clearOperatorToken } from '../auth';
import { ClearApi, ApiError } from '../api';

export default function OperatorLogin() {
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code) return;
    
    setLoading(true);
    setError(null);
    setOperatorToken(code);
    
    try {
      // Validate by calling an operator endpoint
      await ClearApi.metrics();
      navigate('/operator');
    } catch (err) {
      clearOperatorToken();
      if (err instanceof ApiError) {
        if (err.status === 401 || err.status === 403) {
          setError('Invalid access code.');
        } else if (err.status === 0) {
          setError('Cannot reach server.');
        } else {
          setError(err.detail || 'Login failed.');
        }
      } else {
        setError('Unknown error occurred.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-brutal-bg font-sans">
      <div className="w-full max-w-md">
        <div className="mb-6">
          <Link to="/" className="brutal-btn bg-white hover:bg-gray-100 inline-flex items-center gap-2">
            <ArrowLeft size={20} className="stroke-[3]" /> Gateway
          </Link>
        </div>
        
        <div className="brutal-card bg-brutal-yellow border-[6px] p-8">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-white border-4 border-black rounded-full flex items-center justify-center shadow-[4px_4px_0_0_#000]">
              <Lock size={32} className="text-black" />
            </div>
          </div>
          
          <h1 className="text-3xl font-black uppercase text-center mb-8 tracking-tighter">Operator Login</h1>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-lg font-black uppercase mb-2">Access Code</label>
              <input 
                type="password"
                value={code}
                onChange={e => setCode(e.target.value)}
                className="w-full border-4 border-black rounded p-3 text-lg focus:outline-none focus:ring-4 focus:ring-brutal-blue font-bold shadow-[4px_4px_0_0_#000]"
                placeholder="Enter operator code..."
                autoFocus
              />
            </div>
            
            {error && (
              <div className="bg-brutal-pink text-white font-bold border-4 border-black p-3 text-center uppercase shadow-[4px_4px_0_0_#000]">
                {error}
              </div>
            )}
            
            <button 
              type="submit" 
              disabled={loading || !code}
              className="w-full brutal-btn bg-brutal-blue text-white text-xl disabled:opacity-50"
            >
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
