import type { ThemeName } from '../stores/themeStore';

export interface ThemeColors {
  primary: string;
  primaryHover: string;
  secondary: string;
  accent: string;
  background: string;
  surface: string;
  surfaceHover: string;
  border: string;
  text: string;
  textSecondary: string;
  textMuted: string;
  success: string;
  warning: string;
  error: string;
  info: string;
}

export interface ThemeDefinition {
  name: ThemeName;
  label: string;
  description: string;
  light: ThemeColors;
  dark: ThemeColors;
}

const electricBlue: ThemeDefinition = {
  name: 'electric-blue',
  label: 'Electric Blue',
  description: 'Modern electric blue, clean professional',
  light: {
    primary: '#0176D3',
    primaryHover: '#014486',
    secondary: '#747474',
    accent: '#1B96FF',
    background: '#F3F3F3',
    surface: '#FFFFFF',
    surfaceHover: '#F5F5F5',
    border: '#DDDBDA',
    text: '#181818',
    textSecondary: '#444444',
    textMuted: '#706E6B',
    success: '#2E844A',
    warning: '#DD7A01',
    error: '#EA001E',
    info: '#0176D3',
  },
  dark: {
    primary: '#1B96FF',
    primaryHover: '#0D75CB',
    secondary: '#B0ADAB',
    accent: '#0176D3',
    background: '#16181D',
    surface: '#1E2228',
    surfaceHover: '#272B33',
    border: '#3E3E3C',
    text: '#F3F3F3',
    textSecondary: '#C9C7C5',
    textMuted: '#939393',
    success: '#45C65A',
    warning: '#FE9339',
    error: '#FE5C4C',
    info: '#1B96FF',
  },
};

const deepOcean: ThemeDefinition = {
  name: 'deep-ocean',
  label: 'Deep Ocean',
  description: 'Dark navy/teal, calm professional',
  light: {
    primary: '#0D9488',
    primaryHover: '#0F766E',
    secondary: '#64748B',
    accent: '#14B8A6',
    background: '#F0FDFA',
    surface: '#FFFFFF',
    surfaceHover: '#F0F9FF',
    border: '#CBD5E1',
    text: '#0F172A',
    textSecondary: '#334155',
    textMuted: '#94A3B8',
    success: '#059669',
    warning: '#D97706',
    error: '#DC2626',
    info: '#0D9488',
  },
  dark: {
    primary: '#14B8A6',
    primaryHover: '#0D9488',
    secondary: '#94A3B8',
    accent: '#2DD4BF',
    background: '#0F172A',
    surface: '#1E293B',
    surfaceHover: '#263548',
    border: '#334155',
    text: '#F1F5F9',
    textSecondary: '#CBD5E1',
    textMuted: '#64748B',
    success: '#34D399',
    warning: '#FBBF24',
    error: '#F87171',
    info: '#14B8A6',
  },
};

const forestHealth: ThemeDefinition = {
  name: 'forest-health',
  label: 'Forest Health',
  description: 'Green/earth tones, organic feel',
  light: {
    primary: '#059669',
    primaryHover: '#047857',
    secondary: '#78716C',
    accent: '#10B981',
    background: '#F0FDF4',
    surface: '#FFFFFF',
    surfaceHover: '#ECFDF5',
    border: '#D6D3D1',
    text: '#1C1917',
    textSecondary: '#44403C',
    textMuted: '#A8A29E',
    success: '#059669',
    warning: '#CA8A04',
    error: '#DC2626',
    info: '#0284C7',
  },
  dark: {
    primary: '#10B981',
    primaryHover: '#059669',
    secondary: '#A8A29E',
    accent: '#34D399',
    background: '#0C1A12',
    surface: '#162B20',
    surfaceHover: '#1E3A2B',
    border: '#2D4A3A',
    text: '#F5F5F4',
    textSecondary: '#D6D3D1',
    textMuted: '#78716C',
    success: '#34D399',
    warning: '#FACC15',
    error: '#F87171',
    info: '#38BDF8',
  },
};

const midnightAI: ThemeDefinition = {
  name: 'midnight-ai',
  label: 'Midnight AI',
  description: 'Pure dark, neon cyan/purple accents',
  light: {
    primary: '#7C3AED',
    primaryHover: '#6D28D9',
    secondary: '#6B7280',
    accent: '#8B5CF6',
    background: '#FAF5FF',
    surface: '#FFFFFF',
    surfaceHover: '#F5F3FF',
    border: '#D1D5DB',
    text: '#111827',
    textSecondary: '#374151',
    textMuted: '#9CA3AF',
    success: '#059669',
    warning: '#D97706',
    error: '#DC2626',
    info: '#7C3AED',
  },
  dark: {
    primary: '#A78BFA',
    primaryHover: '#8B5CF6',
    secondary: '#9CA3AF',
    accent: '#8B5CF6',
    background: '#0B0D17',
    surface: '#131627',
    surfaceHover: '#1C1F35',
    border: '#2D3054',
    text: '#F9FAFB',
    textSecondary: '#D1D5DB',
    textMuted: '#6B7280',
    success: '#34D399',
    warning: '#FBBF24',
    error: '#F87171',
    info: '#A78BFA',
  },
};

