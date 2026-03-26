import {
  useState,
  useRef,
  useCallback,
  useEffect,
  useMemo,
} from 'react';
import { Box, Text, Loader, Group, ActionIcon, Tooltip } from '@mantine/core';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { IconStethoscope } from '@tabler/icons-react';
import { usePDFStore, type PDFHighlight } from '../../stores/pdfStore';
import { PDFControls } from './PDFControls';
import { PDFThumbnails } from './PDFThumbnails';
import { EvidencePopover } from './EvidencePopover';
import { PDFQuickAddDiagnosis } from './PDFQuickAddDiagnosis';
import { getHighlightColor } from '../../utils/colors';

/* ========================================================================= */
/* Configure PDF.js Worker                                                    */
/* ========================================================================= */
/* Use the worker from react-pdf's bundled pdfjs-dist to avoid version mismatch
   between the top-level pdfjs-dist (5.5.207) and react-pdf's nested copy (5.4.296). */
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'react-pdf/node_modules/pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

/* ========================================================================= */
/* Highlight style maps (sleek gradients, not hard boxes)                     */
/* ========================================================================= */
const HIGHLIGHT_STYLES: Record<
  PDFHighlight['type'],
  { bg: string; bgActive: string; border: string; borderActive: string; glow: string; shadow: string }
> = {
  diagnosis: {
    bg: 'rgba(59,130,246,0.12)',
    bgActive: 'rgba(59,130,246,0.22)',
    border: 'rgba(59,130,246,0.45)',
    borderActive: 'rgba(59,130,246,0.8)',
    glow: '0 0 16px rgba(59,130,246,0.35), 0 0 4px rgba(59,130,246,0.2)',
    shadow: '0 2px 8px rgba(59,130,246,0.15)',
  },
  hedis: {
    bg: 'rgba(16,185,129,0.12)',
    bgActive: 'rgba(16,185,129,0.22)',
    border: 'rgba(16,185,129,0.45)',
    borderActive: 'rgba(16,185,129,0.8)',
    glow: '0 0 16px rgba(16,185,129,0.35), 0 0 4px rgba(16,185,129,0.2)',
    shadow: '0 2px 8px rgba(16,185,129,0.15)',
  },
  negated: {
    bg: 'rgba(239,68,68,0.12)',
    bgActive: 'rgba(239,68,68,0.22)',
    border: 'rgba(239,68,68,0.45)',
    borderActive: 'rgba(239,68,68,0.8)',
    glow: '0 0 16px rgba(239,68,68,0.35), 0 0 4px rgba(239,68,68,0.2)',
    shadow: '0 2px 8px rgba(239,68,68,0.15)',
  },
  meat: {
    bg: 'rgba(245,158,11,0.12)',
    bgActive: 'rgba(245,158,11,0.22)',
    border: 'rgba(245,158,11,0.45)',
    borderActive: 'rgba(245,158,11,0.8)',
    glow: '0 0 16px rgba(245,158,11,0.35), 0 0 4px rgba(245,158,11,0.2)',
    shadow: '0 2px 8px rgba(245,158,11,0.15)',
  },
  ml: {
    bg: 'rgba(139,92,246,0.12)',
    bgActive: 'rgba(139,92,246,0.22)',
    border: 'rgba(139,92,246,0.45)',
    borderActive: 'rgba(139,92,246,0.8)',
    glow: '0 0 16px rgba(139,92,246,0.35), 0 0 4px rgba(139,92,246,0.2)',
    shadow: '0 2px 8px rgba(139,92,246,0.15)',
  },
  search: {
    bg: 'rgba(255,235,59,0.45)',
    bgActive: 'rgba(255,152,0,0.55)',
    border: 'rgba(255,235,59,0.8)',
    borderActive: 'rgba(255,152,0,0.95)',
    glow: '0 0 20px rgba(255,235,59,0.5), 0 0 6px rgba(255,235,59,0.3)',
    shadow: '0 2px 10px rgba(255,235,59,0.25)',
  },
  icd: {
    bg: 'rgba(6,182,212,0.12)',
    bgActive: 'rgba(6,182,212,0.22)',
    border: 'rgba(6,182,212,0.45)',
    borderActive: 'rgba(6,182,212,0.8)',
    glow: '0 0 16px rgba(6,182,212,0.35), 0 0 4px rgba(6,182,212,0.2)',
    shadow: '0 2px 8px rgba(6,182,212,0.15)',
  },
};

/* ========================================================================= */
/* Utility: Normalize text for comparison                                     */
/* ========================================================================= */
function normalizeText(text: string): string {
  return text.replace(/\s+/g, ' ').trim().toLowerCase();
}

