import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  TextInput,
  ActionIcon,
  Text,
  Group,
  ScrollArea,
} from '@mantine/core';
import {
  IconSearch,
  IconChevronUp,
  IconChevronDown,
  IconX,
  IconFileDescription,
} from '@tabler/icons-react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePDFStore, type PDFHighlight } from '../../stores/pdfStore';

/* ========================================================================= */
/* Types                                                                      */
/* ========================================================================= */
interface SearchMatch {
  page: number;
  text: string;
  index: number;
}

type PDFTextItem = {
  str: string;
  transform: number[];
  width: number;
  height: number;
};

interface PDFSearchBarProps {
  visible: boolean;
  onClose: () => void;
  pdfDocProxy: unknown | null; // pdfjs PDFDocumentProxy
}

/* ========================================================================= */
/* Constants                                                                  */
/* ========================================================================= */
const MAX_RECENT_SEARCHES = 5;
const STORAGE_KEY = 'medinsight5-pdf-recent-searches';

/* ========================================================================= */
/* Utility: compute bounding box for a text match from PDF text items         */
/* ========================================================================= */
function findSearchBounds(
  items: PDFTextItem[],
  viewportHeight: number,
  viewportWidth: number,
  charStart: number,
  matchLength: number,
): { x: number; y: number; width: number; height: number } | null {
  /* Build character offset → item mapping */
  let charIdx = 0;
  const itemRanges: { start: number; end: number; item: PDFTextItem }[] = [];

  for (const item of items) {
    const len = item.str.length;
    if (len > 0) {
      itemRanges.push({ start: charIdx, end: charIdx + len, item });
    }
    /* +1 for the space between items in the joined string */
    charIdx += len + 1;
  }

  const charEnd = charStart + matchLength;

  /* Find items overlapping the match range */
  const matchingItems = itemRanges.filter(
    (r) => r.start < charEnd && r.end > charStart,
  );

  if (matchingItems.length === 0) return null;

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const { item } of matchingItems) {
    const [, , , , tx, ty] = item.transform;
    const fontSize = Math.abs(item.transform[0]) || 12;
    const x = tx;
    const y = viewportHeight - ty;
    const w = item.width || fontSize * item.str.length * 0.6;
    const h = fontSize * 1.2;

    if (x < minX) minX = x;
    if (y - h < minY) minY = y - h;
    if (x + w > maxX) maxX = x + w;
    if (y > maxY) maxY = y;
  }

  const pad = 3;
  return {
    x: Math.max(0, minX - pad),
    y: Math.max(0, minY - pad),
    width: Math.min(viewportWidth, maxX - minX + pad * 2),
    height: Math.max(16, maxY - minY + pad * 2),
  };
}

