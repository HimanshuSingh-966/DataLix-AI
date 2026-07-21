import type { SuggestedAction } from '@shared/schema';
import { Button } from '@/components/ui/button';
import { Sparkles, TrendingUp, Download, BarChart3, AlertCircle } from 'lucide-react';

interface SuggestedActionsProps {
  actions: SuggestedAction[];
  onSelect: (prompt: string) => void;
}

const iconMap: Record<string, any> = {
  clean: AlertCircle,
  statistics: TrendingUp,
  visualization: BarChart3,
  export: Download,
  default: Sparkles,
};

function getIcon(label: string) {
  const lowerLabel = label.toLowerCase();
  if (lowerLabel.includes('clean')) return iconMap.clean;
  if (lowerLabel.includes('statistic') || lowerLabel.includes('correlation')) return iconMap.statistics;
  if (lowerLabel.includes('chart') || lowerLabel.includes('visual') || lowerLabel.includes('plot')) return iconMap.visualization;
  if (lowerLabel.includes('export') || lowerLabel.includes('download')) return iconMap.export;
  return iconMap.default;
}

export function SuggestedActions({ actions, onSelect }: SuggestedActionsProps) {
  if (actions.length === 0) return null;

  return (
    <div className="flex flex-col gap-2" data-testid="suggested-actions">
      <span className="text-xs text-muted-foreground font-medium px-2">Suggested actions:</span>
      <div className="flex flex-wrap gap-2">
        {actions.map((action, idx) => {
          const Icon = getIcon(action.label);
          
          return (
            <Button
              key={idx}
              variant="outline"
              size="sm"
              onClick={() => onSelect(action.prompt)}
              className="rounded-full hover-elevate active-elevate-2"
              data-testid={`action-${action.label.toLowerCase().replace(/\s+/g, '-')}`}
            >
              <Icon className="h-3.5 w-3.5 mr-1.5" />
              {action.label}
            </Button>
          );
        })}
      </div>
    </div>
  );
}
