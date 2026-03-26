import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface PDFHighlightMeta {
  confidence?: number;
  code?: string;
  description?: string;
  sourceSection?: string;
  provider?: string;
  dateOfService?: string;
  pageHint?: number;
  pdf?: string;
  exactQuote?: string;
  charStart?: number;
  charEnd?: number;
}

export interface PDFHighlight {
  id: string;
  type: 'diagnosis' | 'hedis' | 'negated' | 'meat' | 'ml' | 'search' | 'icd';
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
  text?: string;
  label?: string;
  meta?: PDFHighlightMeta;
}

interface PDFState {
  currentPage: number;
  numPages: number;
  zoom: number;
  fitMode: 'width' | 'page' | 'none';
  highlights: PDFHighlight[];
  activeHighlightId: string | null;
  searchMatches: PDFHighlight[];
  showThumbnails: boolean;
  pendingEvidenceSearch: {
    text: string;
    type: PDFHighlight['type'];
    label?: string;
    meta?: PDFHighlightMeta;
  } | null;

  setCurrentPage: (page: number) => void;
  setNumPages: (numPages: number) => void;
  setZoom: (zoom: number) => void;
  setFitMode: (mode: 'width' | 'page' | 'none') => void;
  addHighlight: (highlight: PDFHighlight) => void;
  removeHighlight: (id: string) => void;
  clearHighlights: () => void;
  setActiveHighlight: (id: string | null) => void;
  setSearchMatches: (matches: PDFHighlight[]) => void;
  clearSearchMatches: () => void;
  toggleThumbnails: () => void;
  setShowThumbnails: (show: boolean) => void;
  navigateToText: (text: string, type: PDFHighlight['type'], label?: string, meta?: PDFHighlightMeta) => void;
  clearPendingEvidence: () => void;
}

export const usePDFStore = create<PDFState>()(
  persist(
    (set) => ({
      currentPage: 1,
      numPages: 0,
      zoom: 1.0,
      fitMode: 'width' as const,
      highlights: [],
      activeHighlightId: null,
      searchMatches: [],
      showThumbnails: false,
      pendingEvidenceSearch: null,

      setCurrentPage: (page) =>
        set((state) => ({
          currentPage: Math.max(1, Math.min(page, state.numPages || 1)),
        })),

      setNumPages: (numPages) =>
        set({ numPages }),

      setZoom: (zoom) =>
        set({ zoom: Math.max(0.5, Math.min(3.0, zoom)), fitMode: 'none' }),

      setFitMode: (mode) =>
        set({ fitMode: mode }),

      addHighlight: (highlight) =>
        set((state) => ({
          highlights: [
            ...state.highlights.filter((h) => h.id !== highlight.id),
            highlight,
          ],
        })),

      removeHighlight: (id) =>
        set((state) => ({
          highlights: state.highlights.filter((h) => h.id !== id),
          activeHighlightId:
            state.activeHighlightId === id ? null : state.activeHighlightId,
        })),

      clearHighlights: () =>
        set({ highlights: [], activeHighlightId: null }),

      setActiveHighlight: (id) =>
        set((state) => {
          const highlight = id
            ? state.highlights.find((h) => h.id === id) ||
              state.searchMatches.find((h) => h.id === id)
            : null;
          return {
            activeHighlightId: id,
            currentPage: highlight ? highlight.page : state.currentPage,
          };
        }),

      setSearchMatches: (matches) =>
        set({ searchMatches: matches }),

      clearSearchMatches: () =>
        set({ searchMatches: [], activeHighlightId: null }),

      toggleThumbnails: () =>
        set((state) => ({ showThumbnails: !state.showThumbnails })),

      setShowThumbnails: (show) =>
        set({ showThumbnails: show }),

      navigateToText: (text, type, label, meta) =>
        set({
          pendingEvidenceSearch: { text, type, label, meta },
        }),

      clearPendingEvidence: () =>
        set({ pendingEvidenceSearch: null }),
    }),
    {
      name: 'medinsight5-pdf',
      partialize: (state) => ({
        zoom: state.zoom,
        fitMode: state.fitMode,
        showThumbnails: state.showThumbnails,
      }),
    },
  ),
);