/* ========================================================================= */
/* Component - Always-visible inline search on left side                      */
/* ========================================================================= */
export function PDFSearchBar({ visible, onClose, pdfDocProxy }: PDFSearchBarProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [matches, setMatches] = useState<SearchMatch[]>([]);
  const [activeMatchIdx, setActiveMatchIdx] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? (JSON.parse(stored) as string[]) : [];
    } catch {
      return [];
    }
  });

  const { setSearchMatches, clearSearchMatches, setCurrentPage, setActiveHighlight } = usePDFStore();
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* Focus input when bar becomes visible */
  useEffect(() => {
    if (visible) {
      setTimeout(() => inputRef.current?.focus(), 100);
    } else {
      setQuery('');
      setMatches([]);
      clearSearchMatches();
      setShowDropdown(false);
    }
  }, [visible, clearSearchMatches]);

  /* Save recent searches */
  const addRecentSearch = useCallback(
    (q: string) => {
      const trimmed = q.trim();
      if (!trimmed) return;
      setRecentSearches((prev) => {
        const filtered = prev.filter((s) => s !== trimmed);
        const updated = [trimmed, ...filtered].slice(0, MAX_RECENT_SEARCHES);
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
        } catch { /* ignore */ }
        return updated;
      });
    },
    [],
  );

  /* Perform text search across all pages */
  const performSearch = useCallback(
    async (searchQuery: string) => {
      if (!searchQuery.trim() || !pdfDocProxy) {
        setMatches([]);
        clearSearchMatches();
        return;
      }

      setIsSearching(true);
      const doc = pdfDocProxy as {
        numPages: number;
        getPage: (n: number) => Promise<{
          getTextContent: () => Promise<{ items: unknown[] }>;
          getViewport: (opts: { scale: number }) => { width: number; height: number };
        }>;
      };
      const found: SearchMatch[] = [];
      const highlights: PDFHighlight[] = [];
      const queryLower = searchQuery.toLowerCase();

      try {
        for (let pageNum = 1; pageNum <= doc.numPages; pageNum++) {
          const page = await doc.getPage(pageNum);
          const textContent = await page.getTextContent();
          const viewport = page.getViewport({ scale: 1.0 });

          /* Filter to valid text items with position data */
          const textItems: PDFTextItem[] = [];
          for (const raw of textContent.items) {
            const item = raw as Record<string, unknown>;
            if (
              typeof item.str === 'string' &&
              item.str.length > 0 &&
              Array.isArray(item.transform) &&
              typeof item.width === 'number'
            ) {
              textItems.push(raw as PDFTextItem);
            }
          }

          const pageText = textItems.map((item) => item.str).join(' ');
          const pageTextLower = pageText.toLowerCase();

          let searchIdx = 0;
          while (true) {
            const foundIdx = pageTextLower.indexOf(queryLower, searchIdx);
            if (foundIdx === -1) break;

            const matchText = pageText.slice(
              Math.max(0, foundIdx - 30),
              Math.min(pageText.length, foundIdx + searchQuery.length + 30),
            );

            /* Compute actual bounds from text item transforms */
            const bounds = findSearchBounds(
              textItems,
              viewport.height,
              viewport.width,
              foundIdx,
              searchQuery.length,
            );

            const matchIndex = found.length;
            found.push({
              page: pageNum,
              text: matchText,
              index: matchIndex,
            });

            highlights.push({
              id: `search-${pageNum}-${foundIdx}`,
              type: 'search',
              page: pageNum,
              x: bounds?.x ?? 40,
              y: bounds?.y ?? 40,
              width: bounds?.width ?? 200,
              height: bounds?.height ?? 20,
              text: pageText.slice(foundIdx, foundIdx + searchQuery.length),
              label: `Match ${matchIndex + 1}`,
            });

            searchIdx = foundIdx + 1;
          }
        }
      } catch {
        /* PDF may not be fully loaded */
      }

      setMatches(found);
      setSearchMatches(highlights);

      if (found.length > 0) {
        setActiveMatchIdx(0);
        setCurrentPage(found[0].page);
        setActiveHighlight(highlights[0].id);
        addRecentSearch(searchQuery);
      }

      setIsSearching(false);
    },
    [pdfDocProxy, clearSearchMatches, setSearchMatches, setCurrentPage, setActiveHighlight, addRecentSearch],
  );

  /* Debounced search */
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (!query.trim()) {
      setMatches([]);
      clearSearchMatches();
      return;
    }

    searchTimeoutRef.current = setTimeout(() => {
      performSearch(query);
    }, 300);

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [query, performSearch, clearSearchMatches]);

  /* Navigate between matches */
  const goToMatch = useCallback(
    (idx: number) => {
      if (matches.length === 0) return;
      const wrappedIdx = ((idx % matches.length) + matches.length) % matches.length;
      setActiveMatchIdx(wrappedIdx);
      const match = matches[wrappedIdx];
      setCurrentPage(match.page);
      /* Use the same highlight ID format that performSearch creates */
      const matchHighlight = usePDFStore.getState().searchMatches[wrappedIdx];
      if (matchHighlight) {
        setActiveHighlight(matchHighlight.id);
      }

      /* Scroll to the highlight element with retry — page may need time to render */
      const hlId = matchHighlight?.id;
      const tryScroll = (attempt: number) => {
        const hlEl = hlId ? document.querySelector(`[data-highlight-id="${hlId}"]`) : null;
        if (hlEl) {
          hlEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
          return;
        }
        /* Fallback: scroll to page element */
        if (attempt === 0) {
          const pageEl = document.querySelector(`[data-page="${match.page}"]`);
          if (pageEl) {
            pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }
        /* Retry after page renders */
        if (attempt < 4 && hlId) {
          setTimeout(() => tryScroll(attempt + 1), 500);
        }
      };
      setTimeout(() => tryScroll(0), 250);
    },
    [matches, setCurrentPage, setActiveHighlight],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        if (e.shiftKey) {
          goToMatch(activeMatchIdx - 1);
        } else {
          goToMatch(activeMatchIdx + 1);
        }
      }
      if (e.key === 'Escape') {
        onClose();
      }
    },
    [goToMatch, activeMatchIdx, onClose],
  );

  /* Matches grouped by page */
  const matchesByPage = useMemo(() => {
    const groups: Record<number, SearchMatch[]> = {};
    matches.forEach((m) => {
      if (!groups[m.page]) groups[m.page] = [];
      groups[m.page].push(m);
    });
    return groups;
  }, [matches]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -12 }}
          transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
          style={{
            position: 'absolute',
            top: 52,
            left: 12,
            zIndex: 500,
            width: 300,
          }}
        >
          <Box
            style={{
              borderRadius: 'var(--mi-radius-lg)',
              boxShadow: 'var(--mi-shadow-xl)',
              overflow: 'hidden',
              border: '1px solid var(--mi-border)',
              background: 'var(--mi-surface)',
            }}
          >
            {/* Search input */}
            <Box style={{ padding: '8px 10px', borderBottom: '1px solid var(--mi-border)' }}>
              <TextInput
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.currentTarget.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setShowDropdown(true)}
                placeholder="Search in PDF..."
                size="xs"
                leftSection={<IconSearch size={13} stroke={2} />}
                rightSection={
                  <Group gap={4} wrap="nowrap">
                    {matches.length > 0 && (
                      <Text
                        size="xs"
                        fw={600}
                        style={{
                          color: 'var(--mi-text-muted)',
                          whiteSpace: 'nowrap',
                          fontSize: 9,
                        }}
                      >
                        {activeMatchIdx + 1}/{matches.length}
                      </Text>
                    )}
                    {query && (
                      <ActionIcon
                        size={16}
                        radius="xl"
                        variant="subtle"
                        color="gray"
                        onClick={() => {
                          setQuery('');
                          setMatches([]);
                          clearSearchMatches();
                          inputRef.current?.focus();
                        }}
                      >
                        <IconX size={10} />
                      </ActionIcon>
                    )}
                  </Group>
                }
                rightSectionWidth={matches.length > 0 ? 64 : 24}
                styles={{
                  input: {
                    backgroundColor: 'var(--mi-background)',
                    borderColor: 'var(--mi-border)',
                    color: 'var(--mi-text)',
                    borderRadius: 'var(--mi-radius-full)',
                    fontSize: 12,
                    height: 30,
                  },
                }}
              />

              {/* Navigation arrows */}
              {matches.length > 0 && (
                <Group gap={4} justify="flex-end" mt={4}>
                  <ActionIcon
                    size={22}
                    radius="md"
                    variant="subtle"
                    color="gray"
                    onClick={() => goToMatch(activeMatchIdx - 1)}
                    aria-label="Previous match"
                  >
                    <IconChevronUp size={12} stroke={2} />
                  </ActionIcon>
                  <ActionIcon
                    size={22}
                    radius="md"
                    variant="subtle"
                    color="gray"
                    onClick={() => goToMatch(activeMatchIdx + 1)}
                    aria-label="Next match"
                  >
                    <IconChevronDown size={12} stroke={2} />
                  </ActionIcon>
                </Group>
              )}
            </Box>

            {/* Dropdown: Matches by page OR Recent searches */}
            {showDropdown && (
              <ScrollArea.Autosize mah={220}>
                {query.trim() && matches.length > 0 ? (
                  <Box style={{ padding: '4px 0' }}>
                    {Object.entries(matchesByPage).map(([pageStr, pageMatches]) => (
                      <Box key={pageStr}>
                        <Text
                          size="xs"
                          fw={600}
                          c="dimmed"
                          style={{ padding: '4px 10px 2px', textTransform: 'uppercase', fontSize: 9 }}
                        >
                          Page {pageStr} ({pageMatches.length})
                        </Text>
                        {pageMatches.map((match) => (
                          <Box
                            key={match.index}
                            onClick={() => goToMatch(match.index)}
                            style={{
                              padding: '4px 10px',
                              cursor: 'pointer',
                              transition: 'background var(--mi-transition-fast)',
                              backgroundColor:
                                activeMatchIdx === match.index
                                  ? 'color-mix(in srgb, var(--mi-primary) 10%, transparent)'
                                  : 'transparent',
                              borderLeft:
                                activeMatchIdx === match.index
                                  ? '2px solid var(--mi-primary)'
                                  : '2px solid transparent',
                            }}
                            onMouseEnter={(e) => {
                              if (activeMatchIdx !== match.index) {
                                (e.currentTarget as HTMLElement).style.backgroundColor =
                                  'var(--mi-surface-hover)';
                              }
                            }}
                            onMouseLeave={(e) => {
                              if (activeMatchIdx !== match.index) {
                                (e.currentTarget as HTMLElement).style.backgroundColor =
                                  'transparent';
                              }
                            }}
                          >
                            <Text
                              size="xs"
                              style={{
                                color: 'var(--mi-text-secondary)',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                fontSize: 11,
                              }}
                            >
                              ...{match.text}...
                            </Text>
                          </Box>
                        ))}
                      </Box>
                    ))}
                  </Box>
                ) : query.trim() && matches.length === 0 && !isSearching ? (
                  <Box style={{ padding: '14px 10px', textAlign: 'center' }}>
                    <IconFileDescription
                      size={22}
                      stroke={1.5}
                      style={{ color: 'var(--mi-text-muted)', margin: '0 auto 6px' }}
                    />
                    <Text size="xs" c="dimmed">
                      No matches found
                    </Text>
                  </Box>
                ) : !query.trim() && recentSearches.length > 0 ? (
                  <Box style={{ padding: '4px 0' }}>
                    <Text
                      size="xs"
                      fw={600}
                      c="dimmed"
                      style={{ padding: '4px 10px 2px', textTransform: 'uppercase', fontSize: 9 }}
                    >
                      Recent searches
                    </Text>
                    {recentSearches.map((recent) => (
                      <Box
                        key={recent}
                        onClick={() => {
                          setQuery(recent);
                          performSearch(recent);
                        }}
                        style={{
                          padding: '4px 10px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                          transition: 'background var(--mi-transition-fast)',
                        }}
                        onMouseEnter={(e) => {
                          (e.currentTarget as HTMLElement).style.backgroundColor =
                            'var(--mi-surface-hover)';
                        }}
                        onMouseLeave={(e) => {
                          (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
                        }}
                      >
                        <IconSearch size={10} style={{ color: 'var(--mi-text-muted)', flexShrink: 0 }} />
                        <Text
                          size="xs"
                          style={{
                            color: 'var(--mi-text-secondary)',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            fontSize: 11,
                          }}
                        >
                          {recent}
                        </Text>
                      </Box>
                    ))}
                  </Box>
                ) : isSearching ? (
                  <Box style={{ padding: '12px 10px', textAlign: 'center' }}>
                    <Text size="xs" c="dimmed">
                      Searching...
                    </Text>
                  </Box>
                ) : null}
              </ScrollArea.Autosize>
            )}
          </Box>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
