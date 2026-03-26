import { useMemo } from 'react';
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
  Progress,
} from '@mantine/core';
import {
  IconCpu,
  IconAlertCircle,
  IconRefresh,
  IconClock,
  IconCircleCheck,
  IconCircleX,
  IconPlayerPlay,
  IconBrain,
  IconSearch,
  IconShieldCheck,
  IconChecklist,
  IconArrowRight,
} from '@tabler/icons-react';
import { motion } from 'framer-motion';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { useChartStore } from '../../stores/chartStore';
import { useAuditPack, useMLPredictions, useVerifiedICDs } from '../../hooks/useChart';
import type { PipelineLog } from '../../types/api';
import { formatDuration } from '../../utils/formatters';
import { getPipelineStepColor, getStatusColor, getConfidenceColor } from '../../utils/colors';
import { ConfidenceBar } from '../shared/ConfidenceBar';

/* -------------------------------------------------------------------------- */
/* Skeleton                                                                    */
/* -------------------------------------------------------------------------- */
function PipelineSkeleton() {
  return (
    <Stack gap={16} p={16}>
      <Skeleton height={24} width={160} radius="md" />
      {/* Stepper skeleton */}
      <Group gap={4}>
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} height={60} style={{ flex: 1 }} radius="md" />
        ))}
      </Group>
      {/* Timing chart skeleton */}
      <Skeleton height={200} radius="md" />
      {/* Predictions skeleton */}
      <Skeleton height={24} width={120} radius="md" />
      {[1, 2, 3].map((i) => (
        <Skeleton key={i} height={50} radius="md" />
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
        <IconCpu size={32} stroke={1.2} color="var(--mi-text-muted)" />
      </Box>
      <Text size="md" fw={600} style={{ color: 'var(--mi-text)' }}>
        No Pipeline Data Available
      </Text>
      <Text size="sm" c="dimmed" ta="center" maw={300}>
        ML pipeline results will appear here once the chart has been processed.
      </Text>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Step status icon                                                            */
/* -------------------------------------------------------------------------- */
function StepStatusIcon({ status, size = 18 }: { status: string; size?: number }) {
  const normalized = status.toLowerCase();
  if (normalized === 'completed' || normalized === 'success' || normalized === 'done') {
    return <IconCircleCheck size={size} stroke={2} color="var(--mi-success)" />;
  }
  if (normalized === 'failed' || normalized === 'error') {
    return <IconCircleX size={size} stroke={2} color="var(--mi-error)" />;
  }
  if (normalized === 'running' || normalized === 'in_progress' || normalized === 'processing') {
    return <IconPlayerPlay size={size} stroke={2} color="var(--mi-info)" />;
  }
  return <IconClock size={size} stroke={2} color="var(--mi-text-muted)" />;
}

/* -------------------------------------------------------------------------- */
/* Recharts custom tooltip                                                     */
/* -------------------------------------------------------------------------- */
interface TimingTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; payload: { step: string; duration: number; color: string } }>;
}

function TimingTooltipContent({ active, payload }: TimingTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const entry = payload[0];
  return (
    <Box
      className="glass"
      style={{
        padding: '8px 12px',
        borderRadius: 'var(--mi-radius-md)',
        boxShadow: 'var(--mi-shadow-md)',
      }}
    >
      <Text size="xs" fw={600} style={{ color: 'var(--mi-text)', textTransform: 'capitalize' }}>
        {entry.payload.step.replace(/_/g, ' ')}
      </Text>
      <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
        Duration: {formatDuration(entry.payload.duration)}
      </Text>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Pipeline Steps (horizontal stepper)                                         */
/* -------------------------------------------------------------------------- */
function PipelineStepper({ logs }: { logs: PipelineLog[] }) {
  return (
    <Box
      style={{
        display: 'flex',
        gap: 4,
        overflowX: 'auto',
        padding: '4px 0',
        scrollbarWidth: 'thin',
      }}
    >
      {logs.map((log, idx) => {
        const stepColor = getPipelineStepColor(log.step);
        const duration = log.duration_seconds ?? log.duration ?? null;
        const isSuccess = ['completed', 'success', 'done'].includes(log.status.toLowerCase());
        const isFailed = ['failed', 'error'].includes(log.status.toLowerCase());

        return (
          <motion.div
            key={`${log.step}-${idx}`}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: idx * 0.06, duration: 0.2 }}
            style={{ flex: 1, minWidth: 90 }}
          >
            <Tooltip
              label={`${log.step.replace(/_/g, ' ')} - ${log.status} ${duration !== null ? `(${formatDuration(duration)})` : ''}`}
              withArrow
              multiline
            >
              <Box
                style={{
                  padding: '10px 8px',
                  borderRadius: 'var(--mi-radius-md)',
                  backgroundColor: 'var(--mi-surface)',
                  border: `1px solid ${isSuccess ? stepColor + '40' : isFailed ? 'var(--mi-error)' + '40' : 'var(--mi-border)'}`,
                  textAlign: 'center',
                  position: 'relative',
                  overflow: 'hidden',
                  transition: 'all var(--mi-transition-fast)',
                }}
              >
                {/* Top color bar */}
                <Box
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: 3,
                    backgroundColor: isSuccess ? stepColor : isFailed ? 'var(--mi-error)' : 'var(--mi-border)',
                  }}
                />

                <StepStatusIcon status={log.status} size={16} />

                <Text
                  size="xs"
                  fw={600}
                  mt={4}
                  style={{
                    color: 'var(--mi-text)',
                    fontSize: 10,
                    textTransform: 'capitalize',
                    lineHeight: 1.2,
                  }}
                  lineClamp={2}
                >
                  {log.step.replace(/_/g, ' ')}
                </Text>

                {duration !== null && (
                  <Text
                    size="xs"
                    mt={2}
                    style={{
                      color: 'var(--mi-text-muted)',
                      fontSize: 9,
                      fontVariantNumeric: 'tabular-nums',
                    }}
                  >
                    {formatDuration(duration)}
                  </Text>
                )}
              </Box>
            </Tooltip>

            {/* Arrow between steps */}
            {idx < logs.length - 1 && (
              <Box
                style={{
                  position: 'absolute',
                  right: -8,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--mi-text-muted)',
                  zIndex: 2,
                  display: 'none', // Hidden since steps are side by side
                }}
              >
                <IconArrowRight size={12} />
              </Box>
            )}
          </motion.div>
        );
      })}
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Timing Bar Chart                                                            */
/* -------------------------------------------------------------------------- */
function TimingChart({ logs }: { logs: PipelineLog[] }) {
  const chartData = useMemo(() => {
    return logs
      .filter((log) => {
        const d = log.duration_seconds ?? log.duration;
        return d !== null && d !== undefined && d > 0;
      })
      .map((log) => ({
        step: log.step.replace(/_/g, ' '),
        duration: log.duration_seconds ?? log.duration ?? 0,
        color: getPipelineStepColor(log.step),
      }));
  }, [logs]);

  if (chartData.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2, duration: 0.3 }}
    >
      <Box
        className="glass"
        style={{
          borderRadius: 'var(--mi-radius-lg)',
          padding: 16,
          boxShadow: 'var(--mi-shadow-sm)',
        }}
      >
        <Group gap={8} mb={12}>
          <IconClock size={14} stroke={2} color="var(--mi-primary)" />
          <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
            Pipeline Timing
          </Text>
        </Group>
        <Box style={{ width: '100%', minHeight: 220 }}>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 5, right: 30, bottom: 5, left: 80 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--mi-border)" opacity={0.5} horizontal={false} />
              <XAxis
                type="number"
                tick={{ fill: 'var(--mi-text-muted)', fontSize: 10 }}
                stroke="var(--mi-border)"
                tickFormatter={(v: number) => formatDuration(v)}
              />
              <YAxis
                type="category"
                dataKey="step"
                tick={{ fill: 'var(--mi-text-muted)', fontSize: 10 }}
                stroke="var(--mi-border)"
                width={75}
                style={{ textTransform: 'capitalize' }}
              />
              <RechartsTooltip content={<TimingTooltipContent />} />
              <Bar dataKey="duration" radius={[0, 4, 4, 0]} barSize={18}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} fillOpacity={0.8} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Box>
      </Box>
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */
/* ML Predictions Section                                                      */
/* -------------------------------------------------------------------------- */
function MLPredictionsSection({ chartId }: { chartId: string }) {
  const { data: predictions, isLoading } = useMLPredictions(chartId);

  if (isLoading) {
    return (
      <Stack gap={8}>
        <Skeleton height={20} width={160} radius="md" />
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} height={44} radius="md" />
        ))}
      </Stack>
    );
  }

  if (!predictions || predictions.length === 0) return null;

  // Limit to top 20 by confidence
  const sortedPredictions = [...predictions]
    .sort((a: Record<string, unknown>, b: Record<string, unknown>) => {
      const confA = typeof a.confidence === 'number' ? a.confidence : typeof a.probability === 'number' ? a.probability : 0;
      const confB = typeof b.confidence === 'number' ? b.confidence : typeof b.probability === 'number' ? b.probability : 0;
      return confB - confA;
    })
    .slice(0, 20);

  return (
    <Box>
      <Group gap={8} mb={10}>
        <IconBrain size={14} stroke={2} color="#EC4899" />
        <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
          BioClinicalBERT Predictions
        </Text>
        <Badge size="sm" variant="light" color="pink" radius="md">
          {predictions.length}
        </Badge>
      </Group>

      <Stack gap={6}>
        {sortedPredictions.map((pred: Record<string, unknown>, idx: number) => {
          const hccCode = String(pred.hcc_code ?? pred.code ?? pred.label ?? '');
          const description = String(pred.hcc_description ?? pred.description ?? '');
          const confidence = typeof pred.confidence === 'number' ? pred.confidence : typeof pred.probability === 'number' ? pred.probability : 0;

          return (
            <motion.div
              key={`${hccCode}-${idx}`}
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: Math.min(idx * 0.03, 0.3), duration: 0.15 }}
            >
              <Box
                style={{
                  padding: '10px 12px',
                  borderRadius: 'var(--mi-radius-md)',
                  backgroundColor: 'var(--mi-surface)',
                  border: '1px solid var(--mi-border)',
                }}
              >
                <Group justify="space-between" align="center" wrap="nowrap">
                  <Group gap={8} align="center" style={{ minWidth: 0, flex: 1 }}>
                    <Badge
                      size="xs"
                      variant="light"
                      color="pink"
                      radius="sm"
                      styles={{
                        root: {
                          fontFamily: '"JetBrains Mono", monospace',
                          fontWeight: 700,
                          textTransform: 'none',
                          flexShrink: 0,
                        },
                      }}
                    >
                      {hccCode}
                    </Badge>
                    <Text size="xs" style={{ color: 'var(--mi-text-secondary)', minWidth: 0 }} lineClamp={1}>
                      {description}
                    </Text>
                  </Group>
                  <Box style={{ width: 100, flexShrink: 0 }}>
                    <ConfidenceBar confidence={confidence} size="xs" />
                  </Box>
                </Group>
              </Box>
            </motion.div>
          );
        })}
      </Stack>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Verified ICDs Section                                                       */
