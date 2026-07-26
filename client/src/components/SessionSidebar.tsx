import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { queryClient, apiRequest } from '@/lib/queryClient';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
} from '@/components/ui/sidebar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageSquarePlus, Trash2, MessageSquare, Crown, Upload, ArrowRight } from 'lucide-react';
import { useAuthStore } from '@/lib/store';
import { useToast } from '@/hooks/use-toast';
import type { Session } from '@shared/schema';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface SessionSidebarProps {
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onNewSession: () => void;
}

interface MessageLimitInfo {
  limit: number;
  current: number;
  remaining: number;
  isMaster: boolean;
}

export function SessionSidebar({ currentSessionId, onSessionSelect, onNewSession }: SessionSidebarProps) {
  const { token } = useAuthStore();
  const { toast } = useToast();
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);

  const { data: sessions = [], isLoading } = useQuery<Session[]>({
    queryKey: ['/api/sessions'],
    enabled: !!token,
  });

  const { data: messageLimit } = useQuery<MessageLimitInfo>({
    queryKey: ['/api/user/message-limit'],
    enabled: !!token,
  });

  const deleteMutation = useMutation({
    mutationFn: async (sessionId: string) => {
      await apiRequest('DELETE', `/api/sessions/${sessionId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/sessions'] });
      toast({ description: 'Session deleted successfully' });
      setSessionToDelete(null);
    },
    onError: () => {
      toast({ 
        description: 'Failed to delete session', 
        variant: 'destructive' 
      });
    },
  });

  const handleDeleteClick = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSessionToDelete(sessionId);
  };

  const handleConfirmDelete = () => {
    if (sessionToDelete) {
      deleteMutation.mutate(sessionToDelete);
    }
  };

  const formatDate = (date: Date | string | undefined | null) => {
    if (!date) return '';
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(dateObj.getTime())) return '';
    const now = new Date();
    const diffInMs = now.getTime() - dateObj.getTime();
    const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));

    if (diffInDays === 0) {
      return 'Today';
    } else if (diffInDays === 1) {
      return 'Yesterday';
    } else if (diffInDays < 7) {
      return `${diffInDays} days ago`;
    } else {
      return dateObj.toLocaleDateString();
    }
  };

  return (
    <>
      <Sidebar className="border-r border-border/60 z-10 shadow-sm">
        <SidebarHeader className="p-4">
          <Button
            onClick={onNewSession}
            className="w-full"
            size="default"
            data-testid="button-new-session"
          >
            <MessageSquarePlus className="h-4 w-4" />
            New Session
          </Button>
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel className="flex items-center justify-between">
              <span>Recent Sessions</span>
              {messageLimit && (
                <Badge 
                  variant={messageLimit.isMaster ? "default" : "secondary"}
                  className="text-xs"
                  data-testid="badge-message-limit"
                >
                  {messageLimit.isMaster ? (
                    <div className="flex items-center gap-1">
                      <Crown className="h-3 w-3" />
                      Unlimited
                    </div>
                  ) : (
                    `${messageLimit.remaining}/${messageLimit.limit}`
                  )}
                </Badge>
              )}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <ScrollArea className="h-[calc(100vh-200px)]">
                <SidebarMenu>
                  {isLoading ? (
                    <div className="p-4 text-center text-muted-foreground text-sm">
                      Loading sessions...
                    </div>
                  ) : sessions.length === 0 ? (
                    <div className="p-6 mx-2 mt-4 flex flex-col items-center justify-center text-center text-muted-foreground text-sm border border-dashed border-border/50 rounded-xl bg-card/30">
                      <div className="mb-3 p-2 bg-primary/10 rounded-full text-primary">
                        <Upload className="h-4 w-4" />
                      </div>
                      <p className="font-medium text-foreground">Upload a CSV</p>
                      <p className="text-xs mt-1">in the main area to get started</p>
                      <ArrowRight className="h-4 w-4 mt-3 opacity-50" />
                    </div>
                  ) : (
                    sessions.map((session) => (
                      <SidebarMenuItem key={session.id}>
                        <SidebarMenuButton
                          onClick={() => onSessionSelect(session.id)}
                          isActive={currentSessionId === session.id}
                          className="group"
                          data-testid={`session-item-${session.id}`}
                        >
                          <div className="flex items-center justify-between w-full gap-2">
                            <div className="flex items-center gap-2 flex-1 min-w-0">
                              <MessageSquare className="h-4 w-4 flex-shrink-0" />
                              <div className="flex-1 min-w-0">
                                <div className="font-medium truncate" data-testid={`session-name-${session.id}`}>
                                  {session.name || 'Untitled Session'}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  {formatDate(session.createdAt)}
                                </div>
                              </div>
                            </div>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 opacity-0 group-hover:opacity-100"
                              onClick={(e) => handleDeleteClick(session.id, e)}
                              data-testid={`button-delete-session-${session.id}`}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    ))
                  )}
                </SidebarMenu>
              </ScrollArea>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter className="p-4">
          {messageLimit && !messageLimit.isMaster && (
            <div className="text-xs text-muted-foreground text-center">
              {messageLimit.remaining > 0 ? (
                <>
                  {messageLimit.remaining} message{messageLimit.remaining !== 1 ? 's' : ''} remaining today
                </>
              ) : (
                <span className="text-destructive font-medium">
                  Daily limit reached. Resets at midnight.
                </span>
              )}
            </div>
          )}
        </SidebarFooter>
      </Sidebar>

      <AlertDialog open={!!sessionToDelete} onOpenChange={(open) => !open && setSessionToDelete(null)}>
        <AlertDialogContent data-testid="dialog-delete-session">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Session</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this session? This action cannot be undone.
              All messages in this session will be permanently deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="button-cancel-delete">Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleConfirmDelete}
              data-testid="button-confirm-delete"
              className="bg-destructive text-destructive-foreground hover-elevate"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
