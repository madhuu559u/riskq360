import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Group,
  Text,
  Badge,
  ActionIcon,
  Tooltip,
  Menu,
  Loader,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import {
  IconArrowLeft,
  IconDownload,
  IconRefresh,
  IconTrash,
  IconDotsVertical,
  IconClipboard,
  IconExternalLink,
  IconMaximize,
  IconMinimize,
} from '@tabler/icons-react';
import { motion } from 'framer-motion';
import type { Chart } from '../../types/chart';
import { useProcessChart, useDeleteChart } from '../../hooks/useChart';
import { getChartFileName, getChartPdfUrl } from '../../utils/chartFiles';
import { getStatusColor } from '../../utils/colors';
import { formatChartId, formatDuration, formatRelativeTime } from '../../utils/formatters';

/* ========================================================================= */
/* Props                                                                      */
/* ========================================================================= */
interface ViewerToolbarProps {
  chart: Chart | undefined;
  isLoading: boolean;
  chartId: string;
}

/* ========================================================================= */
/* Status pulse component for processing status                               */
/* ========================================================================= */
function StatusPulse({ color }: { color: string }) {
  return (
    <Box
      style={{
        position: 'relative',
        width: 8,
        height: 8,
        flexShrink: 0,
      }}
    >
      <Box
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          backgroundColor: color,
        }}
      />
      <Box
        style={{
          position: 'absolute',
          inset: -2,
          borderRadius: '50%',
          backgroundColor: color,
          opacity: 0.4,
          animation: 'mi-pulse-glow 2s infinite',
        }}
      />
    </Box>
  );
}

