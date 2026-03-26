import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Tabs,
  Text,
  Badge,
  Skeleton,
  Group,
  Loader,
} from '@mantine/core';
import {
  IconShieldCheck,
  IconStethoscope,
  IconHeartRateMonitor,
  IconReportMedical,
} from '@tabler/icons-react';
import { motion } from 'framer-motion';
import { useChart } from '../../hooks/useChart';
import { useChartStore } from '../../stores/chartStore';
import { usePDFStore } from '../../stores/pdfStore';
import { ViewerToolbar } from './ViewerToolbar';
import { PDFViewer } from '../pdf/PDFViewer';
import { getChartPdfUrl } from '../../utils/chartFiles';
import { HCCPackPanel } from '../hcc/HCCPackPanel';
import { DiagnosesPanel } from '../clinical/DiagnosesPanel';
import { HEDISPanel } from '../hedis/HEDISPanel';
import { ClinicalPanel } from '../clinical/ClinicalPanel';

/* ========================================================================= */
/* Tab definitions                                                            */
/* ========================================================================= */
interface TabDef {
  value: string;
  label: string;
  icon: typeof IconShieldCheck;
  color: string;
}

const TABS: TabDef[] = [
  { value: 'hcc',       label: 'HCC Pack',      icon: IconShieldCheck,      color: '#3B82F6' },
  { value: 'diagnoses', label: 'Diagnoses',      icon: IconStethoscope,      color: '#8B5CF6' },
  { value: 'hedis',     label: 'Care Gaps',      icon: IconHeartRateMonitor, color: '#10B981' },
  { value: 'clinical',  label: 'Clinical Intel',  icon: IconReportMedical,    color: '#F59E0B' },
];

/* ========================================================================= */
/* Placeholder tab content panels (will be replaced by real components)       */
/* ========================================================================= */
function TabPlaceholder({ tab }: { tab: TabDef }) {
  const Icon = tab.icon;
  return (
    <Box
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        minHeight: 300,
        gap: 16,
        padding: 40,
      }}
    >
      <Box
        style={{
          width: 56,
          height: 56,
          borderRadius: 'var(--mi-radius-lg)',
          background: `${tab.color}15`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Icon size={28} color={tab.color} stroke={1.5} />
      </Box>
      <Text size="lg" fw={600} style={{ color: 'var(--mi-text)' }}>
        {tab.label}
      </Text>
      <Text size="sm" c="dimmed" ta="center" maw={280}>
        {tab.label} panel content will be rendered here. Select a chart to begin.
      </Text>
    </Box>
  );
}

/* ========================================================================= */
/* Resizable Split Pane                                                      */
/* ========================================================================= */
interface SplitPaneProps {
  leftPanel: React.ReactNode;
  rightPanel: React.ReactNode;
  defaultSplit?: number;
  minLeft?: number;
  minRight?: number;
}

