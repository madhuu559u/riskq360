import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ChartState {
  activeChartId: string | null;
  activeTab: number;
  sidebarCollapsed: boolean;
  searchQuery: string;

  setActiveChart: (chartId: string | null) => void;
  setActiveTab: (tab: number) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setSearchQuery: (query: string) => void;
}

export const useChartStore = create<ChartState>()(
  persist(
    (set) => ({
      activeChartId: null,
      activeTab: 0,
      sidebarCollapsed: false,
      searchQuery: '',

      setActiveChart: (chartId) =>
        set({ activeChartId: chartId, activeTab: 0 }),

      setActiveTab: (tab) =>
        set({ activeTab: tab }),

      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

      setSidebarCollapsed: (collapsed) =>
        set({ sidebarCollapsed: collapsed }),

      setSearchQuery: (query) =>
        set({ searchQuery: query }),
    }),
    {
      name: 'medinsight5-chart',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    },
  ),
);
