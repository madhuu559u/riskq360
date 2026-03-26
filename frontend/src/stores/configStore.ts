import { create } from 'zustand';

interface ConfigState {
  spotlightOpen: boolean;
  setSpotlightOpen: (open: boolean) => void;
  toggleSpotlight: () => void;
}

export const useConfigStore = create<ConfigState>()((set) => ({
  spotlightOpen: false,

  setSpotlightOpen: (open) =>
    set({ spotlightOpen: open }),

  toggleSpotlight: () =>
    set((state) => ({ spotlightOpen: !state.spotlightOpen })),
}));
