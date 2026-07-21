import { useEffect, useRef, useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useLocation } from 'wouter';
import { queryClient, apiRequest, ApiError } from '@/lib/queryClient';
import { getAccessToken } from '@/lib/supabase';
import { Header } from '@/components/Header';
import { SessionSidebar } from '@/components/SessionSidebar';
import { MessageBubble } from '@/components/MessageBubble';
import { DataPreview } from '@/components/DataPreview';
import { ChartDisplay } from '@/components/ChartDisplay';
import { QualityScore } from '@/components/QualityScore';
import { SuggestedActions } from '@/components/SuggestedActions';
import { FileUpload } from '@/components/FileUpload';
import { TypingIndicator } from '@/components/LoadingStates';
import { EmptyState } from '@/components/EmptyStates';
import { ExampleDatasetDialog } from '@/components/ExampleDatasetDialog';
import { SettingsDialog } from '@/components/SettingsDialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { useChatStore } from '@/lib/store';
import { generateId } from '@/lib/utils';
import { ArrowUp, Paperclip } from 'lucide-react';
import { AIProviderSelector } from '@/components/AIProviderSelector';
import { useToast } from '@/hooks/use-toast';
import type { ChatMessage, Session, Message } from '@shared/schema';

export default function ChatPage() {
  const {
    sessionId,
    messages,
    currentDataset,
    qualityScore,
    isLoading,
    aiProvider,
    addMessage,
    setCurrentDataset,
    setQualityScore,
    setIsLoading,
    clearSession,
  } = useChatStore();

  const [, setLocation] = useLocation();
  const [input, setInput] = useState('');
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showExampleDialog, setShowExampleDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { toast } = useToast();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 128)}px`;
    }
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    if (!sessionId) {
      toast({ description: 'Please upload a dataset first', variant: 'destructive' });
      return;
    }

    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    const messageContent = input;
    const isFirstMessage = messages.length === 0;
    
    addMessage(userMessage);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await getAccessToken()}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: messageContent,
          provider: aiProvider
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Failed to process message' }));
        if (response.status === 429) {
          toast({ 
            description: errorData.error || 'Daily message limit reached (10/10). Limit resets at midnight.',
            variant: 'destructive' 
          });
        }
        throw new Error(errorData.error || 'Failed to process message');
      }

      const data = await response.json();

      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: data.message,
        timestamp: new Date(),
        functionCalls: data.function_calls,
        chartData: data.chart_data,
        dataPreview: data.data_preview,
        suggestedActions: data.suggested_actions,
      };

      addMessage(assistantMessage);

      if (data.data_preview) {
        setCurrentDataset(data.data_preview);
      }

      if (isFirstMessage) {
        const sessionName = messageContent.substring(0, 50);
        await apiRequest('PATCH', `/api/sessions/${sessionId}/name`, { name: sessionName });
        queryClient.invalidateQueries({ queryKey: ['/api/sessions'] });
      }
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: error instanceof Error ? error.message : 'An error occurred',
        timestamp: new Date(),
        error: true,
      };
      addMessage(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    if (e.key === 'k' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      setInput('');
    }
  };

  const handleUpload = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await getAccessToken()}`
        },
        body: formData
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Upload failed');
      }

      const data = await response.json();

      // Store session ID
      useChatStore.setState({ sessionId: data.sessionId });

      // Set data preview and quality score for header
      setCurrentDataset(data.preview);
      setQualityScore(data.quality);

      const message: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: `✓ Dataset uploaded successfully!\n\nQuality Score: **${Math.round(data.quality.overallScore)}/100**\n\nI've analyzed your dataset. ${data.issues.length > 0 ? `Found ${data.issues.length} potential issues.` : 'Your data looks good!'} Ask me anything about your data!`,
        timestamp: new Date(),
        dataPreview: data.preview,
        qualityScore: data.quality,
        suggestedActions: [
          { label: 'Show Statistics', prompt: 'Show statistical summary' },
          { label: 'Correlation Matrix', prompt: 'Show correlation matrix' },
          { label: 'Create Visualization', prompt: 'Create a scatter plot of the first two numeric columns' },
          ...(data.issues.length > 0 ? [{ label: 'Clean Data', prompt: 'Help me clean this dataset' }] : [])
        ],
      };

      addMessage(message);
      setShowUploadDialog(false);
      toast({ description: 'Dataset uploaded and analyzed!' });
    } catch (error) {
      toast({ 
        description: error instanceof Error ? error.message : 'Upload failed', 
        variant: 'destructive' 
      });
    }
  };

  const handleSuggestedAction = (prompt: string) => {
    setInput(prompt);
    textareaRef.current?.focus();
  };

  const handleNewSession = async () => {
    toast({ description: 'Coming soon!' });
  };

  const handleSessionSelect = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/sessions/${sessionId}/messages`, {
        headers: {
          'Authorization': `Bearer ${await getAccessToken()}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load session');
      }

      const sessionMessages = await response.json() as Message[];
      
      const chatMessages: ChatMessage[] = sessionMessages.map(msg => ({
        id: msg.id,
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: new Date(msg.createdAt),
        chartData: msg.chartData as any || undefined,
        dataPreview: msg.dataPreview as any || undefined,
        suggestedActions: msg.suggestedActions as any || undefined,
        functionCalls: msg.functionCalls as any || undefined,
        error: !!msg.error,
      }));

      clearSession();
      useChatStore.setState({ 
        sessionId: sessionId
      });
      useChatStore.getState().setMessages(chatMessages);
      
      if (sessionMessages.length > 0 && sessionMessages[0].dataPreview) {
        setCurrentDataset(sessionMessages[0].dataPreview as any);
      }
    } catch (error) {
      toast({ 
        description: 'Failed to load session', 
        variant: 'destructive' 
      });
    }
  };

  const handleExampleDataset = () => {
    setShowExampleDialog(true);
  };

  const handleExampleDatasetLoaded = (data: any) => {
    useChatStore.setState({ sessionId: data.sessionId });
    setCurrentDataset(data.preview);
    setQualityScore(data.quality);
    
    const issues = data.issues ?? [];

    const message: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content: `✓ Loaded example dataset: **${data.exampleDatasetName}**\n\nQuality Score: **${Math.round(data.quality.overallScore)}/100**\n\nI've loaded a sample dataset for you to explore. ${issues.length > 0 ? `Found ${issues.length} potential issues.` : 'The data looks good!'} Try asking me about the data!`,
      timestamp: new Date(),
      dataPreview: data.preview,
      qualityScore: data.quality,
      suggestedActions: [
        { label: 'Show Statistics', prompt: 'Show statistical summary' },
        { label: 'Correlation Matrix', prompt: 'Show correlation matrix' },
        { label: 'Create Visualization', prompt: 'Create a scatter plot' },
        ...(issues.length > 0 ? [{ label: 'Clean Data', prompt: 'Help me clean this dataset' }] : [])
      ],
    };

    addMessage(message);
  };

  const handleSessionHistory = () => {
    toast({ 
      description: 'Session history feature coming soon!',
      variant: 'default'
    });
  };

  const handleSettings = () => {
    setShowSettingsDialog(true);
  };

  const chatInputNode = (
    <div className="w-full">
      <div className="relative">
        <div className="flex items-end gap-3">
          <div className="flex-1 relative bg-card border border-border rounded-2xl p-3 shadow-sm transition-all focus-within:ring-1 focus-within:ring-primary/30">
            <div className="flex items-center gap-2 mb-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowUploadDialog(true)}
                data-testid="button-attach-file"
                className="h-7 px-2"
              >
                <Paperclip className="h-3.5 w-3.5" />
              </Button>
              <AIProviderSelector className="h-7" />
            </div>
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Ask me anything about your data..."
              className="resize-none min-h-[44px] max-h-32 border-0 bg-transparent p-0 focus-visible:ring-0 focus-visible:ring-offset-0"
              rows={1}
              disabled={isLoading}
              data-testid="input-chat-message"
            />
          </div>

          <Button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            size="icon"
            className="h-12 w-12 rounded-full shrink-0 bg-primary text-primary-foreground hover:bg-primary/90"
            data-testid="button-send-message"
          >
            <ArrowUp className="h-5 w-5" />
          </Button>
        </div>
      </div>

      <div className="mt-4">
        <p className="text-xs text-muted-foreground mb-3 text-center">Try asking:</p>
        <div className="flex flex-wrap gap-2 justify-center max-w-xl mx-auto" data-testid="container-examples">
          <button
            className="text-sm text-foreground/70 px-3 py-1.5 rounded-full border border-border/50 hover:bg-muted transition-colors"
            onClick={() => handleSuggestedAction('Show me the data quality score')}
            data-testid="example-quality"
          >
            Show me the data quality score
          </button>
          <button
            className="text-sm text-foreground/70 px-3 py-1.5 rounded-full border border-border/50 hover:bg-muted transition-colors"
            onClick={() => handleSuggestedAction('Remove outliers')}
            data-testid="example-outliers"
          >
            Remove outliers
          </button>
          <button
            className="text-sm text-foreground/70 px-3 py-1.5 rounded-full border border-border/50 hover:bg-muted transition-colors"
            onClick={() => handleSuggestedAction('Create a correlation heatmap')}
            data-testid="example-heatmap"
          >
            Create a correlation heatmap
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen w-full bg-background">
      <SessionSidebar
        currentSessionId={sessionId}
        onSessionSelect={handleSessionSelect}
        onNewSession={handleNewSession}
      />
      
      <div className="flex flex-col flex-1 h-screen">
        <header className="flex items-center gap-2 p-2 border-b">
          <SidebarTrigger data-testid="button-sidebar-toggle" />
          <div className="flex-1">
            <Header
              onUploadClick={() => setShowUploadDialog(true)}
              onNewSession={handleNewSession}
              onSessionHistory={handleSessionHistory}
              onSettings={handleSettings}
              datasetLoaded={!!currentDataset}
              qualityScore={qualityScore?.overallScore}
            />
          </div>
        </header>

      <div className="flex-1 overflow-y-auto flex justify-center">
        <div className="w-full max-w-2xl px-4 py-6">
          {messages.length === 0 ? (
            <EmptyState 
              type="no-messages" 
              onAction={() => setShowUploadDialog(true)} 
              onExampleDataset={handleExampleDataset}
            >
              {chatInputNode}
            </EmptyState>
          ) : (
            <div className="space-y-6">
              {messages.map((message) => (
                <div key={message.id} className="space-y-4">
                  <MessageBubble
                    message={message}
                    onRegenerate={() => {
                      toast({ description: 'Regenerate feature coming soon!' });
                    }}
                  />

                  {message.qualityScore && (
                    <div className="ml-11">
                      <QualityScore quality={message.qualityScore} />
                    </div>
                  )}

                  {message.dataPreview && (
                    <div className="ml-11">
                      <DataPreview data={message.dataPreview} />
                    </div>
                  )}

                  {message.chartData && (
                    <div className="ml-11">
                      <ChartDisplay chartData={message.chartData} />
                    </div>
                  )}

                  {message.suggestedActions && message.suggestedActions.length > 0 && (
                    <div className="ml-11">
                      <SuggestedActions
                        actions={message.suggestedActions}
                        onSelect={handleSuggestedAction}
                      />
                    </div>
                  )}
                </div>
              ))}

              {isLoading && (
                <TypingIndicator />
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {messages.length > 0 && (
        <div className="border-t border-border bg-background flex justify-center">
          <div className="w-full max-w-3xl px-4 py-6">
            {chatInputNode}
          </div>
        </div>
      )}

      <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Upload Dataset</DialogTitle>
          </DialogHeader>
          <FileUpload onUpload={handleUpload} />
        </DialogContent>
      </Dialog>

      <ExampleDatasetDialog
        open={showExampleDialog}
        onOpenChange={setShowExampleDialog}
        onDatasetLoaded={handleExampleDatasetLoaded}
      />

      <SettingsDialog
        open={showSettingsDialog}
        onOpenChange={setShowSettingsDialog}
      />
      </div>
    </div>
  );
}