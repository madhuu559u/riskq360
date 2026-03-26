import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Modal,
  TextInput,
  Box,
  Text,
  Group,
  Badge,
  UnstyledButton,
  Stack,
  Kbd,
  ScrollArea,
  Loader,
  ThemeIcon,
  Divider,
  SimpleGrid,
  Progress,
  Tabs,
} from '@mantine/core';
import {
  IconSearch,
  IconFile,
  IconStethoscope,
  IconShieldCheck,
  IconHeartRateMonitor,
  IconPill,
  IconHash,
  IconClock,
  IconArrowRight,
  IconCornerDownLeft,
  IconActivity,
  IconDatabase,
  IconSettings,
  IconBrain,
  IconPercentage,
  IconFileAnalytics,
  IconSparkles,
} from '@tabler/icons-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCharts, useDashboardStats } from '../../hooks/useChart';
import { useChartStore } from '../../stores/chartStore';
import { formatRelativeTime, formatChartId, formatRAF, formatDuration, formatPercentValue } from '../../utils/formatters';
import { calculateRelevance } from '../../utils/search';
import { getStatusColor } from '../../utils/colors';

/* ========================================================================= */
/* Types                                                                     */
/* ========================================================================= */
interface SearchResult {
  id: string;
  type: 'chart' | 'diagnosis' | 'hcc' | 'hedis' | 'medication' | 'action';
  title: string;
  subtitle: string;
  icon: typeof IconFile;
  iconColor: string;
  relevance: number;
  action: () => void;
  meta?: Record<string, string | number | null>;
}

interface SpotlightSearchProps {
  opened: boolean;
  onClose: () => void;
}

/* ========================================================================= */
/* Category Metadata                                                         */
/* ========================================================================= */
const CATEGORY_LABELS: Record<string, { label: string; color: string; icon: typeof IconFile }> = {
  chart: { label: 'Charts', color: 'blue', icon: IconFile },
  diagnosis: { label: 'Diagnoses', color: 'teal', icon: IconStethoscope },
  hcc: { label: 'HCC Codes', color: 'indigo', icon: IconShieldCheck },
  hedis: { label: 'HEDIS', color: 'green', icon: IconHeartRateMonitor },
  medication: { label: 'Medications', color: 'orange', icon: IconPill },
  action: { label: 'Quick Actions', color: 'violet', icon: IconSparkles },
};

/* ========================================================================= */
/* Quick Actions                                                             */
/* ========================================================================= */
function useQuickActions(navigate: (path: string) => void, onClose: () => void): SearchResult[] {
  return useMemo(
    () => [
      {
        id: 'action-charts', type: 'action' as const, title: 'Go to Charts',
        subtitle: 'View all processed medical charts', icon: IconFile, iconColor: 'blue',
        relevance: 0, action: () => { navigate('/'); onClose(); },
      },
      {
        id: 'action-dashboard', type: 'action' as const, title: 'Go to Dashboard',
        subtitle: 'System analytics and command center', icon: IconActivity, iconColor: 'teal',
        relevance: 0, action: () => { navigate('/dashboard'); onClose(); },
      },
      {
        id: 'action-settings', type: 'action' as const, title: 'Go to Settings',
        subtitle: 'Configure AI engine, pipeline, and features', icon: IconSettings, iconColor: 'violet',
        relevance: 0, action: () => { navigate('/settings'); onClose(); },
      },
      {
        id: 'action-upload', type: 'action' as const, title: 'Upload Chart',
        subtitle: 'Upload a new medical chart PDF for processing', icon: IconFileAnalytics, iconColor: 'green',
        relevance: 0, action: () => { navigate('/'); onClose(); },
      },
    ],
    [navigate, onClose],
  );
}

