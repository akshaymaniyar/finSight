import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { getLoginUrl, getMe, logout as apiLogout, loginDemo as apiLoginDemo } from '../api/auth';
import type { User } from '../types';

/** Set to true when user arrives via OAuth callback — consumed once by LoginPage. */
let _isOAuthReturn = false;
export function consumeOAuthReturn(): boolean {
  const was = _isOAuthReturn;
  _isOAuthReturn = false;
  return was;
}

interface AuthContextType {
  user: (User & { profile_completed?: boolean; has_gmail_access?: boolean }) | null;
  token: string | null;
  isLoading: boolean;
  login: () => Promise<void>;
  loginDemo: () => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthContextType['user']>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('finsight_token'));
  const [isLoading, setIsLoading] = useState(true);

  const validateToken = useCallback(async (t: string) => {
    try {
      localStorage.setItem('finsight_token', t);
      setToken(t);
      const me = await getMe();
      setUser(me);
      // Store email for returning-user detection
      if (me.email) {
        localStorage.setItem('finsight_email', me.email);
      }
    } catch {
      localStorage.removeItem('finsight_token');
      setToken(null);
      setUser(null);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const me = await getMe();
      setUser(me);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      // Check URL hash for token from OAuth callback
      const hash = window.location.hash;
      if (hash.startsWith('#token=')) {
        const urlToken = hash.slice(7);
        window.history.replaceState(null, '', window.location.pathname);
        _isOAuthReturn = true;
        await validateToken(urlToken);
        setIsLoading(false);
        return;
      }

      // Check localStorage for existing token
      const stored = localStorage.getItem('finsight_token');
      if (stored) {
        await validateToken(stored);
      }
      setIsLoading(false);
    };
    init();
  }, [validateToken]);

  const login = async () => {
    // Pass stored email so returning users skip consent screen
    const storedEmail = localStorage.getItem('finsight_email') || '';
    const { authorization_url } = await getLoginUrl(storedEmail || undefined);
    window.location.href = authorization_url;
  };

  const loginDemoFn = async () => {
    const resp = await apiLoginDemo();
    await validateToken(resp.token);
  };

  const logoutFn = async () => {
    try {
      await apiLogout();
    } catch {
      // ignore
    }
    localStorage.removeItem('finsight_token');
    // Keep finsight_email so returning user detection works
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        loginDemo: loginDemoFn,
        logout: logoutFn,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
