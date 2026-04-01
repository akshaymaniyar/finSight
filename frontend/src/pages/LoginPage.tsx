import { useState, useEffect } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import {
  IndianRupee,
  BarChart3,
  MessageSquare,
  Shield,
  Mail,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { useAuth, consumeOAuthReturn } from '../context/AuthContext';
import LoadingSpinner from '../components/LoadingSpinner';

const features = [
  {
    icon: Mail,
    title: 'Auto-parse Statements',
    description: 'Automatically extract transactions from bank statement emails.',
  },
  {
    icon: BarChart3,
    title: 'Smart Analytics',
    description: 'Categorized spending breakdowns, trends, and card comparisons.',
  },
  {
    icon: MessageSquare,
    title: 'AI-Powered Chat',
    description: 'Ask questions about your finances in natural language.',
  },
  {
    icon: Shield,
    title: 'Secure & Private',
    description: 'Your data stays on your server. No third-party access.',
  },
];

export default function LoginPage() {
  const { user, isLoading, login, loginDemo } = useAuth();
  const navigate = useNavigate();
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);

  // Handle post-OAuth redirect
  useEffect(() => {
    if (user && consumeOAuthReturn()) {
      // Just came back from Google OAuth — route based on profile status
      if (user.profile_completed) {
        navigate('/dashboard', { replace: true });
      } else {
        navigate('/profile', { replace: true });
      }
    }
  }, [user, navigate]);

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gradient-to-br from-indigo-900 via-indigo-800 to-purple-900">
        <LoadingSpinner size={40} className="text-white" />
      </div>
    );
  }

  // Existing user with token — route based on profile status
  if (user) {
    if (user.profile_completed) {
      return <Navigate to="/dashboard" replace />;
    }
    return <Navigate to="/profile" replace />;
  }

  const handleGoogleLogin = async () => {
    setIsLoggingIn(true);
    try {
      await login();
    } catch {
      setIsLoggingIn(false);
    }
  };

  const handleDemoLogin = async () => {
    setIsDemoLoading(true);
    try {
      await loginDemo();
      navigate('/sync');
    } catch (err) {
      console.error('Demo login failed:', err);
      setIsDemoLoading(false);
    }
  };

  // Check if user has previously logged in (for button text)
  const hasLoggedInBefore = !!localStorage.getItem('finsight_email');

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-indigo-800 to-purple-900 flex items-center justify-center p-4">
      <div className="w-full max-w-5xl flex flex-col lg:flex-row items-center gap-12 lg:gap-16">
        {/* Left side: branding + features */}
        <div className="flex-1 text-center lg:text-left">
          <div className="flex items-center justify-center lg:justify-start gap-3 mb-6">
            <div className="bg-white/15 backdrop-blur-sm rounded-xl p-2.5">
              <IndianRupee size={28} className="text-white" />
            </div>
            <h1 className="text-4xl font-bold text-white tracking-tight">FinSight</h1>
          </div>
          <p className="text-lg text-indigo-200 mb-10 max-w-md mx-auto lg:mx-0">
            Your personal finance dashboard. Auto-parse bank statements, track spending, and get
            AI-powered insights.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {features.map(({ icon: Icon, title, description }) => (
              <div
                key={title}
                className="bg-white/8 backdrop-blur-sm rounded-xl p-4 border border-white/10"
              >
                <div className="flex items-start gap-3">
                  <div className="bg-indigo-500/30 rounded-lg p-2 shrink-0">
                    <Icon size={18} className="text-indigo-200" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white mb-1">{title}</h3>
                    <p className="text-xs text-indigo-300 leading-relaxed">{description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right side: login card */}
        <div className="w-full max-w-sm">
          <div className="bg-white rounded-2xl shadow-2xl p-8">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                {hasLoggedInBefore ? 'Welcome Back' : 'Get Started'}
              </h2>
              <p className="text-sm text-gray-500">
                {hasLoggedInBefore
                  ? 'Sign in to your finance dashboard'
                  : 'Sign in with Google to connect your bank statement emails'}
              </p>
            </div>

            <div className="space-y-3">
              <button
                onClick={handleGoogleLogin}
                disabled={isLoggingIn}
                className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-white border-2 border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoggingIn ? (
                  <LoadingSpinner size={18} />
                ) : (
                  <>
                    <svg viewBox="0 0 24 24" className="w-5 h-5">
                      <path
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                        fill="#4285F4"
                      />
                      <path
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                        fill="#34A853"
                      />
                      <path
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                        fill="#FBBC05"
                      />
                      <path
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                        fill="#EA4335"
                      />
                    </svg>
                    {hasLoggedInBefore ? 'Sign in with Google' : 'Sign in with Google'}
                    <ArrowRight size={16} className="text-gray-400" />
                  </>
                )}
              </button>

              <div className="relative py-3">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200" />
                </div>
                <div className="relative flex justify-center">
                  <span className="bg-white px-3 text-xs text-gray-400">or</span>
                </div>
              </div>

              <button
                onClick={handleDemoLogin}
                disabled={isDemoLoading}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 rounded-xl text-sm font-semibold text-white hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDemoLoading ? (
                  <LoadingSpinner size={18} />
                ) : (
                  <>
                    <Sparkles size={16} />
                    Try Demo
                  </>
                )}
              </button>
            </div>

            <p className="mt-6 text-center text-xs text-gray-400">
              Demo mode creates sample data so you can explore all features.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