type PDFTextItem = {
  str: string;
  transform: number[];
  width: number;
  height: number;
};

function isPDFTextItem(item: unknown): item is PDFTextItem {
  if (!item || typeof item !== 'object') return false;
  const candidate = item as Record<string, unknown>;
  return typeof candidate.str === 'string'
    && Array.isArray(candidate.transform)
    && typeof candidate.width === 'number'
    && typeof candidate.height === 'number';
}

/* ========================================================================= */
/* Utility: Find text position via rendered DOM text layer (most reliable)    */
/* ========================================================================= */
function findTextInRenderedPage(
  pageEl: HTMLElement,
  searchText: string,
): { x: number; y: number; w: number; h: number } | null {
  if (!searchText || searchText.length < 2) return null;

  const textLayer = pageEl.querySelector('.react-pdf__Page__textContent, .textLayer');
  if (!textLayer) return null;

  const spans = Array.from(textLayer.querySelectorAll('span')).filter(
    (s) => (s.textContent || '').length > 0,
  ) as HTMLElement[];
  if (spans.length === 0) return null;

  const texts = spans.map((s) => s.textContent || '');
  const fullText = texts.join(' ').replace(/[\r\n]+/g, ' ');
  const fullTextLower = fullText.toLowerCase().replace(/\s+/g, ' ');
  const queryClean = searchText.replace(/[\r\n]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
  const query = queryClean.length > 80 ? queryClean.slice(0, 80) : queryClean;
  if (query.length < 2) return null;

  let matchStart = fullTextLower.indexOf(query);
  let matchLen = query.length;

  /* Fallback: try with collapsed whitespace in both sides */
  if (matchStart === -1) {
    const normalizedFull = fullTextLower.replace(/\s+/g, '');
    const normalizedQuery = query.replace(/\s+/g, '');
    const normalizedIdx = normalizedFull.indexOf(normalizedQuery);
    if (normalizedIdx !== -1) {
      /* Map back to original position: walk chars in original */
      let origIdx = 0;
      let stripped = 0;
      while (stripped < normalizedIdx && origIdx < fullTextLower.length) {
        if (!/\s/.test(fullTextLower[origIdx])) stripped++;
        origIdx++;
      }
      matchStart = origIdx;
      /* Find end position similarly */
      let endStripped = 0;
      let endIdx = origIdx;
      while (endStripped < normalizedQuery.length && endIdx < fullTextLower.length) {
        if (!/\s/.test(fullTextLower[endIdx])) endStripped++;
        endIdx++;
      }
      matchLen = endIdx - origIdx;
    }
  }

  /* Fallback: find first significant word if full match fails */
  if (matchStart === -1) {
    const words = query.split(' ').filter((w) => w.length > 3);
    for (const word of words) {
      const wIdx = fullTextLower.indexOf(word);
      if (wIdx !== -1) {
        matchStart = wIdx;
        matchLen = word.length;
        break;
      }
    }
  }
  if (matchStart === -1) return null;

  const matchEnd = matchStart + matchLen;
  const pageRect = pageEl.getBoundingClientRect();
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  let charPos = 0;

  for (let i = 0; i < spans.length; i++) {
    const spanStart = charPos;
    const spanEnd = charPos + texts[i].length;
    charPos = spanEnd + 1; // +1 for join space

    if (spanStart < matchEnd && spanEnd > matchStart) {
      const rect = spans[i].getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) continue;
      if (rect.left < minX) minX = rect.left;
      if (rect.top < minY) minY = rect.top;
      if (rect.right > maxX) maxX = rect.right;
      if (rect.bottom > maxY) maxY = rect.bottom;
    }
  }

  if (minX === Infinity) return null;

  return {
    x: Math.max(0, minX - pageRect.left - 3),
    y: Math.max(0, minY - pageRect.top - 2),
    w: Math.max(20, maxX - minX + 6),
    h: Math.max(14, maxY - minY + 4),
  };
}

/* ========================================================================= */
/* Props                                                                      */
/* ========================================================================= */
interface PDFViewerProps {
  pdfUrl: string;
}

