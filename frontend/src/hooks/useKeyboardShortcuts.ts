import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useConfigStore } from '../stores/configStore';
import { useThemeStore } from '../stores/themeStore';
import { useChartStore } from '../stores/chartStore';
import { usePDFStore } from '../stores/pdfStore';

export function useKeyboardShortcuts() {
  const navigate = useNavigate();
  const { toggleSpotlight } = useConfigStore();
  const { toggleDarkMode } = useThemeStore();
  const { activeChartId, setActiveTab } = useChartStore();
  const { currentPage, numPages, zoom, setCurrentPage, setZoom } = usePDFStore();

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const tagName = target.tagName.toLowerCase();
      const isInput =
        tagName === 'input' ||
        tagName === 'textarea' ||
        tagName === 'select' ||
        target.isContentEditable;

      // Ctrl+K or / → toggle spotlight (always active)
      if ((e.ctrlKey && e.key === 'k') || (e.key === '/' && !isInput)) {
        e.preventDefault();
        toggleSpotlight();
        return;
      }

      // Ctrl+U → navigate to upload
      if (e.ctrlKey && e.key === 'u') {
        e.preventDefault();
        navigate('/');
        // Trigger file input via custom event
        window.dispatchEvent(new CustomEvent('medinsight:trigger-upload'));
        return;
      }

      // Ctrl+D → toggle dark mode
      if (e.ctrlKey && e.key === 'd') {
        e.preventDefault();
        toggleDarkMode();
        return;
      }

      // Escape → close spotlight
      if (e.key === 'Escape') {
        useConfigStore.getState().setSpotlightOpen(false);
        return;
      }

      // The following shortcuts only work when NOT focused on an input
      if (isInput) return;

      // 1-6 → switch tabs in chart viewer
      if (activeChartId) {
        const num = parseInt(e.key, 10);
        if (num >= 1 && num <= 6) {
          e.preventDefault();
          setActiveTab(num - 1);
          return;
        }
      }

      // Arrow keys → PDF page navigation
      if (activeChartId && numPages > 0) {
        if (e.key === 'ArrowLeft') {
          e.preventDefault();
          setCurrentPage(currentPage - 1);
          return;
        }
        if (e.key === 'ArrowRight') {
          e.preventDefault();
          setCurrentPage(currentPage + 1);
          return;
        }
      }

      // + / - → PDF zoom
      if (activeChartId) {
        if (e.key === '+' || e.key === '=') {
          e.preventDefault();
          setZoom(zoom + 0.1);
          return;
        }
        if (e.key === '-') {
          e.preventDefault();
          setZoom(zoom - 0.1);
          return;
        }
      }
    },
    [
      toggleSpotlight,
      toggleDarkMode,
      navigate,
      activeChartId,
      setActiveTab,
      currentPage,
      numPages,
      zoom,
      setCurrentPage,
      setZoom,
    ],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}
