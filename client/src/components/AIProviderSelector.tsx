import { useEffect, useState } from 'react';
import { getAccessToken } from '@/lib/supabase';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { Bot, Sparkles, Zap, Check } from 'lucide-react';
import { useChatStore } from '@/lib/store';

interface AIProviderSelectorProps {
  className?: string;
}

export function AIProviderSelector({ className }: AIProviderSelectorProps) {
  const { aiProvider, setAiProvider } = useChatStore();
  const [availableProviders, setAvailableProviders] = useState<{
    gemini: boolean;
    groq: boolean;
  }>({ gemini: false, groq: false });

  useEffect(() => {
    getAccessToken().then(token => fetch('/api/ai-providers', {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    }))
      .then(res => res.json())
      .then(data => {
        setAvailableProviders(data.providers);
      })
      .catch(() => {});
  }, []);

  const providerInfo = {
    auto: {
      icon: Bot,
      label: 'Auto',
      description: 'Best available',
      badge: 'default' as const,
    },
    groq: {
      icon: Zap,
      label: 'Groq',
      description: 'Ultra-fast inference',
      badge: 'default' as const,
    },
    gemini: {
      icon: Sparkles,
      label: 'Gemini',
      description: 'Advanced reasoning',
      badge: 'secondary' as const,
    },
  };

  const currentInfo = providerInfo[aiProvider];
  const Icon = currentInfo.icon;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={className}
          data-testid="button-ai-provider"
        >
          <Icon className="h-4 w-4 mr-2" />
          <span className="hidden sm:inline">{currentInfo.label}</span>
          <Badge variant={currentInfo.badge} className="ml-2 text-xs">
            AI
          </Badge>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56" data-testid="menu-ai-provider">
        <DropdownMenuLabel>AI Provider</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuRadioGroup value={aiProvider} onValueChange={(value) => setAiProvider(value as 'auto' | 'groq' | 'gemini')}>
          <DropdownMenuRadioItem value="auto" data-testid="option-ai-auto">
            <div className="flex items-center gap-2 w-full">
              <Bot className="h-4 w-4" />
              <div className="flex-1">
                <div className="font-medium">Auto</div>
                <div className="text-xs text-muted-foreground">Best available</div>
              </div>
              {aiProvider === 'auto' && <Check className="h-4 w-4" />}
            </div>
          </DropdownMenuRadioItem>
          
          <DropdownMenuRadioItem 
            value="groq" 
            disabled={!availableProviders.groq}
            data-testid="option-ai-groq"
          >
            <div className="flex items-center gap-2 w-full">
              <Zap className="h-4 w-4" />
              <div className="flex-1">
                <div className="font-medium flex items-center gap-2">
                  Groq
                  {availableProviders.groq && (
                    <Badge variant="default" className="text-xs">Fast</Badge>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  {availableProviders.groq ? 'Ultra-fast inference' : 'Not configured'}
                </div>
              </div>
              {aiProvider === 'groq' && <Check className="h-4 w-4" />}
            </div>
          </DropdownMenuRadioItem>
          
          <DropdownMenuRadioItem 
            value="gemini" 
            disabled={!availableProviders.gemini}
            data-testid="option-ai-gemini"
          >
            <div className="flex items-center gap-2 w-full">
              <Sparkles className="h-4 w-4" />
              <div className="flex-1">
                <div className="font-medium flex items-center gap-2">
                  Gemini
                  {availableProviders.gemini && (
                    <Badge variant="secondary" className="text-xs">Smart</Badge>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  {availableProviders.gemini ? 'Advanced reasoning' : 'Not configured'}
                </div>
              </div>
              {aiProvider === 'gemini' && <Check className="h-4 w-4" />}
            </div>
          </DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
