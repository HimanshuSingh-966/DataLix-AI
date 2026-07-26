import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Card } from '@/components/ui/card';
import { useChatStore } from '@/lib/store';
import { Moon } from 'lucide-react';

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const { aiProvider, setAiProvider } = useChatStore();
  const [autoScroll, setAutoScroll] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [compactMode, setCompactMode] = useState(false);

  useEffect(() => {
    const savedAutoScroll = localStorage.getItem('autoScroll') !== 'false';
    setAutoScroll(savedAutoScroll);

    const savedSound = localStorage.getItem('soundEnabled') === 'true';
    setSoundEnabled(savedSound);

    const savedCompact = localStorage.getItem('compactMode') === 'true';
    setCompactMode(savedCompact);
  }, [open]);

  const handleAutoScrollChange = (checked: boolean) => {
    setAutoScroll(checked);
    localStorage.setItem('autoScroll', String(checked));
  };

  const handleSoundChange = (checked: boolean) => {
    setSoundEnabled(checked);
    localStorage.setItem('soundEnabled', String(checked));
  };

  const handleCompactModeChange = (checked: boolean) => {
    setCompactMode(checked);
    localStorage.setItem('compactMode', String(checked));
  };

  const handleProviderChange = (provider: string) => {
    setAiProvider(provider as 'auto' | 'gemini' | 'groq');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl" data-testid="dialog-settings">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>
            Customize your DataLix AI experience
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div className="space-y-4">
        <div>
          <h3 className="text-sm font-medium mb-3">Appearance</h3>
          <Card className="p-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Theme</Label>
                  <p className="text-sm text-muted-foreground">
                    Dark mode (default)
                  </p>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Moon className="h-4 w-4" />
                  <span className="text-sm">Dark</span>
                </div>
              </div>

              <Separator />

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="compact-mode">Compact Mode</Label>
                      <p className="text-sm text-muted-foreground">
                        Reduce spacing for more content
                      </p>
                    </div>
                    <Switch
                      id="compact-mode"
                      checked={compactMode}
                      onCheckedChange={handleCompactModeChange}
                      data-testid="switch-compact-mode"
                    />
                  </div>
                </div>
              </Card>
            </div>

            <div>
              <h3 className="text-sm font-medium mb-3">AI Provider</h3>
              <Card className="p-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="provider-select">AI Model</Label>
                    <p className="text-sm text-muted-foreground">
                      Choose your preferred AI provider
                    </p>
                  </div>
                  <Select value={aiProvider} onValueChange={handleProviderChange}>
                    <SelectTrigger className="w-[140px]" id="provider-select" data-testid="select-ai-provider">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto" data-testid="provider-auto">Auto</SelectItem>
                      <SelectItem value="gemini" data-testid="provider-gemini">Gemini</SelectItem>
                      <SelectItem value="groq" data-testid="provider-groq">Groq</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </Card>
            </div>

            <div>
              <h3 className="text-sm font-medium mb-3">Behavior</h3>
              <Card className="p-4">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="auto-scroll">Auto-scroll</Label>
                      <p className="text-sm text-muted-foreground">
                        Automatically scroll to new messages
                      </p>
                    </div>
                    <Switch
                      id="auto-scroll"
                      checked={autoScroll}
                      onCheckedChange={handleAutoScrollChange}
                      data-testid="switch-auto-scroll"
                    />
                  </div>

                  <Separator />

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="sound">Sound Effects</Label>
                      <p className="text-sm text-muted-foreground">
                        Play sounds for notifications
                      </p>
                    </div>
                    <Switch
                      id="sound"
                      checked={soundEnabled}
                      onCheckedChange={handleSoundChange}
                      data-testid="switch-sound"
                    />
                  </div>
                </div>
              </Card>
            </div>
          </div>

          <div className="pt-4">
            <div className="p-4 bg-muted/50 rounded-lg">
              <p className="text-xs text-muted-foreground">
                💡 Your preferences are saved locally and will persist across sessions.
              </p>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
