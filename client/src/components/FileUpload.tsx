import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Upload, File, X, CheckCircle2 } from 'lucide-react';
import { formatFileSize } from '@/lib/utils';

interface FileUploadProps {
  onUpload: (file: File) => Promise<void>;
  acceptedFormats?: string[];
  maxSize?: number;
}

export function FileUpload({
  onUpload,
  acceptedFormats = ['.csv', '.xlsx', '.xls', '.json', '.parquet'],
  maxSize = 100 * 1024 * 1024, // 100MB
}: FileUploadProps) {
  const [uploadingFile, setUploadingFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    if (file.size > maxSize) {
      setError(`File size exceeds ${formatFileSize(maxSize)}`);
      return;
    }

    setUploadingFile(file);
    setError(null);
    setSuccess(false);
    setProgress(0);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 100);

      await onUpload(file);

      clearInterval(progressInterval);
      setProgress(100);
      setSuccess(true);
      
      setTimeout(() => {
        setUploadingFile(null);
        setProgress(0);
        setSuccess(false);
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setProgress(0);
    }
  }, [onUpload, maxSize]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/json': ['.json'],
      'application/octet-stream': ['.parquet'],
    },
    multiple: false,
    maxSize,
  });

  const handleCancel = () => {
    setUploadingFile(null);
    setProgress(0);
    setError(null);
    setSuccess(false);
  };

  return (
    <div className="space-y-4" data-testid="file-upload">
      <Card
        {...getRootProps()}
        className={`p-8 border-2 border-dashed cursor-pointer transition-colors hover-elevate ${
          isDragActive ? 'border-primary bg-primary/5' : 'border-border'
        }`}
      >
        <input {...getInputProps()} data-testid="input-file" />
        <div className="flex flex-col items-center justify-center gap-4 text-center">
          <div className={`p-4 rounded-full ${isDragActive ? 'bg-primary/10' : 'bg-muted'}`}>
            <Upload className={`h-8 w-8 ${isDragActive ? 'text-primary' : 'text-muted-foreground'}`} />
          </div>
          
          <div>
            <h3 className="text-lg font-semibold mb-1" data-testid="text-upload-title">
              {isDragActive ? 'Drop your file here' : 'Upload your dataset'}
            </h3>
            <p className="text-sm text-muted-foreground mb-2" data-testid="text-upload-subtitle">
              Drag and drop or click to browse
            </p>
            <div className="flex flex-wrap items-center justify-center gap-2" data-testid="container-accepted-formats">
              {acceptedFormats.map((format) => (
                <span key={format} className="text-xs px-2 py-1 bg-muted rounded font-mono" data-testid={`format-${format.replace('.', '')}`}>
                  {format}
                </span>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-2" data-testid="text-max-file-size">
              Maximum file size: {formatFileSize(maxSize)}
            </p>
          </div>
        </div>
      </Card>

      {/* Upload Progress */}
      {uploadingFile && (
        <Card className="p-4" data-testid="card-upload-progress">
          <div className="flex items-center gap-3">
            <File className="h-8 w-8 text-muted-foreground flex-shrink-0" data-testid="icon-file" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium truncate" data-testid="text-filename-uploading">{uploadingFile.name}</p>
                <span className="text-xs text-muted-foreground ml-2" data-testid="text-file-size">
                  {formatFileSize(uploadingFile.size)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {success ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-green-600" data-testid="icon-upload-success" />
                    <span className="text-xs text-green-600" data-testid="text-upload-complete">Upload complete!</span>
                  </>
                ) : (
                  <>
                    <Progress value={progress} className="flex-1" data-testid="progress-upload" />
                    <span className="text-xs text-muted-foreground" data-testid="text-upload-percentage">{progress}%</span>
                  </>
                )}
              </div>
            </div>
            {!success && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 flex-shrink-0"
                onClick={handleCancel}
                data-testid="button-cancel-upload"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </Card>
      )}

      {/* Error */}
      {error && (
        <Card className="p-4 bg-destructive/10 border-destructive/20" data-testid="card-upload-error">
          <p className="text-sm text-destructive" data-testid="text-error-message">{error}</p>
        </Card>
      )}
    </div>
  );
}
