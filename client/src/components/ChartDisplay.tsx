import { useEffect, useRef } from 'react';
import type { PlotlyChartData } from '@shared/schema';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';

interface ChartDisplayProps {
  chartData: PlotlyChartData;
  title?: string;
}

export function ChartDisplay({ chartData, title }: ChartDisplayProps) {
  const plotRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!plotRef.current) return;

    const computedStyle = getComputedStyle(document.documentElement);
    const foregroundHSL = computedStyle.getPropertyValue('--foreground').trim();
    const fontColor = `hsl(${foregroundHSL})`;

    import('plotly.js-dist-min').then((Plotly) => {
      if (plotRef.current) {
        Plotly.newPlot(
          plotRef.current,
          chartData.data,
          {
            ...chartData.layout,
            autosize: true,
            margin: { l: 50, r: 50, t: title ? 50 : 30, b: 50 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {
              family: 'Inter, sans-serif',
              color: fontColor,
            },
          },
          {
            ...chartData.config,
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['toImage'],
          }
        );
      }
    });

    return () => {
      if (plotRef.current) {
        import('plotly.js-dist-min').then((Plotly) => {
          if (plotRef.current) {
            Plotly.purge(plotRef.current);
          }
        });
      }
    };
  }, [chartData, title]);

  const handleExport = () => {
    if (!plotRef.current) return;

    import('plotly.js-dist-min').then((Plotly) => {
      if (plotRef.current) {
        Plotly.downloadImage(plotRef.current, {
          format: 'png',
          width: 1200,
          height: 800,
          filename: title || 'chart',
        });
      }
    });
  };

  return (
    <div className="relative border border-border rounded-lg p-4 bg-card" data-testid="chart-display">
      {title && (
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold" data-testid="text-chart-title">{title}</h3>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleExport}
            className="h-8 w-8"
            data-testid="button-export-chart"
          >
            <Download className="h-4 w-4" />
          </Button>
        </div>
      )}
      <div ref={plotRef} className="w-full" style={{ minHeight: '400px' }} data-testid="plot-container" />
    </div>
  );
}