const sunriseWarm: ThemeDefinition = {
  name: 'sunrise-warm',
  label: 'Sunrise Warm',
  description: 'Warm whites, amber/coral accents',
  light: {
    primary: '#EA580C',
    primaryHover: '#C2410C',
    secondary: '#78716C',
    accent: '#F97316',
    background: '#FFFBEB',
    surface: '#FFFFFF',
    surfaceHover: '#FFF7ED',
    border: '#D6D3D1',
    text: '#1C1917',
    textSecondary: '#44403C',
    textMuted: '#A8A29E',
    success: '#16A34A',
    warning: '#CA8A04',
    error: '#DC2626',
    info: '#2563EB',
  },
  dark: {
    primary: '#FB923C',
    primaryHover: '#F97316',
    secondary: '#A8A29E',
    accent: '#F97316',
    background: '#1C1107',
    surface: '#2A1D10',
    surfaceHover: '#36271A',
    border: '#4A3520',
    text: '#FEF3C7',
    textSecondary: '#D6D3D1',
    textMuted: '#78716C',
    success: '#4ADE80',
    warning: '#FACC15',
    error: '#F87171',
    info: '#60A5FA',
  },
};

const royalMedical: ThemeDefinition = {
  name: 'royal-medical',
  label: 'Royal Medical',
  description: 'Deep purple/gold, premium enterprise',
  light: {
    primary: '#7C2D8E',
    primaryHover: '#6B21A8',
    secondary: '#6B7280',
    accent: '#A855F7',
    background: '#FDF4FF',
    surface: '#FFFFFF',
    surfaceHover: '#FAF5FF',
    border: '#D1D5DB',
    text: '#111827',
    textSecondary: '#374151',
    textMuted: '#9CA3AF',
    success: '#059669',
    warning: '#D97706',
    error: '#DC2626',
    info: '#7C2D8E',
  },
  dark: {
    primary: '#C084FC',
    primaryHover: '#A855F7',
    secondary: '#9CA3AF',
    accent: '#A855F7',
    background: '#1A0A20',
    surface: '#2D1238',
    surfaceHover: '#3B1A4A',
    border: '#4C2060',
    text: '#F9FAFB',
    textSecondary: '#D1D5DB',
    textMuted: '#6B7280',
    success: '#34D399',
    warning: '#FBBF24',
    error: '#F87171',
    info: '#C084FC',
  },
};

const themes: Record<ThemeName, ThemeDefinition> = {
  'electric-blue': electricBlue,
  'deep-ocean': deepOcean,
  'forest-health': forestHealth,
  'midnight-ai': midnightAI,
  'sunrise-warm': sunriseWarm,
  'royal-medical': royalMedical,
};

export function getTheme(name: ThemeName): ThemeDefinition {
  return themes[name];
}

export function getAllThemes(): ThemeDefinition[] {
  return Object.values(themes);
}

export function applyTheme(name: ThemeName, isDarkMode: boolean, fontName?: FontFamily): void {
  const theme = themes[name];
  if (!theme) return;

  const colors = isDarkMode ? theme.dark : theme.light;
  const root = document.documentElement;

  root.style.setProperty('--mi-primary', colors.primary);
  root.style.setProperty('--mi-primary-hover', colors.primaryHover);
  root.style.setProperty('--mi-secondary', colors.secondary);
  root.style.setProperty('--mi-accent', colors.accent);
  root.style.setProperty('--mi-background', colors.background);
  root.style.setProperty('--mi-surface', colors.surface);
  root.style.setProperty('--mi-surface-hover', colors.surfaceHover);
  root.style.setProperty('--mi-border', colors.border);
  root.style.setProperty('--mi-text', colors.text);
  root.style.setProperty('--mi-text-secondary', colors.textSecondary);
  root.style.setProperty('--mi-text-muted', colors.textMuted);
  root.style.setProperty('--mi-success', colors.success);
  root.style.setProperty('--mi-warning', colors.warning);
  root.style.setProperty('--mi-error', colors.error);
  root.style.setProperty('--mi-info', colors.info);

  if (isDarkMode) {
    root.classList.add('dark');
    root.setAttribute('data-mantine-color-scheme', 'dark');
  } else {
    root.classList.remove('dark');
    root.setAttribute('data-mantine-color-scheme', 'light');
  }

  root.setAttribute('data-theme', name);

  const font = getFont(fontName ?? 'inter');
  root.style.setProperty('--mi-font-family', font.family);
  root.style.setProperty('--mi-font-mono', font.monoFamily);
}

/* ========================================================================= */
/* Font Theme System                                                         */
/* ========================================================================= */

export type FontFamily = 'inter' | 'dm-sans' | 'space-grotesk';

export interface FontDefinition {
  name: FontFamily;
  label: string;
  family: string;
  monoFamily: string;
}

const fontFamilies: FontDefinition[] = [
  { name: 'inter', label: 'Inter', family: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", monoFamily: "'JetBrains Mono', 'Fira Code', monospace" },
  { name: 'dm-sans', label: 'DM Sans', family: "'DM Sans', 'Inter', -apple-system, sans-serif", monoFamily: "'DM Mono', 'JetBrains Mono', monospace" },
  { name: 'space-grotesk', label: 'Space Grotesk', family: "'Space Grotesk', 'Inter', -apple-system, sans-serif", monoFamily: "'Space Mono', 'JetBrains Mono', monospace" },
];

export function getAllFonts(): FontDefinition[] { return fontFamilies; }
export function getFont(name: FontFamily): FontDefinition { return fontFamilies.find((f) => f.name === name) ?? fontFamilies[0]; }