/* ========================================================================= */
/* Component                                                                  */
/* ========================================================================= */
export function PDFViewer({ pdfUrl }: PDFViewerProps) {
  const {
    currentPage,
    numPages,
    zoom,
    fitMode,
    highlights,
    activeHighlightId,
    searchMatches,
    showThumbnails,
    pendingEvidenceSearch,
    setCurrentPage,
    setNumPages,
    setZoom,
    addHighlight,
    setActiveHighlight,
    clearPendingEvidence,
    clearHighlights,
  } = usePDFStore();

  /* Refs */
  const containerRef = useRef<HTMLDivElement>(null);
  const pageContainerRef = useRef<HTMLDivElement>(null);

  /* State */
  const [containerWidth, setContainerWidth] = useState(600);
  const [containerHeight, setContainerHeight] = useState(800);
  const [pdfDocProxy, setPdfDocProxy] = useState<pdfjs.PDFDocumentProxy | null>(null);
  const [hoveredHighlight, setHoveredHighlight] = useState<PDFHighlight | null>(null);
  const [popoverPosition, setPopoverPosition] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [activeGlowId, setActiveGlowId] = useState<string | null>(null);
  const popoverHoverRef = useRef(false);
  const dismissTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [pageDims, setPageDims] = useState<Record<number, number>>({});

  /* Text selection → add diagnosis */
  const [textSelection, setTextSelection] = useState<{
    text: string;
    page: number;
    rect: { x: number; y: number };
  } | null>(null);
  const [quickAddOpen, setQuickAddOpen] = useState(false);
  const justSelectedTextRef = useRef(false);

  const handleTextSelectionUp = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.toString().trim()) {
      return; /* Don't clear immediately — let click handler do it */
    }
    const selectedText = sel.toString().trim();
    if (selectedText.length < 3) return;

    /* Find which page the selection is in */
    const anchorNode = sel.anchorNode;
    if (!anchorNode) return;
    const pageEl = (anchorNode.nodeType === Node.ELEMENT_NODE
      ? anchorNode as Element
      : anchorNode.parentElement
    )?.closest('[data-page]');

    const pageNum = pageEl ? parseInt(pageEl.getAttribute('data-page') || '1', 10) : currentPage;

    /* Position the floating button near the end of selection */
    const range = sel.getRangeAt(0);
    const rangeRect = range.getBoundingClientRect();
    const containerRect = containerRef.current?.getBoundingClientRect();
    const offsetX = containerRect ? rangeRect.right - containerRect.left : rangeRect.right;
    const offsetY = containerRect ? rangeRect.top - containerRect.top : rangeRect.top;

    setTextSelection({
      text: selectedText.slice(0, 500),
      page: pageNum,
      rect: { x: offsetX, y: offsetY - 36 },
    });
    /* Prevent the subsequent click event from immediately clearing this selection */
    justSelectedTextRef.current = true;
    setTimeout(() => { justSelectedTextRef.current = false; }, 0);
  }, [currentPage]);

  /* Clear selection when clicking background (only if not clicking the button) */
  const clearTextSelection = useCallback(() => {
    setTextSelection(null);
  }, []);

  /* Measure container size */
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setContainerWidth(width);
        setContainerHeight(height);
      }
    });

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  /* Calculate effective page width based on fit mode */
  const effectiveWidth = useMemo(() => {
    const thumbnailOffset = showThumbnails ? 140 : 0;
    const availableWidth = containerWidth - thumbnailOffset - 40; // 40px padding
    const availableHeight = containerHeight - 60; // controls bar height

    if (fitMode === 'width') {
      return Math.max(300, availableWidth);
    }
    if (fitMode === 'page') {
      /* Use approximate A4 ratio 8.5:11 */
      const widthFromHeight = availableHeight * (8.5 / 11);
      return Math.max(300, Math.min(availableWidth, widthFromHeight));
    }
    /* none: use zoom-based width */
    return Math.max(300, (pageDims[1] || 612) * zoom);
  }, [fitMode, zoom, containerWidth, containerHeight, showThumbnails, pageDims]);

  /* Handle document load success */
  const onDocumentLoadSuccess = useCallback(
    async (doc: pdfjs.PDFDocumentProxy) => {
      setNumPages(doc.numPages);
      setPdfDocProxy(doc);
      if (currentPage > doc.numPages) {
        setCurrentPage(1);
      }
      /* Preload page widths for correct highlight scaling (fallback) */
      const dims: Record<number, number> = {};
      for (let i = 1; i <= Math.min(doc.numPages, 200); i++) {
        try {
          const pg = await doc.getPage(i);
          const vp = pg.getViewport({ scale: 1.0 });
          dims[i] = vp.width;
        } catch {
          dims[i] = 612;
        }
      }
      setPageDims(dims);
    },
    [setNumPages, currentPage, setCurrentPage],
  );

  /* ===================================================================== */
  /* Evidence Text Search: Find text in PDF and create highlight            */
  /* ===================================================================== */
  useEffect(() => {
    if (!pendingEvidenceSearch || !pdfDocProxy) return;

    const { text, type, label, meta } = pendingEvidenceSearch;

    const searchForText = async () => {
      const preferredText = (meta?.exactQuote && meta.exactQuote.trim()) || text;
      const normalizedQuery = normalizeText(preferredText);
      /* Try substring of first 80 chars if full text is long */
      const querySubstring =
        normalizedQuery.length > 80
          ? normalizedQuery.slice(0, 80)
          : normalizedQuery;

      /* Extract words for word-matching fallback */
      const queryWords = normalizedQuery
        .split(/\s+/)
        .filter((w) => w.length > 3);

      let bestPage = -1;
      let bestScore = 0;
      let bestX = 50;
      let bestY = 100;
      let bestWidth = 400;
      let bestHeight = 24;
      let foundText = preferredText;
      const hintedPage = Number(meta?.pageHint);
      const validHint =
        Number.isFinite(hintedPage) && hintedPage >= 1 && hintedPage <= pdfDocProxy.numPages
          ? hintedPage
          : null;
      const pageOrder = validHint
        ? [validHint, ...Array.from({ length: pdfDocProxy.numPages }, (_, i) => i + 1).filter((p) => p !== validHint)]
        : Array.from({ length: pdfDocProxy.numPages }, (_, i) => i + 1);

      for (const pageNum of pageOrder) {
        try {
          const page = await pdfDocProxy.getPage(pageNum);
          const textContent = await page.getTextContent();
          const viewport = page.getViewport({ scale: 1.0 });

          const items = textContent.items.reduce<PDFTextItem[]>((acc, item) => {
            if (isPDFTextItem(item) && item.str.length > 0) acc.push(item);
            return acc;
          }, []);

          const fullPageText = items.map((item) => item.str).join(' ');
          const normalizedPage = normalizeText(fullPageText);

          /* Strategy 1: Exact substring match */
          let substringIdx = normalizedPage.indexOf(querySubstring);
          if (substringIdx !== -1) {
            /* Find the text items that correspond to this match */
            const matchBounds = findTextItemBounds(items, viewport, substringIdx, querySubstring.length, normalizedPage);
            if (matchBounds) {
              bestPage = pageNum;
              bestScore = 100;
              bestX = matchBounds.x;
              bestY = matchBounds.y;
              bestWidth = matchBounds.width;
              bestHeight = matchBounds.height;
              foundText = fullPageText.slice(substringIdx, substringIdx + querySubstring.length);
              break;
            }
          }

          /* Strategy 2: Word-based matching */
          if (queryWords.length > 0) {
            let wordMatches = 0;
            for (const word of queryWords) {
              if (normalizedPage.includes(word)) {
                wordMatches++;
              }
            }
            const score = wordMatches / queryWords.length;
            if (score > bestScore && score > 0.5) {
              /* Find the best matching region */
              const firstWord = queryWords.find((w) => normalizedPage.includes(w));
              if (firstWord) {
                const wordIdx = normalizedPage.indexOf(firstWord);
                const matchBounds = findTextItemBounds(items, viewport, wordIdx, firstWord.length, normalizedPage);
                if (matchBounds) {
                  bestPage = pageNum;
                  bestScore = score;
                  bestX = matchBounds.x;
                  bestY = matchBounds.y;
                  bestWidth = Math.min(matchBounds.width * 3, viewport.width * 0.8);
                  bestHeight = matchBounds.height;
                  foundText = text;
                }
              }
            }
          }
        } catch {
          /* Continue to next page */
        }
      }

      if (bestPage <= 0 && validHint) {
        bestPage = validHint;
        bestX = 40;
        bestY = 80;
        bestWidth = 420;
        bestHeight = 24;
      }

      if (bestPage > 0) {
        const highlightId = `evidence-${type}-${Date.now()}`;
        const highlight: PDFHighlight = {
          id: highlightId,
          type,
          page: bestPage,
          x: bestX,
          y: bestY,
          width: bestWidth,
          height: bestHeight,
          text: foundText,
          label: label,
          meta,
        };

        addHighlight(highlight);
        setCurrentPage(bestPage);
        setActiveHighlight(highlightId);

        /* Flash the glow animation */
        setActiveGlowId(highlightId);
        setTimeout(() => setActiveGlowId(null), 3000);

        /* Scroll the actual highlight element into view after render */
        isProgrammaticScroll.current = true;
        if (programmaticScrollTimer.current) clearTimeout(programmaticScrollTimer.current);
        setTimeout(() => {
          const highlightEl = document.querySelector(`[data-highlight-id="${highlightId}"]`);
          if (highlightEl) {
            highlightEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
          } else {
            /* Fallback: scroll to the page */
            const pageEl = pageRefs.current[bestPage];
            if (pageEl) pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
          programmaticScrollTimer.current = setTimeout(() => {
            isProgrammaticScroll.current = false;
          }, 800);
        }, 300);
      }

      clearPendingEvidence();
    };

    searchForText();
  }, [pendingEvidenceSearch, pdfDocProxy, addHighlight, setCurrentPage, setActiveHighlight, clearPendingEvidence]);

  /* ===================================================================== */
  /* Find bounds of text items matching a range in the page text             */
  /* ===================================================================== */
  function findTextItemBounds(
    items: PDFTextItem[],
    viewport: { width: number; height: number },
    charStart: number,
    matchLength: number,
    normalizedPageText: string,
  ): { x: number; y: number; width: number; height: number } | null {
    /* Build a mapping from normalized-text offset to text items */
    let charIdx = 0;
    const itemRanges: { start: number; end: number; item: typeof items[0] }[] = [];

    for (const item of items) {
      const normalizedItem = normalizeText(item.str);
      const itemStart = normalizedPageText.indexOf(normalizedItem, charIdx > 0 ? charIdx - 1 : 0);
      if (itemStart >= 0) {
        itemRanges.push({
          start: itemStart,
          end: itemStart + normalizedItem.length,
          item,
        });
        charIdx = itemStart + normalizedItem.length;
      }
    }

    const charEnd = charStart + matchLength;

    /* Find all items that overlap with our match range */
    const matchingItems = itemRanges.filter(
      (r) => r.start < charEnd && r.end > charStart,
    );

    if (matchingItems.length === 0) return null;

    /* Compute bounding box from transforms */
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;

    for (const { item } of matchingItems) {
      const [, , , , tx, ty] = item.transform;
      const fontSize = Math.abs(item.transform[0]) || 12;
      /* PDF coordinates: origin is bottom-left; convert to top-left */
      const x = tx;
      const y = viewport.height - ty;
      const w = item.width || fontSize * item.str.length * 0.6;
      const h = fontSize * 1.2;

      if (x < minX) minX = x;
      if (y - h < minY) minY = y - h;
      if (x + w > maxX) maxX = x + w;
      if (y > maxY) maxY = y;
    }

    /* Add padding */
    const pad = 3;
    return {
      x: Math.max(0, minX - pad),
      y: Math.max(0, minY - pad),
      width: Math.min(viewport.width, maxX - minX + pad * 2),
      height: Math.max(16, maxY - minY + pad * 2),
    };
  }

  /* ===================================================================== */
  /* Highlights grouped by page                                             */
  /* ===================================================================== */
  const highlightsByPage = useMemo(() => {
    const map: Record<number, PDFHighlight[]> = {};
    for (const h of highlights) {
      if (!map[h.page]) map[h.page] = [];
      map[h.page].push(h);
    }
    for (const h of searchMatches) {
      if (!map[h.page]) map[h.page] = [];
      map[h.page].push(h);
    }
    return map;
  }, [highlights, searchMatches]);

  /* Refs for each page element (for scrolling to page) */
  const pageRefs = useRef<Record<number, HTMLDivElement | null>>({});
  /* Flag to suppress IntersectionObserver updates during programmatic scroll */
  const isProgrammaticScroll = useRef(false);
  const programmaticScrollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* Track visible page via IntersectionObserver (only from user scroll) */
  useEffect(() => {
    const container = pageContainerRef.current;
    if (!container) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (isProgrammaticScroll.current) return;
        for (const entry of entries) {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
            const pageNum = parseInt(entry.target.getAttribute('data-page') || '1', 10);
            if (pageNum !== currentPage) {
              setCurrentPage(pageNum);
            }
            break;
          }
        }
      },
      {
        root: container,
        threshold: 0.5,
      },
    );

    const refs = pageRefs.current;
    for (const [, el] of Object.entries(refs)) {
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [numPages, setCurrentPage, currentPage]);

  /* Scroll to a specific page element */
  const scrollToPage = useCallback((pageNum: number) => {
    const el = pageRefs.current[pageNum];
    if (!el) return;

    /* Suppress observer during programmatic scroll */
    isProgrammaticScroll.current = true;
    if (programmaticScrollTimer.current) clearTimeout(programmaticScrollTimer.current);

    el.scrollIntoView({ behavior: 'smooth', block: 'center' });

    /* Re-enable observer after scroll settles */
    programmaticScrollTimer.current = setTimeout(() => {
      isProgrammaticScroll.current = false;
    }, 800);
  }, []);

  /* Track the last page we scrolled to, to avoid re-triggering */
  const lastScrolledPage = useRef(currentPage);

  /* When currentPage changes via controls (not observer), scroll to it */
  useEffect(() => {
    if (currentPage !== lastScrolledPage.current) {
      lastScrolledPage.current = currentPage;
      setTimeout(() => scrollToPage(currentPage), 50);
    }
  }, [currentPage, scrollToPage]);

  /* ===================================================================== */
  /* Handle download                                                        */
  /* ===================================================================== */
  const handleDownload = useCallback(() => {
    const link = document.createElement('a');
    link.href = pdfUrl;
    link.download = pdfUrl.split('/').pop() || 'document.pdf';
    link.click();
  }, [pdfUrl]);

  /* ===================================================================== */
  /* Highlight hover with persistence - popover stays while mouse is on     */
  /* highlight or popover, click outside dismisses                          */
  /* ===================================================================== */
  const cancelDismiss = useCallback(() => {
    if (dismissTimerRef.current) {
      clearTimeout(dismissTimerRef.current);
      dismissTimerRef.current = null;
    }
  }, []);

  const startDismiss = useCallback(() => {
    cancelDismiss();
    dismissTimerRef.current = setTimeout(() => {
      if (!popoverHoverRef.current) {
        setHoveredHighlight(null);
      }
    }, 350);
  }, [cancelDismiss]);

  const handleHighlightMouseEnter = useCallback(
    (highlight: PDFHighlight, e: React.MouseEvent) => {
      if (highlight.type === 'search') return;
      cancelDismiss();

      /* Get the highlight element's viewport position.
         Position: popup's bottom-left corner = highlight's top-left corner
         (popup appears ABOVE the highlighted text). */
      const highlightEl = e.currentTarget as HTMLElement;
      const rect = highlightEl.getBoundingClientRect();

      setHoveredHighlight(highlight);
      setPopoverPosition({
        x: rect.left,
        y: rect.top,  /* This is the highlight top; popover will use bottom = this */
      });
    },
    [cancelDismiss],
  );

  const handleHighlightMouseLeave = useCallback(() => {
    startDismiss();
  }, [startDismiss]);

  const handlePopoverMouseEnter = useCallback(() => {
    popoverHoverRef.current = true;
    cancelDismiss();
  }, [cancelDismiss]);

  const handlePopoverMouseLeave = useCallback(() => {
    popoverHoverRef.current = false;
    startDismiss();
  }, [startDismiss]);

  /* Close popover on click outside + clear evidence highlights */
  const handleBackgroundClick = useCallback(() => {
    cancelDismiss();
    popoverHoverRef.current = false;
    setHoveredHighlight(null);
    setActiveHighlight(null);
    clearHighlights();
  }, [cancelDismiss, setActiveHighlight, clearHighlights]);

  /* ===================================================================== */
  /* Render                                                                 */
  /* ===================================================================== */
  return (
    <Box
      ref={containerRef}
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        position: 'relative',
        overflow: 'hidden',
        background: 'var(--mi-background)',
      }}
    >
      {/* Controls bar with inline search */}
      <Box style={{ position: 'relative', zIndex: 100 }}>
        <PDFControls onDownload={handleDownload} pdfDocProxy={pdfDocProxy} />
      </Box>

      {/* Main content: thumbnails + page */}
      <Box
        style={{
          display: 'flex',
          flex: 1,
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {/* Thumbnails sidebar */}
        <PDFThumbnails pdfUrl={pdfUrl} visible={showThumbnails} />

        {/* PDF Page area - scrollable continuous view */}
        <Box
          ref={pageContainerRef}
          onClick={(e) => {
            /* Don't clear text selection if clicking the add-diagnosis button */
            if ((e.target as HTMLElement).closest('[data-add-dx-btn]')) return;
            handleBackgroundClick();
            if (!justSelectedTextRef.current) clearTextSelection();
          }}
          onMouseUp={handleTextSelectionUp}
          style={{
            flex: 1,
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '12px 0',
            position: 'relative',
            gap: 0,
          }}
        >
          <Document
            file={pdfUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            loading={
              <Box
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: 400,
                  gap: 16,
                }}
              >
                <Loader size="lg" color="var(--mi-primary)" type="dots" />
                <Text size="sm" c="dimmed">
                  Loading PDF...
                </Text>
              </Box>
            }
            error={
              <Box
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: 400,
                  gap: 12,
                  color: 'var(--mi-text-muted)',
                }}
              >
                <Text size="md" fw={600} style={{ color: 'var(--mi-error)' }}>
                  Failed to load PDF
                </Text>
                <Text size="sm" c="dimmed">
                  The file may be missing or corrupted.
                </Text>
              </Box>
            }
          >
            {/* Render all pages in a continuous scroll */}
            {numPages > 0 && Array.from({ length: numPages }, (_, i) => i + 1).map((pageNum) => {
              const pageHighlights = highlightsByPage[pageNum] || [];
              const pageW = pageDims[pageNum] || pageDims[1] || 612;
              const scale = effectiveWidth / pageW;

              return (
                <Box
                  key={pageNum}
                  ref={(el) => { pageRefs.current[pageNum] = el; }}
                  data-page={pageNum}
                  style={{
                    position: 'relative',
                    display: 'inline-block',
                    boxShadow: 'var(--mi-shadow-lg)',
                    borderRadius: 'var(--mi-radius-sm)',
                    overflow: 'hidden',
                    background: '#FFFFFF',
                    marginBottom: 12,
                  }}
                >
                  <Page
                    pageNumber={pageNum}
                    width={effectiveWidth}
                    renderTextLayer={true}
                    renderAnnotationLayer={true}
                    loading={
                      <Box
                        style={{
                          width: effectiveWidth,
                          height: effectiveWidth * 1.294,
                          background:
                            'linear-gradient(90deg, var(--mi-surface-hover) 0%, var(--mi-surface) 50%, var(--mi-surface-hover) 100%)',
                          backgroundSize: '200% 100%',
                          animation: 'mi-shimmer 1.5s infinite',
                        }}
                      />
                    }
                  />

                  {/* Highlight overlays — DOM-based positioning for accuracy */}
                  {pageHighlights.map((highlight) => {
                    const hlStyle = HIGHLIGHT_STYLES[highlight.type];
                    const colorMeta = getHighlightColor(highlight.type);
                    const isActive =
                      activeHighlightId === highlight.id ||
                      activeGlowId === highlight.id;

                    /* Try DOM text layer for pixel-perfect positioning */
                    const pgEl = pageRefs.current[pageNum];
                    let hlLeft = highlight.x * scale;
                    let hlTop = highlight.y * scale;
                    let hlWidth = highlight.width * scale;
                    let hlHeight = highlight.height * scale;

                    if (pgEl && highlight.text) {
                      const domPos = findTextInRenderedPage(pgEl, highlight.text);
                      if (domPos) {
                        hlLeft = domPos.x;
                        hlTop = domPos.y;
                        hlWidth = domPos.w;
                        hlHeight = domPos.h;
                      }
                    }

                    return (
                      <Box
                        key={highlight.id}
                        data-highlight-id={highlight.id}
                        onMouseEnter={(e) => handleHighlightMouseEnter(highlight, e)}
                        onMouseLeave={handleHighlightMouseLeave}
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveHighlight(highlight.id);
                        }}
                        style={{
                          position: 'absolute',
                          left: hlLeft,
                          top: hlTop,
                          width: hlWidth,
                          height: hlHeight,
                          background: isActive ? hlStyle.bgActive : hlStyle.bg,
                          borderLeft: `3px solid ${isActive ? hlStyle.borderActive : hlStyle.border}`,
                          borderRadius: 4,
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                          boxShadow: isActive ? hlStyle.glow : 'none',
                          animation: isActive ? 'mi-highlight-pulse 2s ease-in-out 3' : undefined,
                          zIndex: isActive ? 10 : 5,
                          pointerEvents: 'auto',
                          minWidth: 20,
                          minHeight: 12,
                        }}
                      >
                        {isActive && highlight.label && (
                          <Box
                            style={{
                              position: 'absolute',
                              top: -26,
                              left: -2,
                              padding: '3px 10px',
                              borderRadius: 'var(--mi-radius-full)',
                              fontSize: 10,
                              fontWeight: 700,
                              fontFamily: '”JetBrains Mono”, monospace',
                              whiteSpace: 'nowrap',
                              background: colorMeta.fill,
                              color: '#FFFFFF',
                              boxShadow: '0 2px 8px rgba(0,0,0,0.15), 0 0 0 1px rgba(255,255,255,0.1) inset',
                              animation: 'mi-fade-in 0.2s ease-out',
                              lineHeight: '16px',
                              letterSpacing: '0.03em',
                            }}
                          >
                            {highlight.label}
                          </Box>
                        )}
                        {isActive && (
                          <Box
                            style={{
                              position: 'absolute',
                              top: -4,
                              right: -4,
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              background: colorMeta.fill,
                              boxShadow: `0 0 6px ${hlStyle.borderActive}`,
                              animation: 'mi-pulse-glow 2s infinite',
                            }}
                          />
                        )}
                      </Box>
                    );
                  })}

                  {/* Page number label */}
                  <Box
                    style={{
                      position: 'absolute',
                      bottom: 4,
                      right: 8,
                      padding: '2px 8px',
                      borderRadius: 'var(--mi-radius-full)',
                      background: 'rgba(0,0,0,0.5)',
                      backdropFilter: 'blur(4px)',
                      fontSize: 10,
                      fontWeight: 600,
                      color: '#fff',
                      opacity: 0.7,
                      pointerEvents: 'none',
                    }}
                  >
                    {pageNum}
                  </Box>
                </Box>
              );
            })}
          </Document>

        </Box>

      </Box>

      {/* Evidence popover - fixed position so it floats over everything */}
      {hoveredHighlight && (
        <EvidencePopover
          highlight={hoveredHighlight}
          position={popoverPosition}
          containerRect={null}
          onClose={() => {
            popoverHoverRef.current = false;
            cancelDismiss();
            setHoveredHighlight(null);
          }}
          onMouseEnter={handlePopoverMouseEnter}
          onMouseLeave={handlePopoverMouseLeave}
          confidence={hoveredHighlight.meta?.confidence}
          icdCode={hoveredHighlight.meta?.code}
          icdDescription={hoveredHighlight.meta?.description}
          sourceSection={hoveredHighlight.meta?.sourceSection}
          provider={hoveredHighlight.meta?.provider}
          dateOfService={hoveredHighlight.meta?.dateOfService}
        />
      )}

      {/* Page indicator at bottom */}
      {numPages > 0 && (
        <Group
          justify="center"
          style={{
            padding: '6px 0',
            borderTop: '1px solid var(--mi-border)',
            background: 'var(--mi-surface)',
          }}
        >
          <Text size="xs" c="dimmed" fw={500}>
            Page {currentPage} of {numPages}
          </Text>
        </Group>
      )}

      {/* Floating "Add Diagnosis" button on text selection */}
      {textSelection && !quickAddOpen && (
        <Tooltip label="Add diagnosis from selected text" withArrow position="top">
          <ActionIcon
            data-add-dx-btn
            size={32}
            radius="xl"
            variant="filled"
            color="violet"
            onClick={() => {
              setQuickAddOpen(true);
            }}
            style={{
              position: 'absolute',
              left: Math.max(8, Math.min(textSelection.rect.x - 16, containerWidth - 44)),
              top: Math.max(60, textSelection.rect.y),
              zIndex: 600,
              boxShadow: '0 4px 14px rgba(139,92,246,0.35), 0 0 0 2px rgba(139,92,246,0.15)',
              animation: 'mi-fade-in 0.15s ease-out',
            }}
          >
            <IconStethoscope size={16} stroke={2} />
          </ActionIcon>
        </Tooltip>
      )}

      {/* Quick add diagnosis modal */}
      <PDFQuickAddDiagnosis
        opened={quickAddOpen}
        onClose={() => {
          setQuickAddOpen(false);
          setTextSelection(null);
          window.getSelection()?.removeAllRanges();
        }}
        selectedText={textSelection?.text ?? ''}
        pageNumber={textSelection?.page ?? currentPage}
      />

      {/* CSS for highlight pulse animation */}
      <style>{`
        @keyframes mi-highlight-pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.6;
          }
        }

        @keyframes mi-fade-in {
          from { opacity: 0; transform: scale(0.8); }
          to { opacity: 1; transform: scale(1); }
        }

        /* Hide react-pdf annotation layer yellow icons */
        .react-pdf__Page__annotations {
          pointer-events: none;
        }
        .react-pdf__Page__annotations .linkAnnotation,
        .react-pdf__Page__annotations .popupAnnotation,
        .react-pdf__Page__annotations section {
          display: none !important;
        }

        /* Text layer: fully transparent text for selection, not visible overlay */
        .react-pdf__Page__textContent {
          opacity: 1 !important;
          mix-blend-mode: normal !important;
        }
        .react-pdf__Page__textContent span {
          color: transparent !important;
        }
        .react-pdf__Page__textContent span::selection {
          background-color: color-mix(in srgb, var(--mi-primary) 30%, transparent);
          color: transparent;
        }

        /* Ensure highlight overlays render above the PDF text layer */
        .react-pdf__Page {
          z-index: 0 !important;
        }
        [data-highlight-id] {
          z-index: 5 !important;
        }
      `}</style>
    </Box>
  );
}
