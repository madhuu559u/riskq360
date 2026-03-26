import {
  Box,
  Text,
  Stack,
  Group,
  Badge,
  Skeleton,
  Alert,
  Button,
  Tooltip,
} from '@mantine/core';
import {
  IconClipboardCheck,
  IconAlertCircle,
  IconRefresh,
  IconCheck,
  IconX,
  IconClock,
  IconCircleCheck,
  IconCircleX,
  IconPlayerPlay,
  IconShieldCheck,
  IconHeartRateMonitor,
  IconAlertTriangle,
} from '@tabler/icons-react';
import { motion } from 'framer-motion';
import { useChartStore } from '../../stores/chartStore';
import { useAuditPack } from '../../hooks/useChart';
import type { AuditPack, PipelineLog } from '../../types/api';
import { formatDuration, formatDateTime, formatRelativeTime } from '../../utils/formatters';
import { getStatusColor, getPipelineStepColor } from '../../utils/colors';

/* -------------------------------------------------------------------------- */
/* Skeleton                                                                    */
/* -------------------------------------------------------------------------- */
function AuditSkeleton() {
  return (
    <Stack gap={16} p={16}>
      {/* Summary cards skeleton */}
      <Group gap={12}>
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} height={80} radius="md" style={{ flex: 1 }} />
        ))}
      </Group>
      {/* Timeline skeleton */}
      <Skeleton height={24} width={140} radius="md" />
      {[1, 2, 3, 4].map((i) => (
        <Box key={i} style={{ display: 'flex', gap: 12, paddingLeft: 24 }}>
          <Skeleton width={12} height={12} circle />
          <Skeleton height={60} style={{ flex: 1 }} radius="md" />
        </Box>
      ))}
    </Stack>
  );
}

