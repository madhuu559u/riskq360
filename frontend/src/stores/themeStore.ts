import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { applyTheme, type FontFamily } from '../themes';

export type ThemeName =
  | 'electric-blue'
  | 'deep-ocean'
  | 'forest-health'
  | 'midnight-ai'
  | 'sunrise-warm'
  | 'royal-medical';

interface ThemeState {
  theme: ThemeName;
  isDarkMode: boolean;
  fontFamily: FontFamily;
  setTheme: (theme: ThemeName) => void;
  toggleDarkMode: () => void;
  setDarkMode: (isDark: boolean) => void;
  setFontFamily: (font: FontFamily) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: 'electric-blue',
      isDarkMode: false,
      fontFamily: 'inter' as FontFamily,

      setTheme: (theme) => {
        set({ theme });
        applyTheme(theme, get().isDarkMode, get().fontFamily);
      },

      toggleDarkMode: () => {
        const newDark = !get().isDarkMode;
        set({ isDarkMode: newDark });
        applyTheme(get().theme, newDark, get().fontFamily);
      },

      setDarkMode: (isDark) => {
        set({ isDarkMode: isDark });
        applyTheme(get().theme, isDark, get().fontFamily);
      },

      setFontFamily: (font) => {
        set({ fontFamily: font });
        applyTheme(get().theme, get().isDarkMode, font);
      },
    }),
    {
      name: 'medinsight5-theme',
      onRehydrateStorage: () => (state) => {
        if (state) {
          // Guard against removed font values from older localStorage
          const validFonts = ['inter', 'dm-sans', 'space-grotesk'] as const;
          if (!validFonts.includes(state.fontFamily as typeof validFonts[number])) {
            state.fontFamily = 'inter';
          }
          applyTheme(state.theme, state.isDarkMode, state.fontFamily);
        }
      },
    },
  ),
);