/* -------------------------------------------------------------------------- */
function VerifiedICDsSection({ chartId }: { chartId: string }) {
  const { data: icds, isLoading } = useVerifiedICDs(chartId);

  if (isLoading) {
    return (
      <Stack gap={8}>
        <Skeleton height={20} width={140} radius="md" />
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} height={44} radius="md" />
        ))}
      </Stack>
    );
  }

  if (!icds || icds.length === 0) return null;

  return (
    <Box>
      <Group gap={8} mb={10}>
        <IconChecklist size={14} stroke={2} color="#10B981" />
        <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
          LLM Verified ICDs
        </Text>
        <Badge size="sm" variant="light" color="green" radius="md">
          {icds.length}
        </Badge>
      </Group>

      <Stack gap={6}>
        {icds.slice(0, 15).map((icd: Record<string, unknown>, idx: number) => {
          const code = String(icd.icd10_code ?? icd.code ?? '');
          const description = String(icd.icd10_description ?? icd.description ?? '');
          const verified = icd.verified === true || icd.status === 'verified';
          const confidence = typeof icd.confidence === 'number' ? icd.confidence : typeof icd.llm_confidence === 'number' ? icd.llm_confidence : null;

          return (
            <motion.div
              key={`${code}-${idx}`}
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: Math.min(idx * 0.03, 0.3), duration: 0.15 }}
            >
              <Box
                style={{
                  padding: '10px 12px',
                  borderRadius: 'var(--mi-radius-md)',
                  backgroundColor: 'var(--mi-surface)',
                  border: '1px solid var(--mi-border)',
                }}
              >
                <Group justify="space-between" align="center" wrap="nowrap">
                  <Group gap={8} align="center" style={{ minWidth: 0, flex: 1 }}>
                    <Badge
                      size="xs"
                      variant="filled"
                      color={verified ? 'green' : 'red'}
                      radius="sm"
                      styles={{
                        root: {
                          fontFamily: '"JetBrains Mono", monospace',
                          fontWeight: 700,
                          textTransform: 'none',
                          flexShrink: 0,
                        },
                      }}
                    >
                      {code}
                    </Badge>
                    <Text size="xs" style={{ color: 'var(--mi-text-secondary)', minWidth: 0 }} lineClamp={1}>
                      {description}
                    </Text>
                  </Group>
                  <Group gap={8} style={{ flexShrink: 0 }}>
                    {confidence !== null && (
                      <Box style={{ width: 80 }}>
                        <ConfidenceBar confidence={confidence} size="xs" />
                      </Box>
                    )}
                    <Badge
                      size="xs"
                      variant="light"
                      color={verified ? 'green' : 'red'}
                      radius="sm"
                      styles={{ root: { textTransform: 'none' } }}
                    >
                      {verified ? 'Verified' : 'Rejected'}
                    </Badge>
                  </Group>
                </Group>
              </Box>
            </motion.div>
          );
        })}
      </Stack>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Main Pipeline Panel                                                         */
