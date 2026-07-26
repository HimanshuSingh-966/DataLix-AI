import { useEffect } from 'react';
import { useLocation } from 'wouter';
import { getSupabase } from '@/lib/supabase';
import { useAuthStore } from '@/lib/store';
import { useToast } from '@/hooks/use-toast';
import { Loader2 } from 'lucide-react';

export default function AuthCallback() {
  const [, setLocation] = useLocation();
  const { setUser, setToken } = useAuthStore();
  const { toast } = useToast();

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const supabase = getSupabase();
        
        if (!supabase) {
          toast({
            description: 'Supabase not configured. Please use email/password authentication.',
            variant: 'destructive',
          });
          setLocation('/auth');
          return;
        }
        
        const { data, error } = await supabase.auth.getSession();

        if (error) {
          throw error;
        }

        if (data.session) {
          const username = data.session.user.user_metadata?.username || 
                          data.session.user.email?.split('@')[0] || 
                          'user';

          setUser({
            id: data.session.user.id,
            email: data.session.user.email || '',
            username: username,
          });
          
          setToken(data.session.access_token);
          localStorage.setItem('access_token', data.session.access_token);

          toast({ description: 'Successfully signed in with Google!' });
          setLocation('/');
        } else {
          throw new Error('No session found');
        }
      } catch (error) {
      console.error('OAuth callback failed');
      toast({
        description: 'Authentication failed',
          variant: 'destructive',
        });
        setLocation('/auth');
      }
    };

    handleCallback();
  }, [setLocation, setUser, setToken, toast]);

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-background via-background to-muted/20">
      <div className="text-center">
        <Loader2 className="h-12 w-12 animate-spin mx-auto mb-4 text-primary" />
        <h2 className="text-xl font-semibold mb-2">Completing sign-in...</h2>
        <p className="text-muted-foreground">Please wait while we redirect you.</p>
      </div>
    </div>
  );
}
