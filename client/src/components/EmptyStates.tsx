import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Upload, Sparkles, FileText, TrendingUp } from 'lucide-react';

interface EmptyStateProps {
  type: 'no-data' | 'no-messages' | 'error';
  onAction?: () => void;
  onExampleDataset?: () => void;
  children?: React.ReactNode;
}

export function EmptyState({ type, onAction, onExampleDataset, children }: EmptyStateProps) {
  if (type === 'no-messages') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] px-6 py-12 text-center" data-testid="empty-state-no-messages">
        <h1 className="font-heading text-4xl md:text-5xl mb-4 text-foreground font-semibold" data-testid="text-welcome-title">
          Welcome to DataLix
        </h1>
        <p className="text-xl text-foreground/80 mb-8 max-w-2xl" data-testid="text-welcome-description">
          Your AI-powered data analysis companion. Upload a dataset and start exploring through natural conversation.
        </p>
        
        <div className="flex flex-col sm:flex-row items-center gap-3 mb-8">
          <Button 
            onClick={() => onAction?.()} 
            size="lg"
            className="min-w-[160px] bg-primary text-primary-foreground hover:bg-primary/90"
            data-testid="button-upload-dataset"
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload Dataset
          </Button>
          <Button 
            onClick={() => onExampleDataset?.()} 
            variant="outline"
            size="lg"
            className="min-w-[160px]"
            data-testid="button-try-example"
          >
            <FileText className="h-4 w-4 mr-2" />
            Try Example
          </Button>
        </div>

        {/* Chat Input Container */}
        <div className="w-full max-w-3xl mb-6">
          {children}
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-3xl mt-8">
          <Card className="p-4 text-left border-border/50 bg-card/50 hover:bg-card transition-colors flex flex-col gap-2">
            <div className="p-2 w-fit rounded-lg bg-primary/10 text-primary">
              <TrendingUp className="h-5 w-5" />
            </div>
            <h3 className="font-medium text-foreground">Correlation</h3>
            <p className="text-sm text-muted-foreground">Find hidden relationships between metrics.</p>
          </Card>
          <Card className="p-4 text-left border-border/50 bg-card/50 hover:bg-card transition-colors flex flex-col gap-2">
            <div className="p-2 w-fit rounded-lg bg-primary/10 text-primary">
              <FileText className="h-5 w-5" />
            </div>
            <h3 className="font-medium text-foreground">Export Data</h3>
            <p className="text-sm text-muted-foreground">Download your cleaned and analyzed data.</p>
          </Card>
          <Card className="p-4 text-left border-border/50 bg-card/50 hover:bg-card transition-colors flex flex-col gap-2">
            <div className="p-2 w-fit rounded-lg bg-primary/10 text-primary">
              <Sparkles className="h-5 w-5" />
            </div>
            <h3 className="font-medium text-foreground">Visualize</h3>
            <p className="text-sm text-muted-foreground">Generate stunning charts automatically.</p>
          </Card>
        </div>
      </div>
    );
  }

  if (type === 'no-data') {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-6 text-center" data-testid="empty-state-no-data">
        <div className="p-6 rounded-full bg-muted mb-4">
          <TrendingUp className="h-10 w-10 text-muted-foreground" />
        </div>
        <h3 className="text-xl font-semibold mb-2">No data loaded</h3>
        <p className="text-muted-foreground mb-4 max-w-sm">
          Upload a dataset to start analyzing and visualizing your data
        </p>
        {onAction && (
          <Button onClick={onAction} data-testid="button-upload-data">
            <Upload className="h-4 w-4 mr-2" />
            Upload Dataset
          </Button>
        )}
      </div>
    );
  }

  if (type === 'error') {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-6 text-center" data-testid="empty-state-error">
        <div className="p-6 rounded-full bg-destructive/10 mb-4">
          <FileText className="h-10 w-10 text-destructive" />
        </div>
        <h3 className="text-xl font-semibold mb-2">Something went wrong</h3>
        <p className="text-muted-foreground mb-4 max-w-sm">
          We encountered an error. Please try again or contact support if the problem persists.
        </p>
        {onAction && (
          <Button onClick={onAction} variant="outline" data-testid="button-retry">
            Try Again
          </Button>
        )}
      </div>
    );
  }

  return null;
}
