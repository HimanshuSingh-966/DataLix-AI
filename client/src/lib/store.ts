import { create } from 'zustand';
import type { ChatMessage, DataPreview, DataQuality } from '@shared/schema';

interface ChatStore {
  sessionId: string | null;
  messages: ChatMessage[];
  currentDataset: DataPreview | null;
  qualityScore: DataQuality | null;
  isLoading: boolean;
  aiProvider: 'auto' | 'groq' | 'gemini';
  
  setSessionId: (id: string) => void;
  setMessages: (messages: ChatMessage[]) => void;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  deleteMessage: (id: string) => void;
  setCurrentDataset: (dataset: DataPreview | null) => void;
  setQualityScore: (score: DataQuality | null) => void;
  setIsLoading: (loading: boolean) => void;
  setAiProvider: (provider: 'auto' | 'groq' | 'gemini') => void;
  clearSession: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  sessionId: null,
  messages: [],
  currentDataset: null,
  qualityScore: null,
  isLoading: false,
  aiProvider: 'auto',
  
  setSessionId: (id) => set({ sessionId: id }),
  
  setMessages: (messages) => set({ messages }),
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  
  updateMessage: (id, updates) => set((state) => ({
    messages: state.messages.map(msg => 
      msg.id === id ? { ...msg, ...updates } : msg
    )
  })),
  
  deleteMessage: (id) => set((state) => ({
    messages: state.messages.filter(msg => msg.id !== id)
  })),
  
  setCurrentDataset: (dataset) => set({ currentDataset: dataset }),
  
  setQualityScore: (score) => set({ qualityScore: score }),
  
  setIsLoading: (loading) => set({ isLoading: loading }),
  
  setAiProvider: (provider) => set({ aiProvider: provider }),
  
  clearSession: () => set({
    messages: [],
    currentDataset: null,
    qualityScore: null,
    isLoading: false,
  }),
}));

interface AuthStore {
  user: { id: string; username: string; email: string } | null;
  token: string | null;
  isAuthenticated: boolean;
  
  setUser: (user: { id: string; username: string; email: string } | null) => void;
  setToken: (token: string | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  
  setToken: (token) => set({ token }),
  
  logout: () => set({ user: null, token: null, isAuthenticated: false }),
}));