/* ========================================================================= */
/* Component                                                                 */
/* ========================================================================= */
export function SpotlightSearch({ opened, onClose }: SpotlightSearchProps) {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [recentSearches, setRecentSearches] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem('medinsight5-recent-searches');
      return stored ? JSON.parse(stored) as string[] : [];
    } catch { return []; }
  });

  const { setActiveChart } = useChartStore();
  const { data: chartsData, isLoading: chartsLoading } = useCharts();
  const { data: dashStats } = useDashboardStats();

  const quickActions = useQuickActions(navigate, onClose);

  /* ----------------------------------------------------------------------- */
  /* Build comprehensive search results                                      */
  /* ----------------------------------------------------------------------- */
  const allResults = useMemo<SearchResult[]>(() => {
    if (!query.trim()) return [];

    const items: SearchResult[] = [];
    const q = query.toLowerCase().trim();

    // Search charts — comprehensive matching
    const charts = chartsData?.charts ?? [];
    for (const chart of charts) {
      const matchText = `${chart.chart_id} ${chart.filename ?? ''} ${chart.status} ${chart.run_id ?? ''} ${chart.raf_summary?.total_raf_score ?? ''}`;
      const relevance = calculateRelevance(matchText, q);
      if (relevance > 0) {
        items.push({
          id: `chart-${chart.chart_id}`,
          type: 'chart',
          title: formatChartId(chart.chart_id, chart.filename),
          subtitle: `Status: ${chart.status}`,
          icon: IconFile,
          iconColor: 'blue',
          relevance,
          action: () => { setActiveChart(chart.chart_id); navigate(`/charts/${chart.chart_id}`); onClose(); },
          meta: {
            raf: chart.raf_summary?.total_raf_score != null ? formatRAF(chart.raf_summary.total_raf_score) : null,
            hccs: chart.raf_summary?.payable_hcc_count ?? null,
            pages: chart.pages_processed,
            time: chart.total_seconds != null ? formatDuration(chart.total_seconds) : null,
            status: chart.status,
            date: chart.started_at ? formatRelativeTime(chart.started_at) : null,
          },
        });
      }

      // Also search within chart's HCC details
      if (chart.raf_summary?.hcc_details) {
        for (const hcc of chart.raf_summary.hcc_details) {
          const hccMatch = `${hcc.hcc_code} ${hcc.hcc_description}`;
          const hccRelevance = calculateRelevance(hccMatch, q);
          if (hccRelevance > 0) {
            const hccId = `hcc-${chart.chart_id}-${hcc.hcc_code}`;
            if (!items.find((i) => i.id === hccId)) {
              items.push({
                id: hccId,
                type: 'hcc',
                title: hcc.hcc_code,
                subtitle: hcc.hcc_description,
                icon: IconShieldCheck,
                iconColor: 'indigo',
                relevance: hccRelevance,
                action: () => { setActiveChart(chart.chart_id); navigate(`/charts/${chart.chart_id}`); onClose(); },
                meta: {
                  raf_weight: hcc.raf_weight?.toFixed(3) ?? null,
                  icd_count: hcc.icd_count ?? null,
                  chart: formatChartId(chart.chart_id, chart.filename),
                },
              });
            }
          }
        }
      }
    }

    // Search quick actions
    for (const action of quickActions) {
      const matchText = `${action.title} ${action.subtitle}`;
      const relevance = calculateRelevance(matchText, q);
      if (relevance > 0) items.push({ ...action, relevance });
    }

    items.sort((a, b) => b.relevance - a.relevance);
    return items.slice(0, 50);
  }, [query, chartsData, quickActions, navigate, onClose, setActiveChart]);

  /* Filter by active category */
  const results = useMemo(() => {
    if (!activeCategory) return allResults;
    return allResults.filter((r) => r.type === activeCategory);
  }, [allResults, activeCategory]);

  /* Category counts */
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const r of allResults) counts[r.type] = (counts[r.type] ?? 0) + 1;
    return counts;
  }, [allResults]);

  /* ----------------------------------------------------------------------- */
  /* Keyboard navigation                                                     */
  /* ----------------------------------------------------------------------- */
  const allItems = query.trim() ? results : quickActions;

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIdx((prev) => Math.min(prev + 1, allItems.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIdx((prev) => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const item = allItems[selectedIdx];
        if (item) {
          if (query.trim()) {
            const newRecent = [query, ...recentSearches.filter((s) => s !== query)].slice(0, 8);
            setRecentSearches(newRecent);
            localStorage.setItem('medinsight5-recent-searches', JSON.stringify(newRecent));
          }
          item.action();
        }
      } else if (e.key === 'Escape') {
        onClose();
      }
    },
    [allItems, selectedIdx, query, recentSearches, onClose],
  );

  /* ----------------------------------------------------------------------- */
  /* Reset state on open                                                     */
  /* ----------------------------------------------------------------------- */
  useEffect(() => {
    if (opened) {
      setQuery('');
      setSelectedIdx(0);
      setActiveCategory(null);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [opened]);

  useEffect(() => { setSelectedIdx(0); }, [query, activeCategory]);

  /* ----------------------------------------------------------------------- */
  /* Render                                                                   */
  /* ----------------------------------------------------------------------- */
  const showRecent = !query.trim() && recentSearches.length > 0;
  const hasResults = query.trim() && results.length > 0;
  const noResults = query.trim() && allResults.length === 0 && !chartsLoading;

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      withCloseButton={false}
      size={560}
      padding={0}
      radius="xl"
      overlayProps={{ backgroundOpacity: 0.3, blur: 8 }}
      styles={{
        content: { backgroundColor: 'var(--mi-surface)', border: '1px solid var(--mi-border)', boxShadow: '0 24px 64px rgba(0,0,0,0.4), var(--mi-shadow-xl)', overflow: 'hidden' },
        body: { padding: 0 },
      }}
      transitionProps={{ transition: 'pop', duration: 200 }}
    >
      {/* Search Input */}
      <Box style={{ padding: '14px 20px', borderBottom: '1px solid var(--mi-border)' }}>
        <TextInput
          ref={inputRef}
          placeholder="Search charts, HCC codes, diagnoses, actions..."
          value={query}
          onChange={(e) => setQuery(e.currentTarget.value)}
          onKeyDown={handleKeyDown}
          size="lg"
          leftSection={
            chartsLoading
              ? <Loader size={20} color="var(--mi-primary)" />
              : <IconSearch size={22} stroke={1.8} color="var(--mi-text-muted)" />
          }
          styles={{
            input: { border: 'none', backgroundColor: 'transparent', fontSize: 17, color: 'var(--mi-text)', '&::placeholder': { color: 'var(--mi-text-muted)' } },
          }}
          variant="unstyled"
        />
      </Box>

      {/* Category filter tabs (when searching) */}
      {query.trim() && allResults.length > 0 && (
        <Box style={{ padding: '8px 16px', borderBottom: '1px solid var(--mi-border)' }}>
          <Group gap={6}>
            <UnstyledButton
              onClick={() => setActiveCategory(null)}
              style={{
                padding: '4px 12px', borderRadius: 'var(--mi-radius-full)', fontSize: 12, fontWeight: 600,
                backgroundColor: !activeCategory ? 'var(--mi-primary)' : 'transparent',
                color: !activeCategory ? '#fff' : 'var(--mi-text-secondary)',
                transition: 'all 0.1s ease',
              }}
            >
              All ({allResults.length})
            </UnstyledButton>
            {Object.entries(categoryCounts).map(([type, count]) => {
              const cat = CATEGORY_LABELS[type];
              if (!cat) return null;
              const isActive = activeCategory === type;
              return (
                <UnstyledButton
                  key={type}
                  onClick={() => setActiveCategory(isActive ? null : type)}
                  style={{
                    padding: '4px 12px', borderRadius: 'var(--mi-radius-full)', fontSize: 12, fontWeight: 600,
                    backgroundColor: isActive ? `var(--mantine-color-${cat.color}-filled, var(--mi-primary))` : 'transparent',
                    color: isActive ? '#fff' : 'var(--mi-text-secondary)',
                    transition: 'all 0.1s ease',
                  }}
                >
                  {cat.label} ({count})
                </UnstyledButton>
              );
            })}
          </Group>
        </Box>
      )}

      {/* Quick Stats Bar (when no query) */}
      {!query.trim() && dashStats && (
        <Box style={{ padding: '10px 16px', borderBottom: '1px solid var(--mi-border)' }}>
          <Group gap={16}>
            {[
              { icon: IconFile, label: 'Charts', value: String(dashStats.total_charts ?? 0), color: 'blue' },
              { icon: IconPercentage, label: 'Success', value: formatPercentValue(dashStats.success_rate ?? 0), color: 'green' },
              { icon: IconClock, label: 'Avg Time', value: formatDuration(dashStats.avg_processing_seconds ?? 0), color: 'orange' },
            ].map((stat) => (
              <Group key={stat.label} gap={6}>
                <stat.icon size={13} color={`var(--mantine-color-${stat.color}-5, var(--mi-text-muted))`} />
                <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>{stat.label}:</Text>
                <Text size="xs" fw={700} style={{ color: 'var(--mi-text)' }}>{stat.value}</Text>
              </Group>
            ))}
          </Group>
        </Box>
      )}

      {/* Results */}
      <ScrollArea.Autosize mah={480} type="auto">
        <Box style={{ padding: '8px' }}>
          {/* Recent Searches */}
          <AnimatePresence mode="wait">
            {showRecent && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                <Text size="xs" fw={600} c="dimmed" px={12} py={6} tt="uppercase" style={{ letterSpacing: '0.05em' }}>
                  Recent Searches
                </Text>
                {recentSearches.map((s) => (
                  <UnstyledButton
                    key={s} onClick={() => setQuery(s)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10, width: '100%', padding: '8px 12px',
                      borderRadius: 'var(--mi-radius-md)', color: 'var(--mi-text-secondary)', transition: 'background var(--mi-transition-fast)',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--mi-surface-hover)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
                  >
                    <IconClock size={14} stroke={1.5} />
                    <Text size="sm">{s}</Text>
                  </UnstyledButton>
                ))}
                <Divider my={8} color="var(--mi-border)" />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Quick Actions */}
          {!query.trim() && (
            <>
              <Text size="xs" fw={600} c="dimmed" px={12} py={6} tt="uppercase" style={{ letterSpacing: '0.05em' }}>
                Quick Actions
              </Text>
              {quickActions.map((item, idx) => (
                <SpotlightResultItem key={item.id} item={item} isSelected={idx === selectedIdx}
                  onSelect={item.action} onHover={() => setSelectedIdx(idx)} />
              ))}
            </>
          )}

          {/* Search Results */}
          {hasResults && (
            <AnimatePresence mode="wait">
              <motion.div key={`${query}-${activeCategory}`} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                {groupResultsByCategory(results).map(([category, items]) => (
                  <Box key={category} mb={4}>
                    <Group gap={6} px={12} py={6}>
                      <Text size="xs" fw={600} c="dimmed" tt="uppercase" style={{ letterSpacing: '0.05em' }}>
                        {CATEGORY_LABELS[category]?.label ?? category}
                      </Text>
                      <Badge size="xs" variant="light" color={CATEGORY_LABELS[category]?.color ?? 'gray'} radius="sm">
                        {items.length}
                      </Badge>
                    </Group>
                    {items.map((item) => {
                      const globalIdx = results.indexOf(item);
                      return (
                        <SpotlightResultItem key={item.id} item={item} isSelected={globalIdx === selectedIdx}
                          onSelect={item.action} onHover={() => setSelectedIdx(globalIdx)} />
                      );
                    })}
                  </Box>
                ))}
              </motion.div>
            </AnimatePresence>
          )}

          {/* No Results */}
          {noResults && (
            <Box py={48} style={{ textAlign: 'center' }}>
              <IconSearch size={40} stroke={1.2} color="var(--mi-text-muted)" style={{ opacity: 0.4 }} />
              <Text size="sm" c="dimmed" mt={16} fw={500}>No results for "{query}"</Text>
              <Text size="xs" c="dimmed" mt={6}>Try searching by chart name, HCC code, status, or action</Text>
            </Box>
          )}
        </Box>
      </ScrollArea.Autosize>

      {/* Footer */}
      <Box style={{ padding: '8px 16px', borderTop: '1px solid var(--mi-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Group gap={16}>
          <Group gap={4}>
            <Kbd size="xs">↑↓</Kbd>
            <Text size="xs" c="dimmed">Navigate</Text>
          </Group>
          <Group gap={4}>
            <Kbd size="xs"><IconCornerDownLeft size={10} /></Kbd>
            <Text size="xs" c="dimmed">Open</Text>
          </Group>
          <Group gap={4}>
            <Kbd size="xs">Esc</Kbd>
            <Text size="xs" c="dimmed">Close</Text>
          </Group>
        </Group>
        <Text size="xs" c="dimmed" style={{ fontVariantNumeric: 'tabular-nums' }}>
          {query.trim() ? `${results.length} results` : `${chartsData?.total ?? 0} charts indexed`}
        </Text>
      </Box>
    </Modal>
  );
}

/* ========================================================================= */
/* Result Item (Enhanced)                                                    */
/* ========================================================================= */
interface SpotlightResultItemProps {
  item: SearchResult;
  isSelected: boolean;
  onSelect: () => void;
  onHover: () => void;
}

function SpotlightResultItem({ item, isSelected, onSelect, onHover }: SpotlightResultItemProps) {
  const Icon = item.icon;

  return (
    <UnstyledButton
      onClick={onSelect}
      onMouseEnter={onHover}
      style={{
        display: 'flex', alignItems: 'center', gap: 10, width: '100%', padding: '6px 10px',
        borderRadius: 'var(--mi-radius-md)', backgroundColor: isSelected ? 'var(--mi-surface-hover)' : 'transparent',
        transition: 'background var(--mi-transition-fast)', border: isSelected ? '1px solid var(--mi-border)' : '1px solid transparent',
      }}
    >
      <ThemeIcon size={28} radius="md" variant="light" color={item.iconColor} style={{ flexShrink: 0 }}>
        <Icon size={14} stroke={1.8} />
      </ThemeIcon>
      <Box style={{ flex: 1, minWidth: 0 }}>
        <Group gap={6} wrap="nowrap">
          <Text size="xs" fw={600} truncate="end" style={{ color: 'var(--mi-text)' }}>{item.title}</Text>
          {item.meta?.status && (
            <Badge size="xs" variant="light" color={getStatusColor(String(item.meta.status))} radius="sm" styles={{ root: { fontSize: 9 } }}>
              {String(item.meta.status)}
            </Badge>
          )}
          {/* Inline metadata */}
          {item.meta && item.type !== 'action' && (
            <>
              {item.meta.raf != null && (
                <Text size="xs" fw={600} style={{ color: '#8B5CF6', fontSize: 10, flexShrink: 0 }}>RAF {item.meta.raf}</Text>
              )}
              {item.meta.raf_weight != null && (
                <Text size="xs" fw={600} style={{ color: '#8B5CF6', fontSize: 10, flexShrink: 0 }}>Wt {item.meta.raf_weight}</Text>
              )}
              {item.meta.hccs != null && Number(item.meta.hccs) > 0 && (
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10, flexShrink: 0 }}>{item.meta.hccs} HCCs</Text>
              )}
            </>
          )}
        </Group>
        <Text size="xs" c="dimmed" truncate="end" style={{ fontSize: 11 }}>{item.subtitle}</Text>
      </Box>
      {isSelected && (
        <IconArrowRight size={14} stroke={1.5} color="var(--mi-text-muted)" style={{ flexShrink: 0 }} />
      )}
    </UnstyledButton>
  );
}

/* ========================================================================= */
/* Helpers                                                                   */
/* ========================================================================= */
function groupResultsByCategory(results: SearchResult[]): [string, SearchResult[]][] {
  const grouped = new Map<string, SearchResult[]>();
  for (const result of results) {
    const existing = grouped.get(result.type) ?? [];
    existing.push(result);
    grouped.set(result.type, existing);
  }
  return Array.from(grouped.entries());
}
