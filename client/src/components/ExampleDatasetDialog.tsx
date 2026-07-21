import { getAccessToken } from '@/lib/supabase';
import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, Database, FileText, Users, TrendingUp } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface ExampleDataset {
  id: string;
  name: string;
  description: string;
  rows: number;
  columns: number;
}

interface ExampleDatasetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDatasetLoaded: (data: any) => void;
}

const DATASET_ICONS = {
  sales: Database,
  customers: Users,
  employees: FileText,
} as const;

export function ExampleDatasetDialog({ open, onOpenChange, onDatasetLoaded }: ExampleDatasetDialogProps) {
  const [datasets, setDatasets] = useState<ExampleDataset[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingDataset, setLoadingDataset] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    if (open) {
      fetchDatasets();
    }
  }, [open]);

  const fetchDatasets = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/example-datasets', {
        headers: {
          'Authorization': `Bearer ${await getAccessToken()}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch example datasets');
      }

      const data = await response.json();
      setDatasets(data.datasets || []);
    } catch (error) {
      toast({
        description: error instanceof Error ? error.message : 'Failed to load example datasets',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const loadDataset = async (datasetId: string) => {
    try {
      setLoadingDataset(datasetId);

      const response = await fetch(`/api/load-example-dataset?dataset_id=${datasetId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await getAccessToken()}`
        }
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to load dataset');
      }

      const data = await response.json();
      onDatasetLoaded(data);
      onOpenChange(false);
      
      toast({
        description: `Loaded ${data.exampleDatasetName || 'example dataset'} successfully!`
      });
    } catch (error) {
      toast({
        description: error instanceof Error ? error.message : 'Failed to load dataset',
        variant: 'destructive'
      });
    } finally {
      setLoadingDataset(null);
    }
  };

  const getIcon = (datasetId: string) => {
    const Icon = DATASET_ICONS[datasetId as keyof typeof DATASET_ICONS] || TrendingUp;
    return Icon;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl" data-testid="dialog-example-datasets">
        <DialogHeader>
          <DialogTitle>Example Datasets</DialogTitle>
          <DialogDescription>
            Choose a sample dataset to explore DataLix AI features
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="grid gap-4 py-4">
            {datasets.map((dataset) => {
              const Icon = getIcon(dataset.id);
              const isLoading = loadingDataset === dataset.id;
              
              return (
                <Card
                  key={dataset.id}
                  className="p-4 hover-elevate cursor-pointer transition-all"
                  onClick={() => !isLoading && loadDataset(dataset.id)}
                  data-testid={`card-example-${dataset.id}`}
                >
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-lg bg-primary/10">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold mb-1" data-testid={`text-dataset-name-${dataset.id}`}>
                        {dataset.name}
                      </h3>
                      <p className="text-sm text-muted-foreground mb-2">
                        {dataset.description}
                      </p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span data-testid={`text-rows-${dataset.id}`}>
                          {dataset.rows.toLocaleString()} rows
                        </span>
                        <span>•</span>
                        <span data-testid={`text-columns-${dataset.id}`}>
                          {dataset.columns} columns
                        </span>
                      </div>
                    </div>

                    <Button
                      size="sm"
                      disabled={isLoading}
                      onClick={(e) => {
                        e.stopPropagation();
                        loadDataset(dataset.id);
                      }}
                      data-testid={`button-load-${dataset.id}`}
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Loading...
                        </>
                      ) : (
                        'Load Dataset'
                      )}
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        <div className="mt-4 p-4 bg-muted/50 rounded-lg">
          <p className="text-xs text-muted-foreground">
            💡 Example datasets are generated with realistic data patterns including outliers, missing values, and duplicates to help you explore data quality and cleaning features.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}