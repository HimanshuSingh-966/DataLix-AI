import { useState, useMemo } from 'react';
import type { DataPreview as DataPreviewType } from '@shared/schema';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ChevronDown, ChevronUp, ArrowUpDown } from 'lucide-react';
import { formatNumber } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

interface DataPreviewProps {
  data: DataPreviewType;
  maxRows?: number;
}

export function DataPreview({ data, maxRows = 5 }: DataPreviewProps) {
  const [expanded, setExpanded] = useState(false);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const sortedRows = useMemo(() => {
    if (!sortColumn) return data.rows;

    return [...data.rows].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      if (aVal === null || aVal === undefined || aVal === '') return 1;
      if (bVal === null || bVal === undefined || bVal === '') return -1;

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      const aStr = String(aVal).toLowerCase();
      const bStr = String(bVal).toLowerCase();
      
      if (sortDirection === 'asc') {
        return aStr < bStr ? -1 : aStr > bStr ? 1 : 0;
      } else {
        return aStr > bStr ? -1 : aStr < bStr ? 1 : 0;
      }
    });
  }, [data.rows, sortColumn, sortDirection]);

  const displayRows = expanded ? sortedRows : sortedRows.slice(0, maxRows);
  const hasMore = data.rows.length > maxRows;

  const getTypeColor = (type: string) => {
    if (type.includes('int') || type.includes('float')) return 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400';
    if (type.includes('object') || type.includes('string')) return 'bg-purple-100 text-purple-700 dark:bg-purple-900/20 dark:text-purple-400';
    if (type.includes('bool')) return 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400';
    if (type.includes('date')) return 'bg-orange-100 text-orange-700 dark:bg-orange-900/20 dark:text-orange-400';
    return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
  };

  return (
    <div className="space-y-2" data-testid="data-preview">
      {/* Header with stats */}
      <div className="flex items-center justify-between px-3 py-2 bg-muted/50 rounded-lg text-sm" data-testid="preview-stats">
        <div className="flex items-center gap-4">
          <span className="text-muted-foreground" data-testid="text-row-column-count">
            <span className="font-semibold text-foreground">{formatNumber(data.totalRows, 0)}</span> rows ×{' '}
            <span className="font-semibold text-foreground">{data.totalColumns}</span> columns
          </span>
          {data.fileName && (
            <span className="text-muted-foreground" data-testid="text-filename">
              File: <span className="font-medium text-foreground">{data.fileName}</span>
            </span>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="border border-border rounded-lg overflow-hidden" data-testid="table-container">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/30">
                {data.columns.map((col) => (
                  <TableHead
                    key={col.name}
                    className="font-semibold cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => handleSort(col.name)}
                    data-testid={`column-header-${col.name}`}
                  >
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span>{col.name}</span>
                        {sortColumn === col.name ? (
                          sortDirection === 'asc' ? (
                            <ChevronUp className="h-3 w-3" data-testid="icon-sort-asc" />
                          ) : (
                            <ChevronDown className="h-3 w-3" data-testid="icon-sort-desc" />
                          )
                        ) : (
                          <ArrowUpDown className="h-3 w-3 opacity-30" data-testid="icon-sort-none" />
                        )}
                      </div>
                      <Badge variant="secondary" className={`text-xs font-normal w-fit ${getTypeColor(col.type)}`} data-testid={`badge-type-${col.name}`}>
                        {col.type}
                      </Badge>
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayRows.map((row, idx) => (
                <TableRow key={idx} className="hover:bg-muted/30" data-testid={`table-row-${idx}`}>
                  {data.columns.map((col) => {
                    const value = row[col.name];
                    const isNull = value === null || value === undefined || value === '';
                    
                    return (
                      <TableCell
                        key={col.name}
                        className={`font-mono text-sm ${
                          isNull ? 'text-destructive bg-destructive/5' : ''
                        } ${
                          typeof value === 'number' ? 'text-right' : 'text-left'
                        }`}
                        data-testid={`cell-${idx}-${col.name}`}
                      >
                        {isNull ? (
                          <span className="italic font-sans" data-testid="text-null-value">null</span>
                        ) : typeof value === 'number' ? (
                          formatNumber(value, 2)
                        ) : (
                          String(value)
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Expand/Collapse button */}
      {hasMore && (
        <div className="flex justify-center pt-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
            data-testid="button-toggle-preview"
          >
            {expanded ? (
              <>
                <ChevronUp className="h-4 w-4 mr-2" />
                Show less
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4 mr-2" />
                Show all {data.totalRows} rows
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
