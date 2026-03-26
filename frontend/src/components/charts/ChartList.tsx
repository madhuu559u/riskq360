import { useState, useMemo, useEffect, useCallback } from 'react';
import {
  Box,
  TextInput,
  Group,
  Text,
  Badge,
  SimpleGrid,
  Skeleton,
  Stack,
  ActionIcon,
  Tooltip,
  SegmentedControl,
  Select,
  Affix,
  Button,
  Checkbox,
  Collapse,
} from '@mantine/core';
import {
  IconSearch,
  IconPlus,
  IconLayoutGrid,
  IconLayoutList,
  IconCloudUpload,
  IconRefresh,
  IconFilter,
  IconX,
  IconAdjustments,
  IconChevronDown,
  IconChevronUp,
} from '@tabler/icons-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCharts } from '../../hooks/useChart';
import { ChartCard } from './ChartCard';
import { ChartUpload } from './ChartUpload';
import { searchItems } from '../../utils/search';
import type { Chart } from '../../types/chart';

/* ========================================================================= */
/* Empty State                                                               */
/* ========================================================================= */
function EmptyState({ onUpload }: { onUpload: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
    >
      <Stack align="center" gap={16} py={60}>
        <Box
          style={{
            width: 80,
            height: 80,
            borderRadius: 'var(--mi-radius-xl)',
            background: 'linear-gradient(135deg, color-mix(in srgb, var(--mi-primary) 10%, transparent), color-mix(in srgb, var(--mi-accent) 10%, transparent))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <IconCloudUpload size={36} stroke={1.2} color="var(--mi-primary)" />
        </Box>
        <Box ta="center">
          <Text size="lg" fw={700} style={{ color: 'var(--mi-text)' }}>
            No charts yet
          </Text>
          <Text size="sm" c="dimmed" mt={6} maw={360}>
            Upload a medical chart to start AI-powered risk adjustment and quality analysis.
          </Text>
        </Box>
        <Button
          size="md"
          radius="xl"
          leftSection={<IconPlus size={16} />}
          onClick={onUpload}
          style={{
            background: 'linear-gradient(135deg, var(--mi-primary), var(--mi-accent))',
            border: 'none',
            fontWeight: 700,
          }}
        >
          Upload Chart
        </Button>
      </Stack>
    </motion.div>
  );
}

/* ========================================================================= */
/* No Results                                                                */
/* ========================================================================= */
function NoResultsState({ onClear }: { onClear: () => void }) {
  return (
    <Stack align="center" gap={12} py={48}>
      <IconSearch size={32} stroke={1.2} color="var(--mi-text-muted)" style={{ opacity: 0.4 }} />
      <Text size="sm" fw={600} style={{ color: 'var(--mi-text)' }}>
        No matching charts
      </Text>
      <Button
        variant="light"
        radius="md"
        size="xs"
        leftSection={<IconX size={12} />}
        onClick={onClear}
      >
        Clear filters
      </Button>
    </Stack>
  );
}

/* ========================================================================= */
/* Main Chart List                                                           */
/* ========================================================================= */
export function ChartList() {
  const [uploadOpen, setUploadOpen] = useState(false);
  const [viewMode, setViewMode] = useState<string>('grid');
  const [filtersOpen, setFiltersOpen] = useState(false);

  // Search / filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [hccFilter, setHccFilter] = useState('');
  const [dxFilter, setDxFilter] = useState('');
  const [highRiskOnly, setHighRiskOnly] = useState(false);
  const [hasGapsOnly, setHasGapsOnly] = useState(false);

  const { data: chartsData, isLoading, refetch } = useCharts();

  useEffect(() => {
    const handler = () => setUploadOpen(true);
    window.addEventListener('medinsight:trigger-upload', handler);
    return () => window.removeEventListener('medinsight:trigger-upload', handler);
  }, []);

  const activeFilterCount = useMemo(() => {
    let n = 0;
    if (statusFilter) n++;
    if (hccFilter.trim()) n++;
    if (dxFilter.trim()) n++;
    if (highRiskOnly) n++;
    if (hasGapsOnly) n++;
    return n;
  }, [statusFilter, hccFilter, dxFilter, highRiskOnly, hasGapsOnly]);

  const filteredCharts = useMemo(() => {
    let charts = chartsData?.charts ?? [];

    // Status filter
    if (statusFilter) {
      charts = charts.filter((c) => c.status === statusFilter);
    }

    // Text search — filename, chart_id, patient name, status
    if (searchQuery.trim()) {
      charts = searchItems(charts, searchQuery, ['chart_id', 'filename', 'patient_name', 'status']);
    }

    // HCC code filter — match if any hcc_detail code contains the search term
    if (hccFilter.trim()) {
      const q = hccFilter.trim().toUpperCase();
      charts = charts.filter((c) => {
        const details = c.raf_summary?.hcc_details ?? [];
        return details.some((d) => d.hcc_code.toUpperCase().includes(q));
      });
    }

    // Diagnosis code filter — not available on list data, but we filter RAF hcc_details
    if (dxFilter.trim()) {
      const q = dxFilter.trim().toUpperCase();
      charts = charts.filter((c) => {
        const details = c.raf_summary?.hcc_details ?? [];
        return details.some((d) =>
          d.hcc_code.toUpperCase().includes(q) ||
          d.hcc_description.toUpperCase().includes(q)
        );
      });
    }

    // High risk: RAF >= 2.0
    if (highRiskOnly) {
      charts = charts.filter((c) => (c.raf_summary?.total_raf_score ?? 0) >= 2.0);
    }

    // Has HEDIS gaps
    if (hasGapsOnly) {
      charts = charts.filter((c) => (c.hedis_summary?.gap_count ?? 0) > 0);
    }

    return charts;
  }, [chartsData, searchQuery, statusFilter, hccFilter, dxFilter, highRiskOnly, hasGapsOnly]);

  const clearAll = useCallback(() => {
    setSearchQuery('');
    setStatusFilter(null);
    setHccFilter('');
    setDxFilter('');
    setHighRiskOnly(false);
    setHasGapsOnly(false);
  }, []);

  const statusOptions = useMemo(() => {
    const statuses = new Set((chartsData?.charts ?? []).map((c) => c.status));
    return Array.from(statuses).map((s) => ({
      value: s,
      label: s.charAt(0).toUpperCase() + s.slice(1),
    }));
  }, [chartsData]);

  const inputStyles = {
    input: {
      backgroundColor: 'var(--mi-surface)',
      borderColor: 'var(--mi-border)',
      color: 'var(--mi-text)',
      fontSize: 13,
    },
  };

  return (
    <Box>
      {/* Header */}
      <Box
        style={{
          padding: '20px 0 16px',
          borderBottom: '1px solid var(--mi-border)',
          background: 'var(--mi-background)',
        }}
      >
        <Box className="content-container">
          <Group justify="space-between" align="center" mb={14}>
            <Box>
              <Text fw={700} style={{ color: 'var(--mi-text)', fontSize: 22, letterSpacing: '-0.02em' }}>
                Charts
              </Text>
              <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>
                {chartsData?.total ?? 0} total
              </Text>
            </Box>
            <Group gap={8}>
              <Tooltip label="Refresh">
                <ActionIcon size={32} radius="md" variant="subtle" color="gray" onClick={() => refetch()}>
                  <IconRefresh size={16} stroke={1.8} />
                </ActionIcon>
              </Tooltip>
              <Button
                size="xs"
                radius="xl"
                leftSection={<IconPlus size={14} />}
                onClick={() => setUploadOpen(true)}
                style={{
                  background: 'linear-gradient(135deg, var(--mi-primary), var(--mi-accent))',
                  border: 'none',
                  fontWeight: 700,
                }}
              >
                Upload
              </Button>
            </Group>
          </Group>

          {/* Search bar + filter toggle */}
          <Group gap={8} align="center">
            <TextInput
              placeholder="Search charts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.currentTarget.value)}
              leftSection={<IconSearch size={14} stroke={1.8} />}
              rightSection={
                searchQuery ? (
                  <ActionIcon size="xs" variant="subtle" color="gray" onClick={() => setSearchQuery('')} radius="xl">
                    <IconX size={12} />
                  </ActionIcon>
                ) : null
              }
              radius="md"
              size="xs"
              style={{ flex: 1, maxWidth: 320 }}
              styles={inputStyles}
            />

            <Select
              placeholder="Status"
              value={statusFilter}
              onChange={setStatusFilter}
              data={statusOptions}
              clearable
              radius="md"
              size="xs"
              leftSection={<IconFilter size={12} stroke={1.8} />}
              w={130}
              styles={inputStyles}
            />

            <Tooltip label="Advanced filters">
              <ActionIcon
                size={30}
                radius="md"
                variant={filtersOpen || activeFilterCount > 0 ? 'light' : 'subtle'}
                color={activeFilterCount > 0 ? 'blue' : 'gray'}
                onClick={() => setFiltersOpen((o) => !o)}
              >
                <IconAdjustments size={15} stroke={1.8} />
              </ActionIcon>
            </Tooltip>

            {activeFilterCount > 0 && (
              <Badge
                size="xs"
                variant="filled"
                color="blue"
                radius="xl"
                rightSection={
                  <ActionIcon size={12} variant="transparent" color="white" onClick={clearAll}>
                    <IconX size={8} />
                  </ActionIcon>
                }
                style={{ cursor: 'pointer' }}
              >
                {activeFilterCount} filter{activeFilterCount !== 1 ? 's' : ''}
              </Badge>
            )}

            <Box style={{ marginLeft: 'auto' }}>
              <Group gap={6}>
                <SegmentedControl
                  value={viewMode}
                  onChange={setViewMode}
                  size="xs"
                  radius="md"
                  data={[
                    { value: 'grid', label: <IconLayoutGrid size={13} /> },
                    { value: 'list', label: <IconLayoutList size={13} /> },
                  ]}
                  styles={{
                    root: { backgroundColor: 'var(--mi-surface)', borderColor: 'var(--mi-border)' },
                  }}
                />
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', whiteSpace: 'nowrap', fontSize: 11 }}>
                  {filteredCharts.length}
                </Text>
              </Group>
            </Box>
          </Group>

          {/* Advanced filters collapsible */}
          <Collapse in={filtersOpen}>
            <Box
              mt={10}
              style={{
                padding: '10px 12px',
                borderRadius: 8,
                backgroundColor: 'var(--mi-surface)',
                border: '1px solid var(--mi-border)',
              }}
            >
              <Group gap={10} wrap="wrap" align="flex-end">
                <TextInput
                  label="HCC Code"
                  placeholder="e.g. HCC 18"
                  value={hccFilter}
                  onChange={(e) => setHccFilter(e.currentTarget.value)}
                  size="xs"
                  radius="md"
                  w={130}
                  styles={inputStyles}
                />
                <TextInput
                  label="Diagnosis"
                  placeholder="e.g. Diabetes"
                  value={dxFilter}
                  onChange={(e) => setDxFilter(e.currentTarget.value)}
                  size="xs"
                  radius="md"
                  w={150}
                  styles={inputStyles}
                />
                <Checkbox
                  label="High risk (RAF >= 2.0)"
                  checked={highRiskOnly}
                  onChange={(e) => setHighRiskOnly(e.currentTarget.checked)}
                  size="xs"
                  styles={{ label: { color: 'var(--mi-text-secondary)', fontSize: 12 } }}
                />
                <Checkbox
                  label="Has HEDIS gaps"
                  checked={hasGapsOnly}
                  onChange={(e) => setHasGapsOnly(e.currentTarget.checked)}
                  size="xs"
                  styles={{ label: { color: 'var(--mi-text-secondary)', fontSize: 12 } }}
                />
                {activeFilterCount > 0 && (
                  <Button
                    variant="subtle"
                    size="xs"
                    radius="md"
                    color="gray"
                    leftSection={<IconX size={12} />}
                    onClick={clearAll}
                    style={{ fontSize: 11 }}
                  >
                    Clear all
                  </Button>
                )}
              </Group>
            </Box>
          </Collapse>
        </Box>
      </Box>

      {/* Chart grid */}
      <Box className="content-container" py={16}>
        {isLoading ? (
          <SimpleGrid
            cols={viewMode === 'grid' ? { base: 1, sm: 2, lg: 3, xl: 4 } : { base: 1 }}
            spacing="sm"
          >
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} height={viewMode === 'grid' ? 72 : 56} radius="md" />
            ))}
          </SimpleGrid>
        ) : filteredCharts.length === 0 && (chartsData?.charts ?? []).length === 0 ? (
          <EmptyState onUpload={() => setUploadOpen(true)} />
        ) : filteredCharts.length === 0 ? (
          <NoResultsState onClear={clearAll} />
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={`${viewMode}-${statusFilter}-${searchQuery}-${hccFilter}-${dxFilter}-${highRiskOnly}-${hasGapsOnly}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <SimpleGrid
                cols={viewMode === 'grid' ? { base: 1, sm: 2, lg: 3, xl: 4 } : { base: 1 }}
                spacing="sm"
              >
                {filteredCharts.map((chart, idx) => (
                  <ChartCard key={chart.chart_id || `chart-${idx}`} chart={chart} index={idx} />
                ))}
              </SimpleGrid>
            </motion.div>
          </AnimatePresence>
        )}
      </Box>

      {/* FAB */}
      <Affix position={{ bottom: 24, right: 24 }} zIndex={250}>
        <motion.div
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4, duration: 0.25 }}
        >
          <Tooltip label="Upload chart (Ctrl+U)" position="left">
            <ActionIcon
              size={48}
              radius="xl"
              onClick={() => setUploadOpen(true)}
              style={{
                background: 'linear-gradient(135deg, var(--mi-primary), var(--mi-accent))',
                border: 'none',
                boxShadow: '0 4px 16px color-mix(in srgb, var(--mi-primary) 30%, transparent)',
                color: '#FFFFFF',
                transition: 'all var(--mi-transition-fast)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'scale(1.08)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)';
              }}
            >
              <IconPlus size={22} stroke={2.5} />
            </ActionIcon>
          </Tooltip>
        </motion.div>
      </Affix>

      <ChartUpload opened={uploadOpen} onClose={() => setUploadOpen(false)} />
    </Box>
  );
}