/* -------------------------------------------------------------------------- */
export function PipelinePanel() {
  const activeChartId = useChartStore((s) => s.activeChartId);
  const { data: auditPack, isLoading, isError, refetch } = useAuditPack(activeChartId);

  /* Loading */
  if (isLoading) {
    return <PipelineSkeleton />;
  }

  /* Error */
  if (isError) {
    return (
      <Box p={16}>
        <Alert
          icon={<IconAlertCircle size={18} />}
          title="Failed to load pipeline data"
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
            There was an error loading pipeline data.
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

  const pipelineLogs = auditPack?.pipeline_log ?? [];

  /* Empty */
  if (!auditPack && pipelineLogs.length === 0) {
    return <EmptyState />;
  }

  return (
    <Box
      style={{
        height: '100%',
        overflow: 'auto',
        padding: 16,
      }}
    >
      <Stack gap={20}>
        {/* Pipeline header */}
        <Group gap={8}>
          <IconCpu size={16} stroke={1.5} color="var(--mi-primary)" />
          <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
            ML Pipeline Results
          </Text>
        </Group>

        {/* Horizontal Stepper */}
        {pipelineLogs.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <PipelineStepper logs={pipelineLogs} />
          </motion.div>
        )}

        {/* Timing Chart */}
        {pipelineLogs.length > 0 && <TimingChart logs={pipelineLogs} />}

        {/* ML Predictions */}
        {activeChartId && <MLPredictionsSection chartId={activeChartId} />}

        {/* Verified ICDs */}
        {activeChartId && <VerifiedICDsSection chartId={activeChartId} />}

        {pipelineLogs.length === 0 && !activeChartId && <EmptyState />}
      </Stack>
    </Box>
  );
}
