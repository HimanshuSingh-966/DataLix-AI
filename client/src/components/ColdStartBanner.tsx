import { useEffect, useState } from 'react';
import { AlertCircle, Loader2, X } from 'lucide-react';

const PYTHON_BACKEND_URL = '/api';

export function ColdStartBanner() {
  const [visible, setVisible] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [canDismiss, setCanDismiss] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const checkBackend = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);
        const res = await fetch('/api/health', { signal: controller.signal });
        clearTimeout(timeout);
        if (res.ok) {
          // Backend is ready
          if (!cancelled) setVisible(false);
          return;
        }
      } catch {
        // Backend not ready yet
        if (!cancelled) setVisible(true);
      }

      // Retry after 3 seconds
      if (!cancelled) {
        setTimeout(checkBackend, 3000);
      }
    };

    checkBackend();

    // Allow dismissal after 3 seconds
    const dismissTimer = setTimeout(() => {
      if (!cancelled) setCanDismiss(true);
    }, 3000);

    return () => {
      cancelled = true;
      clearTimeout(dismissTimer);
    };
  }, []);

  if (!visible || dismissed) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 animate-in slide-in-from-top duration-300">
      <div className="bg-gradient-to-r from-amber-500/90 via-orange-500/90 to-amber-500/90 backdrop-blur-sm text-white px-4 py-2.5 flex items-center justify-center gap-3 shadow-lg">
        <Loader2 className="h-4 w-4 animate-spin shrink-0" />
        <span className="text-sm font-medium">
          Warming up the backend server — this may take up to 30 seconds on first visit...
        </span>
        {canDismiss && (
          <button
            onClick={() => setDismissed(true)}
            className="ml-2 p-0.5 rounded-full hover:bg-white/20 transition-colors shrink-0"
            aria-label="Dismiss banner"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}