function SplitPane({
  leftPanel,
  rightPanel,
  defaultSplit = 45,
  minLeft = 20,
  minRight = 25,
}: SplitPaneProps) {
  const [splitPercent, setSplitPercent] = useState(defaultSplit);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      let percent = (x / rect.width) * 100;
      percent = Math.max(minLeft, Math.min(100 - minRight, percent));
      setSplitPercent(percent);
    };

    const handleMouseUp = () => {
      if (isDragging.current) {
        isDragging.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [minLeft, minRight]);

  return (
    <Box
      ref={containerRef}
      style={{
        display: 'flex',
        height: '100%',
        width: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Left panel */}
      <Box
        style={{
          width: `${splitPercent}%`,
          height: '100%',
          overflow: 'hidden',
          flexShrink: 0,
        }}
      >
        {leftPanel}
      </Box>

      {/* Drag handle */}
      <Box
        onMouseDown={handleMouseDown}
        style={{
          width: 6,
          flexShrink: 0,
          cursor: 'col-resize',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 50,
        }}
      >
        {/* Visible line */}
        <Box
          style={{
            width: 2,
            height: '100%',
            backgroundColor: 'var(--mi-border)',
            transition: 'background-color var(--mi-transition-fast)',
            borderRadius: 1,
          }}
        />
        {/* Hover/drag indicator */}
        <Box
          style={{
            position: 'absolute',
            width: 6,
            height: 40,
            borderRadius: 'var(--mi-radius-full)',
            backgroundColor: 'var(--mi-border)',
            transition: 'all var(--mi-transition-fast)',
            opacity: 0.6,
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget as HTMLElement;
            el.style.backgroundColor = 'var(--mi-primary)';
            el.style.opacity = '1';
            el.style.width = '4px';
            /* Also brighten the line */
            const line = el.previousElementSibling as HTMLElement;
            if (line) line.style.backgroundColor = 'var(--mi-primary)';
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget as HTMLElement;
            el.style.backgroundColor = 'var(--mi-border)';
            el.style.opacity = '0.6';
            el.style.width = '6px';
            const line = el.previousElementSibling as HTMLElement;
            if (line) line.style.backgroundColor = 'var(--mi-border)';
          }}
        />
      </Box>

      {/* Right panel */}
      <Box
        style={{
          flex: 1,
          height: '100%',
          overflow: 'hidden',
          minWidth: 0,
        }}
      >
        {rightPanel}
      </Box>
    </Box>
  );
}

/* ========================================================================= */
/* Loading Skeleton for the viewer                                            */
/* ========================================================================= */
function ViewerSkeleton() {
  return (
    <Box style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Toolbar skeleton */}
      <Box
        style={{
          height: 52,
          padding: '0 16px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          borderBottom: '1px solid var(--mi-border)',
          background: 'var(--mi-surface)',
        }}
      >
        <Skeleton width={34} height={34} radius="md" />
        <Skeleton width={100} height={26} radius="md" />
        <Skeleton width={80} height={22} radius="md" />
        <Box style={{ flex: 1 }} />
        <Skeleton width={34} height={34} radius="md" />
        <Skeleton width={34} height={34} radius="md" />
      </Box>

      {/* Content skeleton */}
      <Box style={{ flex: 1, display: 'flex' }}>
        {/* Left panel skeleton */}
        <Box style={{ width: '45%', padding: 16 }}>
          <Group gap={8} mb={16}>
            {TABS.map((t) => (
              <Skeleton key={t.value} width={70} height={32} radius="md" />
            ))}
          </Group>
          <Skeleton height={200} radius="md" mb={12} />
          <Skeleton height={120} radius="md" mb={12} />
          <Skeleton height={160} radius="md" />
        </Box>

        {/* Divider */}
        <Box style={{ width: 2, background: 'var(--mi-border)' }} />

        {/* Right panel skeleton */}
        <Box style={{ flex: 1, padding: 16 }}>
          <Skeleton height={40} radius="md" mb={12} />
          <Skeleton height="calc(100% - 56px)" radius="md" />
        </Box>
      </Box>
    </Box>
  );
}

