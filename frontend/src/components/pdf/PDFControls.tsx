import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  Box,
  Group,
  ActionIcon,
  TextInput,
  Text,
  Menu,
  Tooltip,
  Divider,
} from '@mantine/core';
import {
  IconChevronLeft,
  IconChevronRight,
  IconMinus,
  IconPlus,
  IconArrowsMaximize,
  IconArrowAutofitWidth,
  IconDownload,
  IconLayoutSidebar,
  IconSearch,
  IconChevronUp,
  IconChevronDown,
  IconX,
} from '@tabler/icons-react';
import { usePDFStore, type PDFHighlight } from '../../stores/pdfStore';

/* ========================================================================= */
/* Zoom Presets                                                               */
/* ========================================================================= */
const ZOOM_PRESETS = [
  { label: '50%', value: 0.5 },
  { label: '75%', value: 0.75 },
  { label: '100%', value: 1.0 },
  { label: '125%', value: 1.25 },
  { label: '150%', value: 1.5 },
  { label: '200%', value: 2.0 },
  { label: '250%', value: 2.5 },
  { label: '300%', value: 3.0 },
];

/* ========================================================================= */
/* Search match type                                                          */
/* ========================================================================= */
interface SearchMatch {
  page: number;
  text: string;
  index: number;
}

/* ========================================================================= */
/* Props                                                                      */
/* ========================================================================= */
interface PDFControlsProps {
  onDownload?: () => void;
  pdfDocProxy?: unknown | null;
}

