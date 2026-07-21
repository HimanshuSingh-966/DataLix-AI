import { createClient, SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

let supabase: SupabaseClient | null = null;

if (supabaseUrl && supabaseAnonKey) {
  supabase = createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
    },
  });
} else {
  // Supabase not configured, using fallback auth
}

export const getSupabase = () => supabase;
export { supabase };

/**
 * Returns the current access token for API calls.
 *
 * Always prefers the live Supabase session (supabase-js auto-refreshes it, so
 * this never goes stale — unlike localStorage, which only updates on SIGNED_IN).
 * Falls back to localStorage for the backend's fallback-auth mode.
 */
export async function getAccessToken(): Promise<string | null> {
  if (supabase) {
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (token) {
        localStorage.setItem('access_token', token);
        return token;
      }
    } catch {
      // fall through to localStorage
    }
  }
  return localStorage.getItem('access_token');
}