/* ========================================================================= */
/* Main ChartViewer Component                                                 */
/* ========================================================================= */
export function ChartViewer() {
  const { chartId } = useParams<{ chartId: string }>();
  const navigate = useNavigate();
  const { setActiveChart, activeTab, setActiveTab } = useChartStore();
  const { clearHighlights, clearSearchMatches, setCurrentPage } = usePDFStore();

  /* Set active chart in store */
  useEffect(() => {
    if (chartId) {
      setActiveChart(chartId);
    }
    return () => {
      setActiveChart(null);
      clearHighlights();
      clearSearchMatches();
    };
  }, [chartId, setActiveChart, clearHighlights, clearSearchMatches]);

  /* Fetch chart data */
  const { data: chart, isLoading, isError } = useChart(chartId ?? null);
  const pdfUrl = useMemo(() => (chartId ? getChartPdfUrl(chartId, chart) : ''), [chartId, chart]);

  /* Map activeTab index to tab value */
  const activeTabValue = useMemo(() => {
    return TABS[activeTab]?.value ?? 'hcc';
  }, [activeTab]);

  /* Handle tab change */
  const handleTabChange = useCallback(
    (value: string | null) => {
      if (!value) return;
      const idx = TABS.findIndex((t) => t.value === value);
      if (idx >= 0) setActiveTab(idx);
    },
    [setActiveTab],
  );

  /* Error state */
  if (isError || (!isLoading && !chart && chartId)) {
    return (
      <Box
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: 'calc(100vh - 40px)',
          gap: 16,
          padding: 40,
        }}
      >
        <Text size="xl" fw={700} style={{ color: 'var(--mi-error)' }}>
          Chart Not Found
        </Text>
        <Text size="sm" c="dimmed" ta="center" maw={400}>
          The chart with ID{' '}
          <Text component="span" fw={600} style={{ fontFamily: 'monospace' }}>
            {chartId}
          </Text>{' '}
          could not be found or there was an error loading it.
        </Text>
        <Box
          component="button"
          onClick={() => navigate('/')}
          style={{
            marginTop: 8,
            padding: '8px 20px',
            borderRadius: 'var(--mi-radius-md)',
            background: 'var(--mi-primary)',
            color: '#FFFFFF',
            border: 'none',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: 14,
            transition: 'all var(--mi-transition-fast)',
          }}
          onMouseEnter={(e: React.MouseEvent<HTMLButtonElement>) => {
            e.currentTarget.style.background = 'var(--mi-primary-hover)';
          }}
          onMouseLeave={(e: React.MouseEvent<HTMLButtonElement>) => {
            e.currentTarget.style.background = 'var(--mi-primary)';
          }}
        >
          Back to Charts
        </Box>
      </Box>
    );
  }

  /* Loading state */
  if (isLoading && !chart) {
    return <ViewerSkeleton />;
  }

  /* ===================================================================== */
  /* Left Panel: Tabbed clinical data                                       */
  /* ===================================================================== */
  const leftPanel = (
    <Box
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: 'var(--mi-surface)',
        overflow: 'hidden',
      }}
    >
      <Tabs
        value={activeTabValue}
        onChange={handleTabChange}
        variant="default"
        keepMounted={false}
        style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
        styles={{
          root: { height: '100%', display: 'flex', flexDirection: 'column' },
          panel: { flex: 1, overflow: 'auto', padding: 0 },
        }}
      >
        {/* Tab headers */}
        <Tabs.List
          style={{
            padding: '4px 8px 0',
            borderBottom: '1px solid var(--mi-border)',
            background: 'var(--mi-surface)',
            flexShrink: 0,
            gap: 0,
            flexWrap: 'nowrap',
            overflowX: 'auto',
            overflowY: 'hidden',
            scrollbarWidth: 'none',
          }}
        >
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTabValue === tab.value;
            return (
              <Tabs.Tab
                key={tab.value}
                value={tab.value}
                leftSection={
                  <Icon
                    size={14}
                    stroke={isActive ? 2 : 1.5}
                    style={{
                      color: isActive ? tab.color : 'var(--mi-text-muted)',
                      transition: 'color var(--mi-transition-fast)',
                    }}
                  />
                }
                style={{
                  fontSize: 11,
                  fontWeight: isActive ? 700 : 500,
                  color: isActive ? 'var(--mi-text)' : 'var(--mi-text-muted)',
                  borderBottom: isActive ? `2px solid ${tab.color}` : '2px solid transparent',
                  padding: '6px 8px',
                  transition: 'all var(--mi-transition-fast)',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}
              >
                {tab.label}
              </Tabs.Tab>
            );
          })}
        </Tabs.List>

        {/* Tab panels */}
        {TABS.map((tab) => (
          <Tabs.Panel key={tab.value} value={tab.value}>
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.15 }}
              style={{ height: '100%' }}
            >
              {tab.value === 'hcc' ? (
                <HCCPackPanel />
              ) : tab.value === 'diagnoses' ? (
                <DiagnosesPanel />
              ) : tab.value === 'hedis' ? (
                <HEDISPanel />
              ) : tab.value === 'clinical' ? (
                <ClinicalPanel />
              ) : (
                <TabPlaceholder tab={tab} />
              )}
            </motion.div>
          </Tabs.Panel>
        ))}
      </Tabs>
    </Box>
  );

  /* ===================================================================== */
  /* Right Panel: PDF Viewer                                                */
  /* ===================================================================== */
  const rightPanel = (
    <Box style={{ height: '100%', overflow: 'hidden' }}>
      <PDFViewer pdfUrl={pdfUrl} />
    </Box>
  );

  return (
    <Box
      style={{
        height: 'calc(100vh - 40px)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Top toolbar */}
      <ViewerToolbar
        chart={chart}
        isLoading={isLoading}
        chartId={chartId ?? ''}
      />

      {/* Split layout */}
      <Box style={{ flex: 1, overflow: 'hidden' }}>
        <SplitPane
          leftPanel={leftPanel}
          rightPanel={rightPanel}
          defaultSplit={35}
          minLeft={20}
          minRight={30}
        />
      </Box>
    </Box>
  );
}