/* ========================================================================= */
/* Component                                                                  */
/* ========================================================================= */
export function PDFControls({ onDownload, pdfDocProxy }: PDFControlsProps) {
  const {
    currentPage,
    numPages,
    zoom,
    fitMode,
    showThumbnails,
    searchMatches,
    setCurrentPage,
    setZoom,
    setFitMode,
    toggleThumbnails,
    setSearchMatches,
    clearSearchMatches,
    setActiveHighlight,
  } = usePDFStore();

  const [pageInput, setPageInput] = useState(String(currentPage));
  const pageInputRef = useRef<HTMLInputElement>(null);

  /* Search state - always visible */
  const [searchQuery, setSearchQuery] = useState('');
  const [matches, setMatches] = useState<SearchMatch[]>([]);
  const [activeMatchIdx, setActiveMatchIdx] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  /* Sync page input with store */
  useEffect(() => {
    setPageInput(String(currentPage));
  }, [currentPage]);

  /* Focus search input on Ctrl+F */

  /* Close results dropdown when clicking outside */
  useEffect(() => {
    if (!showResults) return;
    const handleClick = (e: MouseEvent) => {
      if (resultsRef.current && !resultsRef.current.contains(e.target as Node)) {
        setShowResults(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showResults]);

  const handlePageInputSubmit = useCallback(() => {
    const page = parseInt(pageInput, 10);
    if (!isNaN(page) && page >= 1 && page <= numPages) {
      setCurrentPage(page);
    } else {
      setPageInput(String(currentPage));
    }
  }, [pageInput, numPages, currentPage, setCurrentPage]);

  const handlePageInputKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        handlePageInputSubmit();
        pageInputRef.current?.blur();
      }
      if (e.key === 'Escape') {
        setPageInput(String(currentPage));
        pageInputRef.current?.blur();
      }
    },
    [handlePageInputSubmit, currentPage],
  );

  /* ===================================================================== */
  /* Search logic                                                           */
  /* ===================================================================== */
  const performSearch = useCallback(
    async (query: string) => {
      if (!query.trim() || !pdfDocProxy) {
        setMatches([]);
        clearSearchMatches();
        return;
      }

      setIsSearching(true);
      const doc = pdfDocProxy as {
        numPages: number;
        getPage: (n: number) => Promise<{
          getTextContent: () => Promise<{ items: { str: string }[] }>;
        }>;
      };
      const found: SearchMatch[] = [];
      const highlights: PDFHighlight[] = [];
      const queryLower = query.toLowerCase();

      try {
        for (let pageNum = 1; pageNum <= doc.numPages; pageNum++) {
          const page = await doc.getPage(pageNum);
          const textContent = await page.getTextContent();
          const pageText = textContent.items
            .map((item) => ('str' in item ? item.str : ''))
            .join(' ');
          const pageTextLower = pageText.toLowerCase();

          let searchIdx = 0;
          while (true) {
            const foundIdx = pageTextLower.indexOf(queryLower, searchIdx);
            if (foundIdx === -1) break;

            const matchText = pageText.slice(
              Math.max(0, foundIdx - 30),
              Math.min(pageText.length, foundIdx + query.length + 30),
            );

            const matchIndex = found.length;
            found.push({ page: pageNum, text: matchText, index: matchIndex });

            highlights.push({
              id: `search-${pageNum}-${foundIdx}`,
              type: 'search',
              page: pageNum,
              x: 0,
              y: 0,
              width: 0,
              height: 0,
              text: pageText.slice(foundIdx, foundIdx + query.length),
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
        setShowResults(true);

        /* Scroll to the page in continuous-scroll mode */
        setTimeout(() => {
          const pageEl = document.querySelector(`[data-page="${found[0].page}"]`);
          if (pageEl) pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
      }

      setIsSearching(false);
    },
    [pdfDocProxy, clearSearchMatches, setSearchMatches, setCurrentPage],
  );

  /* Debounced search */
  useEffect(() => {
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);

    if (!searchQuery.trim()) {
      setMatches([]);
      clearSearchMatches();
      setShowResults(false);
      return;
    }

    searchTimeoutRef.current = setTimeout(() => {
      performSearch(searchQuery);
    }, 300);

    return () => {
      if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    };
  }, [searchQuery, performSearch, clearSearchMatches]);

  /* Navigate between matches */
  const goToMatch = useCallback(
    (idx: number) => {
      if (matches.length === 0) return;
      const wrappedIdx = ((idx % matches.length) + matches.length) % matches.length;
      setActiveMatchIdx(wrappedIdx);
      const match = matches[wrappedIdx];
      setCurrentPage(match.page);

      /* Set the active highlight so the matching overlay gets the glow */
      const highlightId = searchMatches[wrappedIdx]?.id;
      if (highlightId) {
        setActiveHighlight(highlightId);
      }

      /* Scroll the search highlight or page into view */
      setTimeout(() => {
        if (highlightId) {
          const hlEl = document.querySelector(`[data-highlight-id="${highlightId}"]`);
          if (hlEl) {
            hlEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
          }
        }
        const pageEl = document.querySelector(`[data-page="${match.page}"]`);
        if (pageEl) {
          pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 150);
    },
    [matches, searchMatches, setCurrentPage, setActiveHighlight],
  );

  const handleSearchKeyDown = useCallback(
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
        setSearchQuery('');
        setMatches([]);
        clearSearchMatches();
        setShowResults(false);
        searchInputRef.current?.blur();
      }
    },
    [goToMatch, activeMatchIdx],
  );

  /* Ctrl+F handler - focus the always-visible search input */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'f') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  /* Matches grouped by page for dropdown */
  const matchesByPage = useMemo(() => {
    const groups: Record<number, SearchMatch[]> = {};
    matches.forEach((m) => {
      if (!groups[m.page]) groups[m.page] = [];
      groups[m.page].push(m);
    });
    return groups;
  }, [matches]);

  const zoomPercent = `${Math.round(zoom * 100)}%`;

  return (
    <Box
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '3px 6px',
        borderBottom: '1px solid var(--mi-border)',
        background: 'var(--mi-surface)',
        minHeight: 36,
        gap: 6,
        position: 'relative',
        flexWrap: 'nowrap',
      }}
    >
      {/* Search input */}
      <Box style={{ position: 'relative', flexShrink: 0 }} ref={resultsRef}>
        <Group gap={2} wrap="nowrap">
          <TextInput
            ref={searchInputRef}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.currentTarget.value)}
            onKeyDown={handleSearchKeyDown}
            onFocus={() => { if (matches.length > 0) setShowResults(true); }}
            placeholder="Search PDF..."
            size="xs"
            leftSection={<IconSearch size={12} stroke={2} style={{ color: 'var(--mi-text-muted)' }} />}
            rightSection={
              <Group gap={2} wrap="nowrap">
                {matches.length > 0 && (
                  <Text size="xs" fw={600} style={{ color: 'var(--mi-text-muted)', whiteSpace: 'nowrap', fontSize: 9 }}>
                    {activeMatchIdx + 1}/{matches.length}
                  </Text>
                )}
                {searchQuery && (
                  <ActionIcon
                    size={14}
                    radius="xl"
                    variant="subtle"
                    color="gray"
                    onClick={() => { setSearchQuery(''); setMatches([]); clearSearchMatches(); setShowResults(false); searchInputRef.current?.focus(); }}
                  >
                    <IconX size={9} />
                  </ActionIcon>
                )}
              </Group>
            }
            rightSectionWidth={matches.length > 0 ? 60 : 20}
            styles={{
              input: {
                width: 180,
                height: 28,
                minHeight: 28,
                fontSize: 11,
                backgroundColor: 'var(--mi-background)',
                borderColor: 'var(--mi-border)',
                color: 'var(--mi-text)',
                borderRadius: 'var(--mi-radius-full)',
                paddingLeft: 28,
              },
            }}
            aria-label="Search in PDF"
          />

          {matches.length > 0 && (
            <>
              <ActionIcon size={22} radius="xl" variant="subtle" color="gray" onClick={() => goToMatch(activeMatchIdx - 1)} aria-label="Previous match">
                <IconChevronUp size={12} stroke={2} />
              </ActionIcon>
              <ActionIcon size={22} radius="xl" variant="subtle" color="gray" onClick={() => goToMatch(activeMatchIdx + 1)} aria-label="Next match">
                <IconChevronDown size={12} stroke={2} />
              </ActionIcon>
            </>
          )}
        </Group>

        {/* Search results dropdown */}
        {showResults && matches.length > 0 && (
          <Box
            style={{
              position: 'absolute',
              top: 32,
              left: 0,
              width: 320,
              zIndex: 600,
              borderRadius: 10,
              border: '1px solid var(--mi-glass-border)',
              background: 'var(--mi-surface)',
              boxShadow: 'var(--mi-shadow-xl)',
              overflow: 'hidden',
            }}
          >
            <Box style={{ padding: '5px 10px', borderBottom: '1px solid var(--mi-border)', background: 'var(--mi-surface-hover)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Text size="xs" fw={600} style={{ color: 'var(--mi-text-muted)', fontSize: 9 }}>
                {matches.length} result{matches.length !== 1 ? 's' : ''} across {Object.keys(matchesByPage).length} page{Object.keys(matchesByPage).length !== 1 ? 's' : ''}
              </Text>
              <ActionIcon size={14} radius="xl" variant="subtle" color="gray" onClick={() => setShowResults(false)}>
                <IconX size={9} />
              </ActionIcon>
            </Box>
            <Box style={{ padding: '3px 0' }}>
              {Object.entries(matchesByPage).slice(0, 5).map(([pageStr, pageMatches]) => (
                <Box key={pageStr}>
                  <Text size="xs" fw={700} style={{ padding: '4px 10px 2px', color: 'var(--mi-primary)', fontSize: 9, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                    Page {pageStr}
                  </Text>
                  {pageMatches.slice(0, 3).map((match) => (
                    <Box
                      key={match.index}
                      onClick={() => { goToMatch(match.index); setShowResults(false); }}
                      style={{
                        padding: '5px 10px',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                        backgroundColor: activeMatchIdx === match.index ? 'color-mix(in srgb, var(--mi-primary) 8%, transparent)' : 'transparent',
                        borderLeft: activeMatchIdx === match.index ? '2px solid var(--mi-primary)' : '2px solid transparent',
                      }}
                      onMouseEnter={(e) => { if (activeMatchIdx !== match.index) e.currentTarget.style.backgroundColor = 'var(--mi-surface-hover)'; }}
                      onMouseLeave={(e) => { if (activeMatchIdx !== match.index) e.currentTarget.style.backgroundColor = 'transparent'; }}
                    >
                      <Text size="xs" style={{ color: 'var(--mi-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 10 }}>
                        ...{match.text}...
                      </Text>
                    </Box>
                  ))}
                </Box>
              ))}
            </Box>
          </Box>
        )}
      </Box>

      {/* Divider */}
      <Divider orientation="vertical" style={{ height: 18, alignSelf: 'center', borderColor: 'var(--mi-border)' }} />

      {/* Thumbnails toggle */}
      <Tooltip label={showThumbnails ? 'Hide thumbnails' : 'Show thumbnails'}>
        <ActionIcon size={26} radius="xl" variant={showThumbnails ? 'filled' : 'subtle'} color={showThumbnails ? 'blue' : 'gray'} onClick={toggleThumbnails} aria-label="Toggle thumbnails">
          <IconLayoutSidebar size={13} stroke={1.8} />
        </ActionIcon>
      </Tooltip>

      <Divider orientation="vertical" style={{ height: 18, alignSelf: 'center', borderColor: 'var(--mi-border)' }} />

      {/* Page navigation */}
      <Group gap={2} wrap="nowrap">
        <Tooltip label="Previous page">
          <ActionIcon size={26} radius="xl" variant="subtle" color="gray" onClick={() => setCurrentPage(currentPage - 1)} disabled={currentPage <= 1} aria-label="Previous page">
            <IconChevronLeft size={13} stroke={2} />
          </ActionIcon>
        </Tooltip>
        <Group gap={3} wrap="nowrap" align="center">
          <TextInput
            ref={pageInputRef}
            value={pageInput}
            onChange={(e) => setPageInput(e.currentTarget.value)}
            onBlur={handlePageInputSubmit}
            onKeyDown={handlePageInputKeyDown}
            size="xs"
            styles={{
              input: {
                width: 30,
                height: 22,
                minHeight: 22,
                textAlign: 'center',
                padding: '0 3px',
                fontSize: 10,
                fontWeight: 600,
                borderRadius: 'var(--mi-radius-sm)',
                backgroundColor: 'var(--mi-background)',
                borderColor: 'var(--mi-border)',
                color: 'var(--mi-text)',
              },
            }}
            aria-label="Page number"
          />
          <Text size="xs" c="dimmed" style={{ userSelect: 'none', whiteSpace: 'nowrap', fontSize: 10 }}>
            / {numPages || '--'}
          </Text>
        </Group>
        <Tooltip label="Next page">
          <ActionIcon size={26} radius="xl" variant="subtle" color="gray" onClick={() => setCurrentPage(currentPage + 1)} disabled={currentPage >= numPages} aria-label="Next page">
            <IconChevronRight size={13} stroke={2} />
          </ActionIcon>
        </Tooltip>
      </Group>

      <Divider orientation="vertical" style={{ height: 18, alignSelf: 'center', borderColor: 'var(--mi-border)' }} />

      {/* Zoom controls */}
      <Group gap={2} wrap="nowrap">
        <Tooltip label="Zoom out">
          <ActionIcon size={26} radius="xl" variant="subtle" color="gray" onClick={() => setZoom(zoom - 0.1)} disabled={zoom <= 0.5} aria-label="Zoom out">
            <IconMinus size={12} stroke={2} />
          </ActionIcon>
        </Tooltip>

        <Menu shadow="md" width={110} position="bottom" radius="md" transitionProps={{ transition: 'pop', duration: 150 }}>
          <Menu.Target>
            <Tooltip label="Zoom level">
              <Box
                component="button"
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '1px 4px',
                  borderRadius: 'var(--mi-radius-sm)',
                  fontSize: 10,
                  fontWeight: 600,
                  color: 'var(--mi-text)',
                  transition: 'background var(--mi-transition-fast)',
                  minWidth: 36,
                  textAlign: 'center',
                }}
                onMouseEnter={(e: React.MouseEvent<HTMLButtonElement>) => { e.currentTarget.style.backgroundColor = 'var(--mi-surface-hover)'; }}
                onMouseLeave={(e: React.MouseEvent<HTMLButtonElement>) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
              >
                {zoomPercent}
              </Box>
            </Tooltip>
          </Menu.Target>
          <Menu.Dropdown style={{ backgroundColor: 'var(--mi-surface)', borderColor: 'var(--mi-border)' }}>
            {ZOOM_PRESETS.map((preset) => (
              <Menu.Item
                key={preset.value}
                onClick={() => setZoom(preset.value)}
                style={{
                  color: 'var(--mi-text)',
                  fontWeight: Math.abs(zoom - preset.value) < 0.01 ? 700 : 400,
                  backgroundColor: Math.abs(zoom - preset.value) < 0.01 ? 'color-mix(in srgb, var(--mi-primary) 10%, transparent)' : undefined,
                }}
              >
                {preset.label}
              </Menu.Item>
            ))}
          </Menu.Dropdown>
        </Menu>

        <Tooltip label="Zoom in">
          <ActionIcon size={26} radius="xl" variant="subtle" color="gray" onClick={() => setZoom(zoom + 0.1)} disabled={zoom >= 3.0} aria-label="Zoom in">
            <IconPlus size={12} stroke={2} />
          </ActionIcon>
        </Tooltip>
      </Group>

      <Divider orientation="vertical" style={{ height: 18, alignSelf: 'center', borderColor: 'var(--mi-border)' }} />

      {/* Fit modes */}
      <Group gap={2} wrap="nowrap">
        <Tooltip label="Fit to width">
          <ActionIcon size={26} radius="xl" variant={fitMode === 'width' ? 'filled' : 'subtle'} color={fitMode === 'width' ? 'blue' : 'gray'} onClick={() => setFitMode(fitMode === 'width' ? 'none' : 'width')} aria-label="Fit to width">
            <IconArrowAutofitWidth size={13} stroke={1.8} />
          </ActionIcon>
        </Tooltip>
        <Tooltip label="Fit to page">
          <ActionIcon size={26} radius="xl" variant={fitMode === 'page' ? 'filled' : 'subtle'} color={fitMode === 'page' ? 'blue' : 'gray'} onClick={() => setFitMode(fitMode === 'page' ? 'none' : 'page')} aria-label="Fit to page">
            <IconArrowsMaximize size={13} stroke={1.8} />
          </ActionIcon>
        </Tooltip>
      </Group>

      {/* Download */}
      {onDownload && (
        <>
          <Divider orientation="vertical" style={{ height: 18, alignSelf: 'center', borderColor: 'var(--mi-border)' }} />
          <Tooltip label="Download PDF">
            <ActionIcon size={26} radius="xl" variant="subtle" color="gray" onClick={onDownload} aria-label="Download PDF">
              <IconDownload size={13} stroke={1.8} />
            </ActionIcon>
          </Tooltip>
        </>
      )}
    </Box>
  );
}