/* -------------------------------------------------------------------------- */
/* Empty State                                                                 */
/* -------------------------------------------------------------------------- */
function EmptyState() {
  return (
    <Box
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 48,
        gap: 16,
      }}
    >
      <Box
        style={{
          width: 64,
          height: 64,
          borderRadius: 'var(--mi-radius-lg)',
          background: 'color-mix(in srgb, var(--mi-primary) 8%, var(--mi-surface))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <IconClipboardCheck size={32} stroke={1.2} color="var(--mi-text-muted)" />
      </Box>
      <Text size="md" fw={600} style={{ color: 'var(--mi-text)' }}>
        No Audit Data Available
      </Text>
      <Text size="sm" c="dimmed" ta="center" maw={300}>
        Audit trail data will appear here once the chart has been fully processed.
      </Text>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Status icon for pipeline step                                               */
/* -------------------------------------------------------------------------- */
function StepStatusIcon({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  if (normalized === 'completed' || normalized === 'success' || normalized === 'done') {
    return <IconCircleCheck size={16} stroke={2} color="var(--mi-success)" />;
  }
  if (normalized === 'failed' || normalized === 'error') {
    return <IconCircleX size={16} stroke={2} color="var(--mi-error)" />;
  }
  if (normalized === 'running' || normalized === 'in_progress' || normalized === 'processing') {
    return <IconPlayerPlay size={16} stroke={2} color="var(--mi-info)" />;
  }
  if (normalized === 'skipped') {
    return <IconX size={16} stroke={2} color="var(--mi-text-muted)" />;
  }
  return <IconClock size={16} stroke={2} color="var(--mi-text-muted)" />;
}

/* -------------------------------------------------------------------------- */
/* Summary Card Component                                                      */
/* -------------------------------------------------------------------------- */
interface SummaryCardProps {
  title: string;
  icon: React.ReactNode;
  color: string;
  data: Record<string, unknown> | undefined;
}

function SummaryCard({ title, icon, color, data }: SummaryCardProps) {
  if (!data || Object.keys(data).length === 0) return null;

  const entries = Object.entries(data).filter(
    ([, val]) => val !== null && val !== undefined,
  );

  if (entries.length === 0) return null;

  return (
    <Box
      className="glass"
      style={{
        flex: 1,
        minWidth: 200,
        padding: 16,
        borderRadius: 'var(--mi-radius-lg)',
        boxShadow: 'var(--mi-shadow-sm)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <Box
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 2,
          background: color,
        }}
      />
      <Group gap={8} mb={12}>
        {icon}
        <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
          {title}
        </Text>
      </Group>
      <Stack gap={6}>
        {entries.map(([key, value]) => {
          const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
          const displayValue =
            typeof value === 'object'
              ? JSON.stringify(value)
              : typeof value === 'number'
                ? Number.isInteger(value)
                  ? value.toString()
                  : value.toFixed(2)
                : String(value);

          return (
            <Group key={key} justify="space-between" gap={8} wrap="nowrap">
              <Text size="xs" style={{ color: 'var(--mi-text-muted)', minWidth: 0 }} lineClamp={1}>
                {displayKey}
              </Text>
              <Text
                size="xs"
                fw={600}
                style={{
                  color: 'var(--mi-text)',
                  flexShrink: 0,
                  fontVariantNumeric: 'tabular-nums',
                  maxWidth: 120,
                  textAlign: 'right',
                }}
                lineClamp={1}
              >
                {displayValue}
              </Text>
            </Group>
          );
        })}
      </Stack>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Pipeline Timeline Step                                                      */
/* -------------------------------------------------------------------------- */
function PipelineTimelineStep({ log, index, isLast }: { log: PipelineLog; index: number; isLast: boolean }) {
  const duration = log.duration_seconds ?? log.duration ?? null;
  const timestamp = log.timestamp ?? log.created_at ?? null;
  const stepColor = getPipelineStepColor(log.step);
  const statusColor = getStatusColor(log.status);

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index * 0.06, 0.5), duration: 0.25 }}
      style={{ position: 'relative' }}
    >
      {/* Timeline dot */}
      <Box
        style={{
          position: 'absolute',
          left: -21,
          top: 12,
          width: 14,
          height: 14,
          borderRadius: '50%',
          backgroundColor: stepColor,
          border: '3px solid var(--mi-surface)',
          boxShadow: `0 0 0 2px ${stepColor}40`,
          zIndex: 2,
        }}
      />

      {/* Step card */}
      <Box
        style={{
          padding: '12px 14px',
          borderRadius: 'var(--mi-radius-lg)',
          backgroundColor: 'var(--mi-surface)',
          border: '1px solid var(--mi-border)',
          borderLeft: `3px solid ${stepColor}`,
          transition: 'all var(--mi-transition-fast)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.boxShadow = 'var(--mi-shadow-sm)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        <Group justify="space-between" align="center" mb={4} wrap="nowrap">
          <Group gap={8} align="center" style={{ minWidth: 0 }}>
            <StepStatusIcon status={log.status} />
            <Text
              size="sm"
              fw={700}
              style={{
                color: 'var(--mi-text)',
                minWidth: 0,
                textTransform: 'capitalize',
              }}
              lineClamp={1}
            >
              {log.step.replace(/_/g, ' ')}
            </Text>
          </Group>
          <Badge
            size="xs"
            color={statusColor}
            variant="light"
            radius="sm"
            styles={{ root: { textTransform: 'capitalize', flexShrink: 0 } }}
          >
            {log.status}
          </Badge>
        </Group>

        <Group gap={16} wrap="wrap">
          {duration !== null && (
            <Group gap={4}>
              <IconClock size={11} stroke={1.5} color="var(--mi-text-muted)" />
              <Text size="xs" fw={600} style={{ color: 'var(--mi-text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                {formatDuration(duration)}
              </Text>
            </Group>
          )}
          {timestamp && (
            <Tooltip label={formatDateTime(timestamp)} withArrow>
              <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>
                {formatRelativeTime(timestamp)}
              </Text>
            </Tooltip>
          )}
        </Group>

        {/* Show any additional data keys */}
        {Object.entries(log)
          .filter(
            ([key, val]) =>
              !['step', 'status', 'duration_seconds', 'duration', 'timestamp', 'created_at'].includes(key) &&
              val !== null &&
              val !== undefined &&
              typeof val !== 'object',
          )
          .slice(0, 3)
          .map(([key, val]) => (
            <Text key={key} size="xs" mt={4} style={{ color: 'var(--mi-text-muted)' }}>
              {key.replace(/_/g, ' ')}: {String(val)}
            </Text>
          ))}
      </Box>
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */
/* Main Audit Panel                                                            */
/* -------------------------------------------------------------------------- */
export function AuditPanel() {
  const activeChartId = useChartStore((s) => s.activeChartId);
  const { data: auditPack, isLoading, isError, refetch } = useAuditPack(activeChartId);

  /* Loading */
  if (isLoading) {
    return <AuditSkeleton />;
  }

  /* Error */
  if (isError) {
    return (
      <Box p={16}>
        <Alert
          icon={<IconAlertCircle size={18} />}
          title="Failed to load audit data"
          color="red"
          radius="md"
          styles={{
            root: {
              backgroundColor: 'color-mix(in srgb, var(--mi-error) 6%, var(--mi-surface))',
              borderColor: 'color-mix(in srgb, var(--mi-error) 20%, transparent)',
            },
          }}
        >
          <Text size="sm" style={{ color: 'var(--mi-text-secondary)' }}>
            There was an error loading audit trail data.
          </Text>
          <Button
            size="xs"
            variant="light"
            color="red"
            mt={8}
            leftSection={<IconRefresh size={14} />}
            onClick={() => refetch()}
          >
            Retry
          </Button>
        </Alert>
      </Box>
    );
  }

  /* Empty */
  if (!auditPack) {
    return <EmptyState />;
  }

  const pipelineLogs = auditPack.pipeline_log ?? [];
  const totalDuration = pipelineLogs.reduce((sum, log) => {
    const d = log.duration_seconds ?? log.duration ?? 0;
    return sum + (d ?? 0);
  }, 0);
  const completedSteps = pipelineLogs.filter((l) => {
    const s = (l.status ?? '').toLowerCase();
    return s === 'completed' || s === 'success' || s === 'done';
  }).length;
  const failedSteps = pipelineLogs.filter((l) => {
    const s = (l.status ?? '').toLowerCase();
    return s === 'failed' || s === 'error';
  }).length;

  return (
    <Box
      style={{
        height: '100%',
        overflow: 'auto',
        padding: 16,
      }}
    >
      <Stack gap={16}>
        {/* Header info */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Box
            className="glass"
            style={{
              padding: 16,
              borderRadius: 'var(--mi-radius-lg)',
              boxShadow: 'var(--mi-shadow-sm)',
            }}
          >
            <Group justify="space-between" align="center" mb={12}>
              <Group gap={8}>
                <IconClipboardCheck size={16} stroke={1.5} color="var(--mi-primary)" />
                <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
                  Audit Trail
                </Text>
              </Group>
              {auditPack.run_id && (
                <Badge
                  size="xs"
                  variant="outline"
                  color="gray"
                  radius="sm"
                  styles={{ root: { fontFamily: 'monospace', textTransform: 'none' } }}
                >
                  Run: {(auditPack.run_id ?? '').length > 12 ? auditPack.run_id.slice(0, 12) + '...' : auditPack.run_id ?? ''}
                </Badge>
              )}
            </Group>

            {/* Stats row */}
            <Group gap={20} wrap="wrap">
              <Box>
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Steps
                </Text>
                <Text fw={700} style={{ color: 'var(--mi-text)', fontVariantNumeric: 'tabular-nums' }}>
                  {pipelineLogs.length}
                </Text>
              </Box>
              <Box style={{ width: 1, height: 28, backgroundColor: 'var(--mi-border)' }} />
              <Box>
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Completed
                </Text>
                <Text fw={700} style={{ color: 'var(--mi-success)', fontVariantNumeric: 'tabular-nums' }}>
                  {completedSteps}
                </Text>
              </Box>
              {failedSteps > 0 && (
                <>
                  <Box style={{ width: 1, height: 28, backgroundColor: 'var(--mi-border)' }} />
                  <Box>
                    <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      Failed
                    </Text>
                    <Text fw={700} style={{ color: 'var(--mi-error)', fontVariantNumeric: 'tabular-nums' }}>
                      {failedSteps}
                    </Text>
                  </Box>
                </>
              )}
              <Box style={{ width: 1, height: 28, backgroundColor: 'var(--mi-border)' }} />
              <Box>
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Total Time
                </Text>
                <Text fw={700} style={{ color: 'var(--mi-text)', fontVariantNumeric: 'tabular-nums' }}>
                  {formatDuration(totalDuration)}
                </Text>
              </Box>
            </Group>
          </Box>
        </motion.div>

        {/* Summary Cards */}
        <Group gap={12} wrap="wrap" align="stretch">
          <SummaryCard
            title="HCC Summary"
            icon={<IconShieldCheck size={14} stroke={2} color="#3B82F6" />}
            color="#3B82F6"
            data={auditPack.hcc_summary as Record<string, unknown> | undefined}
          />
          <SummaryCard
            title="HEDIS Summary"
            icon={<IconHeartRateMonitor size={14} stroke={2} color="#10B981" />}
            color="#10B981"
            data={auditPack.hedis_summary as Record<string, unknown> | undefined}
          />
          <SummaryCard
            title="Assertions"
            icon={<IconAlertTriangle size={14} stroke={2} color="#F59E0B" />}
            color="#F59E0B"
            data={auditPack.assertions_summary as Record<string, unknown> | undefined}
          />
        </Group>

        {/* Pipeline Timeline */}
        {pipelineLogs.length > 0 && (
          <Box>
            <Group gap={8} mb={12}>
              <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
                Pipeline Steps
              </Text>
              <Badge size="sm" variant="light" color="blue" radius="md">
                {pipelineLogs.length}
              </Badge>
            </Group>

            <Box style={{ position: 'relative', paddingLeft: 24 }}>
              {/* Vertical line */}
              <Box
                style={{
                  position: 'absolute',
                  left: 7,
                  top: 12,
                  bottom: 12,
                  width: 2,
                  backgroundColor: 'var(--mi-border)',
                  borderRadius: 1,
                }}
              />

              <Stack gap={10}>
                {pipelineLogs.map((log, idx) => (
                  <PipelineTimelineStep
                    key={`${log.step}-${idx}`}
                    log={log}
                    index={idx}
                    isLast={idx === pipelineLogs.length - 1}
                  />
                ))}
              </Stack>
            </Box>
          </Box>
        )}

        {pipelineLogs.length === 0 && !auditPack.hcc_summary && !auditPack.hedis_summary && (
          <EmptyState />
        )}
      </Stack>
    </Box>
  );
}
