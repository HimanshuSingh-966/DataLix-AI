import { Switch, Route, Redirect } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SidebarProvider } from "@/components/ui/sidebar";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useAuthStore } from "@/lib/store";
import { getSupabase } from "@/lib/supabase";
import { useEffect } from "react";
import { ColdStartBanner } from "@/components/ColdStartBanner";
import type { AuthChangeEvent, Session } from "@supabase/supabase-js";
import ChatPage from "@/pages/chat";
import AuthPage from "@/pages/auth";
import AuthCallback from "@/pages/auth-callback";
import NotFound from "@/pages/not-found";

function ProtectedRoute({ component: Component }: { component: () => JSX.Element }) {
  const { isAuthenticated } = useAuthStore();
  
  if (!isAuthenticated) {
    return <Redirect to="/auth" />;
  }
  
  return <Component />;
}

function Router() {
  const { isAuthenticated } = useAuthStore();

  return (
    <Switch>
      <Route path="/auth/callback">
        <AuthCallback />
      </Route>
      <Route path="/auth">
        {isAuthenticated ? <Redirect to="/" /> : <AuthPage />}
      </Route>
      <Route path="/">
        <ProtectedRoute component={ChatPage} />
      </Route>
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  const { setUser, setToken, logout } = useAuthStore();

  useEffect(() => {
    const initAuth = async () => {
      try {
        const supabase = getSupabase();
        
        if (!supabase) {
          console.log('Using local authentication');
          return;
        }
        
        const { data: { session } } = await supabase.auth.getSession();
        
        if (session) {
          const username = session.user.user_metadata?.username || 
                          session.user.email?.split('@')[0] || 
                          'user';

          setUser({
            id: session.user.id,
            email: session.user.email || '',
            username: username,
          });
          setToken(session.access_token);
          localStorage.setItem('access_token', session.access_token);
        }

        const { data: { subscription } } = supabase.auth.onAuthStateChange(
          (event: AuthChangeEvent, session: Session | null) => {
            if ((event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') && session) {
              const username = session.user.user_metadata?.username || 
                              session.user.email?.split('@')[0] || 
                              'user';

              setUser({
                id: session.user.id,
                email: session.user.email || '',
                username: username,
              });
              setToken(session.access_token);
              localStorage.setItem('access_token', session.access_token);
            } else if (event === 'SIGNED_OUT') {
              logout();
              localStorage.removeItem('access_token');
            }
          }
        );

        return () => {
          subscription.unsubscribe();
        };
      } catch (error) {
        console.error('Auth initialization failed');
      }
    };

    initAuth();
  }, [setUser, setToken, logout]);

  const style = {
    "--sidebar-width": "20rem",
    "--sidebar-width-icon": "4rem",
  };

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <ErrorBoundary>
          <SidebarProvider style={style as React.CSSProperties}>
            <ColdStartBanner />
            <Toaster />
            <Router />
          </SidebarProvider>
        </ErrorBoundary>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;