import type { DataQuality } from '@shared/schema';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, CheckCircle2, Info, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react';
import { formatNumber, getQualityColor, getQualityBgColor, getSeverityColor } from '@/lib/utils';

interface QualityScoreProps {
  quality: DataQuality;
}

export function QualityScore({ quality }: QualityScoreProps) {
  const { overallScore, completeness, consistency, uniqueness, validity, columnMetrics, issues, recommendations } = quality;

  const getQualityIcon = (score: number) => {
    if (score >= 75) return CheckCircle;
    if (score >= 50) return AlertCircle;
    return AlertTriangle;
  };

  const getSeverityIcon = (severity: 'high' | 'medium' | 'low') => {
    if (severity === 'high') return AlertTriangle;
    if (severity === 'medium') return Info;
    return CheckCircle2;
  };

  const QualityIcon = getQualityIcon(overallScore);

  return (
    <div className="space-y-4" data-testid="quality-score">
      {/* Overall Score */}
      <Card className="p-6" data-testid="card-overall-score">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold mb-1" data-testid="text-quality-title">Data Quality Score</h3>
            <p className="text-sm text-muted-foreground" data-testid="text-quality-subtitle">Overall dataset health</p>
          </div>
          <div className="flex flex-col items-end">
            <div className={`text-4xl font-bold ${getQualityColor(overallScore)}`} data-testid="text-quality-score">
              {formatNumber(overallScore, 0)}
              <span className="text-2xl">/100</span>
            </div>
            <QualityIcon className={`h-8 w-8 mt-2 ${getQualityColor(overallScore)}`} data-testid="icon-quality-status" />
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-4 h-2 bg-muted rounded-full overflow-hidden" data-testid="progress-quality">
          <div
            className={`h-full transition-all ${getQualityBgColor(overallScore)}`}
            style={{ width: `${overallScore}%` }}
          />
        </div>
      </Card>

      {/* Breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="quality-breakdown">
        <Card className="p-4" data-testid="card-completeness">
          <div className="text-xs text-muted-foreground mb-1" data-testid="label-completeness">Completeness</div>
          <div className="text-2xl font-bold" data-testid="value-completeness">{formatNumber(completeness * 100, 0)}%</div>
          <div className="mt-2 h-1 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-chart-1" style={{ width: `${completeness * 100}%` }} />
          </div>
        </Card>

        <Card className="p-4" data-testid="card-consistency">
          <div className="text-xs text-muted-foreground mb-1" data-testid="label-consistency">Consistency</div>
          <div className="text-2xl font-bold" data-testid="value-consistency">{formatNumber(consistency * 100, 0)}%</div>
          <div className="mt-2 h-1 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-chart-2" style={{ width: `${consistency * 100}%` }} />
          </div>
        </Card>

        <Card className="p-4" data-testid="card-uniqueness">
          <div className="text-xs text-muted-foreground mb-1" data-testid="label-uniqueness">Uniqueness</div>
          <div className="text-2xl font-bold" data-testid="value-uniqueness">{formatNumber(uniqueness * 100, 0)}%</div>
          <div className="mt-2 h-1 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-chart-3" style={{ width: `${uniqueness * 100}%` }} />
          </div>
        </Card>

        <Card className="p-4" data-testid="card-validity">
          <div className="text-xs text-muted-foreground mb-1" data-testid="label-validity">Validity</div>
          <div className="text-2xl font-bold" data-testid="value-validity">{formatNumber(validity * 100, 0)}%</div>
          <div className="mt-2 h-1 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-chart-4" style={{ width: `${validity * 100}%` }} />
          </div>
        </Card>
      </div>

      {/* Issues */}
      {issues.length > 0 && (
        <Card className="p-6" data-testid="card-issues">
          <h4 className="font-semibold mb-4" data-testid="text-issues-title">Issues Found</h4>
          <div className="space-y-3">
            {issues.map((issue, idx) => {
              const Icon = getSeverityIcon(issue.severity);
              
              return (
                <div key={idx} className="flex items-start gap-3" data-testid={`issue-${idx}`}>
                  <Icon className={`h-5 w-5 mt-0.5 flex-shrink-0 ${getSeverityColor(issue.severity)}`} data-testid={`icon-issue-${idx}`} />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant={issue.severity === 'high' ? 'destructive' : 'secondary'} className="text-xs" data-testid={`badge-severity-${idx}`}>
                        {issue.severity}
                      </Badge>
                      {issue.column && (
                        <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded" data-testid={`text-issue-column-${idx}`}>
                          {issue.column}
                        </span>
                      )}
                    </div>
                    <p className="text-sm" data-testid={`text-issue-description-${idx}`}>{issue.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <Card className="p-6" data-testid="card-recommendations">
          <h4 className="font-semibold mb-4" data-testid="text-recommendations-title">Recommended Actions</h4>
          <ul className="space-y-2">
            {recommendations.map((rec, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm" data-testid={`recommendation-${idx}`}>
                <TrendingUp className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" data-testid={`icon-recommendation-${idx}`} />
                <span data-testid={`text-recommendation-${idx}`}>{rec}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
