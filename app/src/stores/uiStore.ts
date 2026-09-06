import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ModelInfo, User } from '@/types';

export type Theme = 'light' | 'dark' | 'system';

interface UIState {
  theme: Theme;
  setTheme: (t: Theme) => void;

  sidebarOpen: boolean; // desktop collapse state
  mobileSidebarOpen: boolean; // mobile drawer state
  toggleSidebar: () => void;
  setMobileSidebarOpen: (v: boolean) => void;

  settingsOpen: boolean;
  settingsTab: string;
  openSettings: (tab?: string) => void;
  closeSettings: () => void;

  models: ModelInfo[];
  setModels: (m: ModelInfo[]) => void;
  selectedModel: string;
  setSelectedModel: (id: string) => void;

  modelsLoading: boolean;
  modelsError: string | null;
  setModelsLoading: (v: boolean) => void;
  setModelsError: (e: string | null) => void;

  user: User | null;
  setUser: (u: User) => void;

  webSearchEnabled: boolean;
  toggleWebSearch: () => void;
  imageGenEnabled: boolean;
  toggleImageGen: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      theme: 'system',
      setTheme: (theme) => set({ theme }),

      sidebarOpen: true,
      mobileSidebarOpen: false,
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setMobileSidebarOpen: (v) => set({ mobileSidebarOpen: v }),

      settingsOpen: false,
      settingsTab: 'general',
      openSettings: (tab) => set({ settingsOpen: true, settingsTab: tab ?? 'general' }),
      closeSettings: () => set({ settingsOpen: false }),

      models: [],
      setModels: (models) => {
        set({ models });
        if (!get().selectedModel && models[0]) set({ selectedModel: models[0].id });
      },
      selectedModel: '',
      setSelectedModel: (id) => set({ selectedModel: id }),

      modelsLoading: true,
      modelsError: null,
      setModelsLoading: (modelsLoading) => set({ modelsLoading }),
      setModelsError: (modelsError) => set({ modelsError }),

      user: null,
      setUser: (user) => set({ user }),

      webSearchEnabled: false,
      toggleWebSearch: () => set((s) => ({ webSearchEnabled: !s.webSearchEnabled, imageGenEnabled: false })),
      imageGenEnabled: false,
      toggleImageGen: () => set((s) => ({ imageGenEnabled: !s.imageGenEnabled, webSearchEnabled: false }))
    }),
    {
      name: 'chatui-settings',
      partialize: (s) => ({ theme: s.theme, sidebarOpen: s.sidebarOpen, selectedModel: s.selectedModel })
    }
  )
);
