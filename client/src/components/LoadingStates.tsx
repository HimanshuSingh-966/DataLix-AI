import { Skeleton } from '@/components/ui/skeleton';

export function TypingIndicator() {
  return (
    <div className="flex items-start gap-3" data-testid="typing-indicator">
      <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-xs font-semibold text-accent-foreground">
        AI
      </div>
      <div className="bg-card border border-card-border rounded-2xl px-4 py-3">
        <div className="flex gap-1.5">
          <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce-dot" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce-dot" style={{ animationDelay: '200ms' }} />
          <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce-dot" style={{ animationDelay: '400ms' }} />
        </div>
      </div>
    </div>
  );
}

export function TableSkeleton() {
  return (
    <div className="space-y-3" data-testid="table-skeleton">
      <Skeleton className="h-10 w-full" />
      <div className="border border-border rounded-lg overflow-hidden">
        <div className="grid grid-cols-4 gap-4 p-4 bg-muted/30">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-6 w-full" />
          ))}
        </div>
        {[...Array(5)].map((_, rowIdx) => (
          <div key={rowIdx} className="grid grid-cols-4 gap-4 p-4 border-t border-border">
            {[...Array(4)].map((_, colIdx) => (
              <Skeleton key={colIdx} className="h-5 w-full" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="border border-border rounded-lg p-4 bg-card" data-testid="chart-skeleton">
      <Skeleton className="h-6 w-48 mb-4" />
      <Skeleton className="h-96 w-full" />
    </div>
  );
}

export function MessageSkeleton() {
  return (
    <div className="flex items-start gap-3" data-testid="message-skeleton">
      <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
      <div className="flex-1 max-w-3xl space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    </div>
  );
}
