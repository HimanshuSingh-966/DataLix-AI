import { useState } from 'react';
import type { ChatMessage } from '@shared/schema';
import { Button } from '@/components/ui/button';
import { Copy, RotateCw, Edit, Trash2, Check } from 'lucide-react';
import { formatTimestamp, copyToClipboard } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';

interface MessageBubbleProps {
  message: ChatMessage;
  onRegenerate?: () => void;
  onEdit?: (id: string, content: string) => void;
  onDelete?: (id: string) => void;
}

export function MessageBubble({ message, onRegenerate, onEdit, onDelete }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const { toast } = useToast();
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    try {
      await copyToClipboard(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast({ description: 'Copied to clipboard' });
    } catch (error) {
      toast({ description: 'Failed to copy', variant: 'destructive' });
    }
  };

  return (
    <div
      className={`flex items-start gap-3 group ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
      data-testid={`message-${message.role}`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold tracking-wide ${
            isUser
              ? 'bg-[#1C1C1E] text-white'
              : 'bg-primary/20 text-primary border border-primary/30 shadow-[0_0_10px_rgba(59,130,246,0.2)]'
        }`}
        data-testid={`avatar-${message.role}`}
      >
        {isUser ? 'U' : 'AI'}
      </div>

      <div className={`flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'} flex-1 max-w-3xl`}>
        {/* Message Content */}
        <div
          className={`rounded-[20px] px-5 py-3.5 shadow-sm ${
            message.error
              ? 'bg-destructive/10 border border-destructive/20 text-destructive'
              : isUser
              ? 'bg-[#1C1C1E] text-white'
              : 'bg-gradient-to-br from-[#121212] to-[#0A0A0A] border border-[#1C1C1E] text-white'
          }`}
          data-testid="message-content"
        >
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap" data-testid="text-message-user">{message.content}</p>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none text-card-foreground" data-testid="text-message-assistant">
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Function calls indicator */}
        {message.functionCalls && message.functionCalls.length > 0 && (
          <div className="flex flex-wrap gap-1 px-2">
            {message.functionCalls.map((fn, idx) => (
              <span
                key={idx}
                className="text-xs px-2 py-0.5 rounded-full bg-accent text-accent-foreground font-mono"
                data-testid={`function-call-${fn}`}
              >
                {fn}
              </span>
            ))}
          </div>
        )}

        {/* Timestamp and Actions */}
        <div className={`flex items-center gap-2 px-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          <span className="text-xs text-muted-foreground" data-testid="text-timestamp">{formatTimestamp(message.timestamp)}</span>

          <div
            className={`flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ${
              isUser ? 'flex-row-reverse' : 'flex-row'
            }`}
          >
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={handleCopy}
              data-testid="button-copy-message"
            >
              {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            </Button>

            {!isUser && onRegenerate && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={onRegenerate}
                data-testid="button-regenerate-message"
              >
                <RotateCw className="h-3 w-3" />
              </Button>
            )}

            {onEdit && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => onEdit(message.id, message.content)}
                data-testid="button-edit-message"
              >
                <Edit className="h-3 w-3" />
              </Button>
            )}

            {onDelete && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => onDelete(message.id)}
                data-testid="button-delete-message"
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