/* ========================================================================= */
/* Component                                                                  */
/* ========================================================================= */
export function ViewerToolbar({ chart, isLoading, chartId }: ViewerToolbarProps) {
  const navigate = useNavigate();
  const processChart = useProcessChart();
  const deleteChart = useDeleteChart();

  const [isFullscreen, setIsFullscreen] = useState(false);
  const isProcessing = chart?.status === 'processing' || chart?.status === 'running';
  const statusColor = chart ? getStatusColor(chart.status) : 'gray';
  const pdfUrl = getChartPdfUrl(chartId, chart);
  const reprocessDisabled = true;

  /* Toggle fullscreen */
  const handleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  }, []);

  /* Copy chart ID to clipboard */
  const handleCopyId = useCallback(() => {
    navigator.clipboard.writeText(chartId);
  }, [chartId]);

  /* Re-process chart */
  const handleReprocess = useCallback(() => {
    modals.openConfirmModal({
      title: 'Re-process Chart',
      children: (
        <Text size="sm" c="dimmed">
          Are you sure you want to re-process chart{' '}
          <Text component="span" fw={600} style={{ fontFamily: 'monospace' }}>
            {formatChartId(chartId, chart?.filename)}
          </Text>
          ? This will run the full pipeline again.
        </Text>
      ),
      labels: { confirm: 'Re-process', cancel: 'Cancel' },
      confirmProps: { color: 'blue' },
      onConfirm: () => processChart.mutate(chartId),
    });
  }, [chartId, processChart]);

  /* Delete chart */
  const handleDelete = useCallback(() => {
    modals.openConfirmModal({
      title: 'Delete Chart',
      children: (
        <Text size="sm" c="dimmed">
          Are you sure you want to delete chart{' '}
          <Text component="span" fw={600} style={{ fontFamily: 'monospace' }}>
            {formatChartId(chartId, chart?.filename)}
          </Text>
          ? This action cannot be undone.
        </Text>
      ),
      labels: { confirm: 'Delete', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: () => {
        deleteChart.mutate(chartId, {
          onSuccess: () => navigate('/'),
        });
      },
    });
  }, [chartId, deleteChart, navigate]);

  /* Download PDF */
  const handleDownload = useCallback(() => {
    const cleanName = getChartFileName(chartId, chart);
    const link = document.createElement('a');
    link.href = pdfUrl;
    link.download = cleanName;
    link.click();
  }, [chartId, chart, pdfUrl]);

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <Box
        style={{
          height: 38,
          display: 'flex',
          alignItems: 'center',
          padding: '0 12px',
          background: 'var(--mi-glass-bg)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          borderBottom: '1px solid var(--mi-glass-border)',
          gap: 8,
        }}
      >
        {/* Left: Back + Chart info */}
        <Group gap={10} wrap="nowrap" style={{ flex: '0 0 auto' }}>
          <Tooltip label="Back to charts">
            <ActionIcon
              size={34}
              radius="md"
              variant="subtle"
              color="gray"
              onClick={() => navigate('/')}
              aria-label="Back to charts"
            >
              <IconArrowLeft size={18} stroke={2} />
            </ActionIcon>
          </Tooltip>

          {/* Chart ID badge */}
          <Tooltip label="Click to copy chart ID">
            <Badge
              variant="light"
              color="gray"
              size="lg"
              radius="md"
              onClick={handleCopyId}
              style={{
                cursor: 'pointer',
                fontFamily: 'monospace',
                fontSize: 12,
                fontWeight: 700,
                letterSpacing: '0.02em',
                transition: 'all var(--mi-transition-fast)',
                backgroundColor: 'var(--mi-surface)',
                borderColor: 'var(--mi-border)',
                color: 'var(--mi-text)',
                border: '1px solid var(--mi-border)',
              }}
              leftSection={<IconClipboard size={12} />}
            >
              {formatChartId(chartId, chart?.filename)}
            </Badge>
          </Tooltip>

          {/* Status badge */}
          {chart && (
            <Badge
              variant="light"
              color={statusColor}
              size="md"
              radius="md"
              leftSection={
                isProcessing ? (
                  <Loader size={10} color={statusColor} type="dots" />
                ) : (
                  <StatusPulse
                    color={
                      statusColor === 'green'
                        ? 'var(--mi-success)'
                        : statusColor === 'red'
                          ? 'var(--mi-error)'
                          : statusColor === 'yellow'
                            ? 'var(--mi-warning)'
                            : 'var(--mi-secondary)'
                    }
                  />
                )
              }
              style={{
                textTransform: 'capitalize',
                fontWeight: 600,
              }}
            >
              {chart.status}
            </Badge>
          )}

          {isLoading && <Loader size={16} color="var(--mi-primary)" type="dots" />}
        </Group>

        {/* Center: Chart metadata */}
        <Box style={{ flex: 1, display: 'flex', justifyContent: 'center', minWidth: 0 }}>
          {chart && (
            <Group gap={16} wrap="nowrap">
              {chart.pages_processed !== null && chart.pages_processed !== undefined && (
                <Text size="xs" c="dimmed">
                  <Text component="span" fw={600} style={{ color: 'var(--mi-text-secondary)' }}>
                    {chart.pages_processed}
                  </Text>{' '}
                  pages
                </Text>
              )}
              {chart.total_seconds !== null && chart.total_seconds !== undefined && (
                <Text size="xs" c="dimmed">
                  Processed in{' '}
                  <Text component="span" fw={600} style={{ color: 'var(--mi-text-secondary)' }}>
                    {formatDuration(chart.total_seconds)}
                  </Text>
                </Text>
              )}
              {chart.raf_summary && (
                <Tooltip label="Total RAF Score">
                  <Badge
                    variant="light"
                    color="blue"
                    size="md"
                    radius="md"
                    style={{
                      fontFamily: 'monospace',
                      fontWeight: 700,
                    }}
                  >
                    RAF {chart.raf_summary.total_raf_score.toFixed(3)}
                  </Badge>
                </Tooltip>
              )}
              {chart.completed_at && (
                <Text size="xs" c="dimmed">
                  {formatRelativeTime(chart.completed_at)}
                </Text>
              )}
            </Group>
          )}
        </Box>

        {/* Right: Actions */}
        <Group gap={6} wrap="nowrap" style={{ flex: '0 0 auto' }}>
          <Tooltip label={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
            <ActionIcon
              size={34}
              radius="md"
              variant="subtle"
              color="gray"
              onClick={handleFullscreen}
              aria-label="Toggle fullscreen"
            >
              {isFullscreen ? <IconMinimize size={17} stroke={1.8} /> : <IconMaximize size={17} stroke={1.8} />}
            </ActionIcon>
          </Tooltip>

          <Tooltip label="Download PDF">
            <ActionIcon
              size={34}
              radius="md"
              variant="subtle"
              color="gray"
              onClick={handleDownload}
              aria-label="Download PDF"
            >
              <IconDownload size={17} stroke={1.8} />
            </ActionIcon>
          </Tooltip>

          <Tooltip label={reprocessDisabled ? 'Reprocessing remains CLI-driven in the current hardened backend build' : 'Re-process chart'}>
            <ActionIcon
              size={34}
              radius="md"
              variant="subtle"
              color="blue"
              onClick={handleReprocess}
              loading={processChart.isPending}
              disabled={isProcessing || reprocessDisabled}
              aria-label="Re-process chart"
            >
              <IconRefresh size={17} stroke={1.8} />
            </ActionIcon>
          </Tooltip>

          <Menu
            shadow="md"
            width={180}
            position="bottom-end"
            radius="md"
            transitionProps={{ transition: 'pop-top-right', duration: 150 }}
          >
            <Menu.Target>
              <Tooltip label="More actions">
                <ActionIcon
                  size={34}
                  radius="md"
                  variant="subtle"
                  color="gray"
                  aria-label="More actions"
                >
                  <IconDotsVertical size={17} stroke={1.8} />
                </ActionIcon>
              </Tooltip>
            </Menu.Target>
            <Menu.Dropdown
              style={{
                backgroundColor: 'var(--mi-surface)',
                borderColor: 'var(--mi-border)',
              }}
            >
              <Menu.Item
                leftSection={<IconClipboard size={14} />}
                onClick={handleCopyId}
                style={{ color: 'var(--mi-text)' }}
              >
                Copy chart ID
              </Menu.Item>
              <Menu.Item
                leftSection={<IconExternalLink size={14} />}
                onClick={() => window.open(pdfUrl, '_blank', 'noopener,noreferrer')}
                style={{ color: 'var(--mi-text)' }}
              >
                Open PDF in new tab
              </Menu.Item>
              <Menu.Divider />
              <Menu.Item
                leftSection={<IconTrash size={14} />}
                color="red"
                onClick={handleDelete}
              >
                Delete chart
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>
      </Box>
    </motion.div>
  );
}
