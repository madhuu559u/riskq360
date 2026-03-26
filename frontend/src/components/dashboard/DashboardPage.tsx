import { useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
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
  SimpleGrid,
  ScrollArea,
  ThemeIcon,
  Progress,
  ActionIcon,
  RingProgress,
} from '@mantine/core';
import {
  IconAlertCircle,
  IconRefresh,
  IconFiles,
  IconCheck,
  IconX,
  IconClock,
  IconDatabase,
  IconActivity,
  IconShieldCheck,
  IconHeartRateMonitor,
  IconArrowUp,
  IconArrowDown,
  IconEye,
  IconBrain,
  IconStethoscope,
  IconAlertTriangle,
  IconChartBar,
  IconTrendingUp,
  IconListCheck,
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
  PieChart,
  Pie,
} from 'recharts';
import { useDashboardStats, useDBStats, useRecentActivity, useCharts, usePipelineRuns } from '../../hooks/useChart';
import { useChartStore } from '../../stores/chartStore';
import type { DashboardStats, DBStats, RecentActivityItem, PipelineRun } from '../../types/api';
import type { Chart } from '../../types/chart';
import { formatNumber, formatDuration, formatPercentValue, formatRelativeTime, formatDateTime, formatChartId, formatRAF } from '../../utils/formatters';
import { getStatusColor } from '../../utils/colors';

/* -------------------------------------------------------------------------- */
/* Skeleton                                                                    */
/* -------------------------------------------------------------------------- */
function DashboardSkeleton() {
  return (
    <Stack gap={20} p={24}>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing={16}>
        {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} height={160} radius="lg" />)}
      </SimpleGrid>
    </Stack>
  );
}

/* -------------------------------------------------------------------------- */
/* Intelligence Tile — reusable card for the 6 tiles                          */
/* -------------------------------------------------------------------------- */
interface TileProps {
  title: string;
  icon: React.ReactNode;
  accentColor: string;
  index: number;
  children: React.ReactNode;
}

function IntelTile({ title, icon, accentColor, index, children }: TileProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      style={{ height: '100%' }}
    >
      <Box
        className="glass"
        style={{
          padding: 18,
          borderRadius: 'var(--mi-radius-xl)',
          boxShadow: 'var(--mi-shadow-md)',
          position: 'relative',
          overflow: 'hidden',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Box style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: accentColor }} />
        <Group gap={8} mb={14}>
          {icon}
          <Text size="xs" fw={700} tt="uppercase" style={{ color: 'var(--mi-text-muted)', letterSpacing: '0.06em', fontSize: 10 }}>
            {title}
          </Text>
        </Group>
        <Box style={{ flex: 1 }}>
          {children}
        </Box>
      </Box>
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */
/* Tile 1: Risk Score Overview                                                 */
/* -------------------------------------------------------------------------- */
function RiskScoreOverview({ charts }: { charts: Chart[] }) {
  const stats = useMemo(() => {
    const withRaf = charts.filter((c) => c.raf_summary?.total_raf_score != null && c.status === 'completed');
    if (withRaf.length === 0) return null;
    const scores = withRaf.map((c) => c.raf_summary!.total_raf_score);
    const avg = scores.reduce((s, v) => s + v, 0) / scores.length;
    const max = Math.max(...scores);
    const min = Math.min(...scores);
    const totalHCCs = withRaf.reduce((s, c) => s + (c.raf_summary?.payable_hcc_count ?? 0), 0);
    const avgHCCs = totalHCCs / withRaf.length;
    // Categorize risk levels
    const highRisk = withRaf.filter((c) => c.raf_summary!.total_raf_score >= 2.0).length;
    const medRisk = withRaf.filter((c) => c.raf_summary!.total_raf_score >= 1.0 && c.raf_summary!.total_raf_score < 2.0).length;
    const lowRisk = withRaf.filter((c) => c.raf_summary!.total_raf_score < 1.0).length;
    return { avg, max, min, totalHCCs, avgHCCs, count: withRaf.length, highRisk, medRisk, lowRisk };
  }, [charts]);

  if (!stats) return (
    <Box style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 100 }}>
      <Text size="sm" c="dimmed">No RAF data yet</Text>
    </Box>
  );

  return (
    <Stack gap={12}>
      <Group justify="space-between" align="flex-end">
        <Box>
          <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>Average RAF</Text>
          <Text fw={800} className="gradient-text" style={{ fontSize: 34, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
            {formatRAF(stats.avg)}
          </Text>
        </Box>
        <Stack gap={2} align="flex-end">
          <Group gap={4}>
            <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>High</Text>
            <Text size="xs" fw={600} style={{ color: '#EF4444', fontSize: 10 }}>{formatRAF(stats.max)}</Text>
          </Group>
          <Group gap={4}>
            <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>Low</Text>
            <Text size="xs" fw={600} style={{ color: '#10B981', fontSize: 10 }}>{formatRAF(stats.min)}</Text>
          </Group>
        </Stack>
      </Group>

      {/* Risk tier breakdown */}
      <Box>
        <Group justify="space-between" mb={4}>
          <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>Risk Distribution</Text>
          <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>{stats.count} members</Text>
        </Group>
        <Group gap={4} wrap="nowrap">
          {stats.highRisk > 0 && (
            <Tooltip label={`High Risk (RAF ≥ 2.0): ${stats.highRisk}`}>
              <Box style={{
                flex: stats.highRisk,
                height: 8,
                borderRadius: 'var(--mi-radius-full)',
                background: 'linear-gradient(90deg, #EF4444, #F87171)',
              }} />
            </Tooltip>
          )}
          {stats.medRisk > 0 && (
            <Tooltip label={`Medium Risk (1.0–2.0): ${stats.medRisk}`}>
              <Box style={{
                flex: stats.medRisk,
                height: 8,
                borderRadius: 'var(--mi-radius-full)',
                background: 'linear-gradient(90deg, #F59E0B, #FBBF24)',
              }} />
            </Tooltip>
          )}
          {stats.lowRisk > 0 && (
            <Tooltip label={`Low Risk (< 1.0): ${stats.lowRisk}`}>
              <Box style={{
                flex: stats.lowRisk,
                height: 8,
                borderRadius: 'var(--mi-radius-full)',
                background: 'linear-gradient(90deg, #10B981, #34D399)',
              }} />
            </Tooltip>
          )}
        </Group>
        <Group gap={12} mt={6}>
          {[
            { label: 'High', value: stats.highRisk, color: '#EF4444' },
            { label: 'Medium', value: stats.medRisk, color: '#F59E0B' },
            { label: 'Low', value: stats.lowRisk, color: '#10B981' },
          ].map((tier) => (
            <Group key={tier.label} gap={4}>
              <Box style={{ width: 6, height: 6, borderRadius: 2, backgroundColor: tier.color }} />
              <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>{tier.label}: {tier.value}</Text>
            </Group>
          ))}
        </Group>
      </Box>

      <Group gap={16}>
        <Box>
          <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>Total HCCs</Text>
          <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>{stats.totalHCCs}</Text>
        </Box>
        <Box>
          <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>Avg HCCs/Member</Text>
          <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>{stats.avgHCCs.toFixed(1)}</Text>
        </Box>
      </Group>
    </Stack>
  );
}

/* -------------------------------------------------------------------------- */
/* Tile 2: HCC Category Distribution                                           */
/* -------------------------------------------------------------------------- */
function HCCDistribution({ charts }: { charts: Chart[] }) {
  const hccData = useMemo(() => {
    const hccMap = new Map<string, { code: string; desc: string; count: number; totalRaf: number }>();
    for (const chart of charts) {
      if (!chart.raf_summary?.hcc_details) continue;
      for (const hcc of chart.raf_summary.hcc_details) {
        const existing = hccMap.get(hcc.hcc_code) ?? { code: hcc.hcc_code, desc: hcc.hcc_description, count: 0, totalRaf: 0 };
        existing.count++;
        existing.totalRaf += hcc.raf_weight ?? 0;
        hccMap.set(hcc.hcc_code, existing);
      }
    }
    return [...hccMap.values()]
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
  }, [charts]);

  if (hccData.length === 0) return (
    <Box style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 100 }}>
      <Text size="sm" c="dimmed">No HCC data</Text>
    </Box>
  );

  const maxCount = Math.max(...hccData.map((h) => h.count));
  const COLORS = ['#3B82F6', '#8B5CF6', '#EC4899', '#10B981', '#F59E0B', '#06B6D4', '#F97316', '#EF4444'];

  return (
    <Stack gap={6}>
      {hccData.map((hcc, i) => (
        <Tooltip key={hcc.code} label={`${hcc.desc} — Avg RAF: ${(hcc.totalRaf / hcc.count).toFixed(3)}`} multiline maw={280}>
          <Box>
            <Group justify="space-between" mb={2}>
              <Group gap={6}>
                <Text size="xs" fw={700} style={{ color: 'var(--mi-text)', fontFamily: '"JetBrains Mono", monospace', fontSize: 10 }}>
                  HCC {hcc.code}
                </Text>
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }} lineClamp={1}>
                  {hcc.desc.length > 25 ? hcc.desc.slice(0, 25) + '...' : hcc.desc}
                </Text>
              </Group>
              <Text size="xs" fw={700} style={{ color: 'var(--mi-text)', fontVariantNumeric: 'tabular-nums', fontSize: 11 }}>
                {hcc.count}
              </Text>
            </Group>
            <Progress value={(hcc.count / maxCount) * 100} size={4} radius="xl" color={COLORS[i % COLORS.length]} />
          </Box>
        </Tooltip>
      ))}
    </Stack>
  );
}

/* -------------------------------------------------------------------------- */
/* Tile 3: Quality Compliance (HEDIS-style)                                    */
/* -------------------------------------------------------------------------- */
function QualityCompliance({ charts, stats }: { charts: Chart[]; stats: DashboardStats | undefined }) {
  // We derive quality metrics from available data
  const qualityMetrics = useMemo(() => {
    const completed = charts.filter((c) => c.status === 'completed');
    const withRaf = completed.filter((c) => c.raf_summary?.total_raf_score != null);
    const withHCCs = completed.filter((c) => (c.raf_summary?.payable_hcc_count ?? 0) > 0);
    const total = completed.length;
    if (total === 0) return null;

    return {
      chartsProcessed: total,
      captureRate: total > 0 ? Math.round((withHCCs.length / total) * 100) : 0,
      avgHCCsPerChart: withRaf.length > 0
        ? (withRaf.reduce((s, c) => s + (c.raf_summary?.payable_hcc_count ?? 0), 0) / withRaf.length).toFixed(1)
        : '0',
      successRate: stats?.success_rate ?? (total > 0 ? Math.round((completed.length / charts.length) * 100) : 0),
    };
  }, [charts, stats]);

  if (!qualityMetrics) return (
    <Box style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 100 }}>
      <Text size="sm" c="dimmed">No quality data</Text>
    </Box>
  );

  const metrics = [
    { label: 'Charts Processed', value: qualityMetrics.chartsProcessed, total: charts.length, color: 'var(--mi-primary)' },
    { label: 'HCC Capture Rate', value: qualityMetrics.captureRate, total: 100, color: '#8B5CF6', suffix: '%' },
    { label: 'Pipeline Success', value: qualityMetrics.successRate, total: 100, color: 'var(--mi-success)', suffix: '%' },
  ];

  return (
    <Stack gap={14}>
      {metrics.map((m) => (
        <Box key={m.label}>
          <Group justify="space-between" mb={4}>
            <Text size="xs" style={{ color: 'var(--mi-text-secondary)', fontSize: 11 }}>{m.label}</Text>
            <Text size="xs" fw={700} style={{ color: 'var(--mi-text)', fontVariantNumeric: 'tabular-nums' }}>
              {m.value}{m.suffix ?? ''}{!m.suffix ? ` / ${m.total}` : ''}
            </Text>
          </Group>
          <Progress value={m.total > 0 ? (m.value / m.total) * 100 : 0} size={6} radius="xl" color={m.color} />
        </Box>
      ))}
      <Box style={{ padding: '8px 10px', borderRadius: 'var(--mi-radius-md)', backgroundColor: 'color-mix(in srgb, var(--mi-primary) 5%, var(--mi-surface))', border: '1px solid color-mix(in srgb, var(--mi-primary) 12%, transparent)' }}>
        <Group gap={6}>
          <IconBrain size={12} color="var(--mi-primary)" />
          <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
            Avg <Text span fw={700}>{qualityMetrics.avgHCCsPerChart}</Text> payable HCCs per chart
          </Text>
        </Group>
      </Box>
    </Stack>
  );
}

/* -------------------------------------------------------------------------- */
/* Tile 4: Top Diagnoses Found                                                 */
/* -------------------------------------------------------------------------- */
function TopDiagnoses({ charts }: { charts: Chart[] }) {
  const diagnoses = useMemo(() => {
    const icdMap = new Map<string, { code: string; desc: string; count: number }>();
    for (const chart of charts) {
      if (!chart.raf_summary?.hcc_details) continue;
      for (const hcc of chart.raf_summary.hcc_details) {
        // Each HCC detail has icd_count but not individual ICDs in the summary
        // Use the HCC as the diagnosis grouping
        const key = hcc.hcc_code;
        const existing = icdMap.get(key) ?? { code: `HCC ${hcc.hcc_code}`, desc: hcc.hcc_description, count: 0 };
        existing.count += hcc.icd_count ?? 1;
        icdMap.set(key, existing);
      }
    }
    return [...icdMap.values()].sort((a, b) => b.count - a.count).slice(0, 6);
  }, [charts]);

  if (diagnoses.length === 0) return (
    <Box style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 100 }}>
      <Text size="sm" c="dimmed">No diagnosis data</Text>
    </Box>
  );

  return (
    <Stack gap={4}>
      {diagnoses.map((dx, i) => (
        <Box
          key={dx.code}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '6px 8px',
            borderRadius: 'var(--mi-radius-md)',
            backgroundColor: i === 0 ? 'color-mix(in srgb, var(--mi-primary) 5%, var(--mi-surface))' : 'transparent',
          }}
        >
          <Text size="xs" fw={800} style={{ color: 'var(--mi-text-muted)', width: 16, textAlign: 'center', fontSize: 10 }}>
            {i + 1}
          </Text>
          <Box style={{ flex: 1, minWidth: 0 }}>
            <Text size="xs" fw={600} style={{ color: 'var(--mi-text)' }} lineClamp={1}>{dx.code}</Text>
            <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }} lineClamp={1}>{dx.desc}</Text>
          </Box>
          <Badge size="xs" variant="light" color="blue" radius="sm" styles={{ root: { fontVariantNumeric: 'tabular-nums' } }}>
            {dx.count} ICD{dx.count !== 1 ? 's' : ''}
          </Badge>
        </Box>
      ))}
    </Stack>
  );
}

/* -------------------------------------------------------------------------- */
/* Tile 5: Processing Pipeline Summary                                         */
/* -------------------------------------------------------------------------- */
function ProcessingSummary({ stats, runs }: { stats: DashboardStats | undefined; runs: PipelineRun[] }) {
  const pipelineStats = useMemo(() => {
    const completed = runs.filter((r) => r.status === 'completed');
    const failed = runs.filter((r) => r.status === 'failed');
    const running = runs.filter((r) => r.status === 'processing' || r.status === 'running');
    const avgTime = completed.length > 0
      ? completed.filter((r) => r.total_seconds).reduce((s, r) => s + (r.total_seconds ?? 0), 0) / completed.length
      : (stats?.avg_processing_seconds ?? 0);
    return {
      total: stats?.total_charts ?? runs.length,
      completed: stats?.completed ?? completed.length,
      failed: stats?.failed ?? failed.length,
      running: running.length,
      avgTime,
      successRate: stats?.success_rate ?? (runs.length > 0 ? Math.round((completed.length / runs.length) * 100) : 0),
    };
  }, [stats, runs]);

  return (
    <Stack gap={10}>
      <Group justify="space-between" align="flex-end">
        <Box>
          <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>Total Charts</Text>
          <Text fw={800} style={{ fontSize: 28, lineHeight: 1, color: 'var(--mi-text)', fontVariantNumeric: 'tabular-nums' }}>
            {pipelineStats.total}
          </Text>
        </Box>
        {pipelineStats.avgTime > 0 && (
          <Group gap={4}>
            <IconClock size={11} color="var(--mi-text-muted)" />
            <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>
              avg {formatDuration(pipelineStats.avgTime)}
            </Text>
          </Group>
        )}
      </Group>

      {/* Status breakdown */}
      <SimpleGrid cols={3} spacing={8}>
        {[
          { label: 'Completed', value: pipelineStats.completed, color: 'var(--mi-success)', icon: <IconCheck size={10} stroke={2.5} color="var(--mi-success)" /> },
          { label: 'Failed', value: pipelineStats.failed, color: 'var(--mi-error)', icon: <IconX size={10} stroke={2.5} color="var(--mi-error)" /> },
          { label: 'Running', value: pipelineStats.running, color: 'var(--mi-warning)', icon: <IconActivity size={10} stroke={2} color="var(--mi-warning)" /> },
        ].map((item) => (
          <Box key={item.label} style={{ padding: '8px', borderRadius: 'var(--mi-radius-md)', backgroundColor: 'var(--mi-surface)', border: '1px solid var(--mi-border)', textAlign: 'center' }}>
            <Group gap={4} justify="center" mb={2}>{item.icon}</Group>
            <Text fw={800} style={{ fontSize: 18, lineHeight: 1, color: 'var(--mi-text)', fontVariantNumeric: 'tabular-nums' }}>
              {item.value}
            </Text>
            <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 9 }}>{item.label}</Text>
          </Box>
        ))}
      </SimpleGrid>

      {/* Success ring */}
      <Group gap={10} style={{ padding: '6px 8px', borderRadius: 'var(--mi-radius-md)', backgroundColor: 'color-mix(in srgb, var(--mi-success) 5%, var(--mi-surface))', border: '1px solid color-mix(in srgb, var(--mi-success) 12%, transparent)' }}>
        <RingProgress
          size={36}
          thickness={4}
          roundCaps
          sections={[{ value: pipelineStats.successRate, color: pipelineStats.successRate >= 80 ? 'var(--mi-success)' : pipelineStats.successRate >= 50 ? 'var(--mi-warning)' : 'var(--mi-error)' }]}
          label={<Text size="xs" fw={800} ta="center" style={{ fontSize: 8, color: 'var(--mi-text)' }}>{pipelineStats.successRate}%</Text>}
        />
        <Box>
          <Text size="xs" fw={600} style={{ color: 'var(--mi-text)', fontSize: 11 }}>Success Rate</Text>
          <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>{pipelineStats.completed} of {pipelineStats.total} charts</Text>
        </Box>
      </Group>
    </Stack>
  );
}

/* -------------------------------------------------------------------------- */
/* Tile 6: RAF Distribution Chart                                              */
/* -------------------------------------------------------------------------- */
function RAFDistributionChart({ charts }: { charts: Chart[] }) {
  const distribution = useMemo(() => {
    const buckets = [
      { range: '< 0.5', min: 0, max: 0.5, count: 0, color: '#10B981' },
      { range: '0.5–1', min: 0.5, max: 1.0, count: 0, color: '#3B82F6' },
      { range: '1–2', min: 1.0, max: 2.0, count: 0, color: '#8B5CF6' },
      { range: '2–3', min: 2.0, max: 3.0, count: 0, color: '#F59E0B' },
      { range: '3–5', min: 3.0, max: 5.0, count: 0, color: '#EF4444' },
      { range: '5+', min: 5.0, max: Infinity, count: 0, color: '#DC2626' },
    ];
    for (const c of charts) {
      const raf = c.raf_summary?.total_raf_score;
      if (raf == null) continue;
      for (const b of buckets) {
        if (raf >= b.min && raf < b.max) { b.count++; break; }
      }
    }
    return buckets.filter((b) => b.count > 0);
  }, [charts]);

  if (distribution.length === 0) return (
    <Box style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 100 }}>
      <Text size="sm" c="dimmed">No RAF distribution data</Text>
    </Box>
  );

  return (
    <Box style={{ width: '100%', height: 180 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={distribution} margin={{ top: 5, right: 5, bottom: 5, left: -10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--mi-border)" opacity={0.4} vertical={false} />
          <XAxis dataKey="range" tick={{ fill: 'var(--mi-text-muted)', fontSize: 10 }} stroke="var(--mi-border)" />
          <YAxis tick={{ fill: 'var(--mi-text-muted)', fontSize: 10 }} stroke="var(--mi-border)" allowDecimals={false} width={24} />
          <RechartsTooltip content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const entry = payload[0];
            return (
              <Box className="glass" style={{ padding: '6px 10px', borderRadius: 'var(--mi-radius-md)', boxShadow: 'var(--mi-shadow-md)' }}>
                <Text size="xs" fw={600} style={{ color: 'var(--mi-text)' }}>RAF {String(entry.payload?.range)}</Text>
                <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>{entry.value} members</Text>
              </Box>
            );
          }} />
          <Bar dataKey="count" radius={[3, 3, 0, 0]} barSize={24}>
            {distribution.map((entry, i) => <Cell key={i} fill={entry.color} fillOpacity={0.85} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Recent Charts List (compact)                                                */
/* -------------------------------------------------------------------------- */
function RecentChartsList({ charts, onViewChart }: { charts: Chart[]; onViewChart: (id: string) => void }) {
  const recent = useMemo(() =>
    [...charts]
      .sort((a, b) => (b.started_at ?? '').localeCompare(a.started_at ?? ''))
      .slice(0, 8),
    [charts],
  );

  if (recent.length === 0) return (
    <Box style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 80 }}>
      <Text size="sm" c="dimmed">No charts yet</Text>
    </Box>
  );

  return (
    <Stack gap={0}>
      {recent.map((chart, idx) => {
        const statusColor = getStatusColor(chart.status);
        const raf = chart.raf_summary?.total_raf_score;
        return (
          <Box
            key={chart.chart_id}
            onClick={() => onViewChart(chart.chart_id)}
            style={{
              display: 'flex', alignItems: 'center', padding: '7px 8px', gap: 10,
              borderBottom: idx < recent.length - 1 ? '1px solid var(--mi-border)' : 'none',
              cursor: 'pointer', transition: 'background-color 0.1s ease', borderRadius: 'var(--mi-radius-sm)',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--mi-surface-hover)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
          >
            <Box style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: `var(--mantine-color-${statusColor}-5, var(--mi-primary))`, flexShrink: 0 }} />
            <Box style={{ flex: 1, minWidth: 0 }}>
              <Text size="xs" fw={600} truncate="end" style={{ color: 'var(--mi-text)' }}>
                {formatChartId(chart.chart_id, chart.filename)}
              </Text>
            </Box>
            {raf != null && (
              <Text size="xs" fw={700} style={{ color: '#8B5CF6', fontVariantNumeric: 'tabular-nums', fontSize: 10, flexShrink: 0 }}>
                {formatRAF(raf)}
              </Text>
            )}
            <Badge size="xs" variant="light" color={statusColor} radius="sm" styles={{ root: { flexShrink: 0, fontSize: 9 } }}>
              {chart.status}
            </Badge>
            <Tooltip label={formatDateTime(chart.started_at)}>
              <Text size="xs" style={{ color: 'var(--mi-text-muted)', flexShrink: 0, fontSize: 10 }}>
                {formatRelativeTime(chart.started_at)}
              </Text>
            </Tooltip>
          </Box>
        );
      })}
    </Stack>
  );
}

/* -------------------------------------------------------------------------- */
/* DB Stats Compact                                                            */
/* -------------------------------------------------------------------------- */
function DBStatsCompact({ dbStats }: { dbStats: DBStats }) {
  const tableData = useMemo(() => {
    let tables = dbStats.tables;
    if (!tables) return [];
    if (!Array.isArray(tables)) {
      if (typeof tables === 'object') {
        tables = Object.entries(tables).map(([name, rows]) => ({ name, rows: typeof rows === 'number' ? rows : Number(rows) || 0 }));
      } else return [];
    }
    return [...tables].filter((t) => t.rows > 0).sort((a, b) => b.rows - a.rows).slice(0, 6);
  }, [dbStats.tables]);

  const totalRows = tableData.reduce((sum, t) => sum + t.rows, 0);

  if (tableData.length === 0) return null;

  return (
    <Stack gap={6}>
      <Group justify="space-between">
        <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>Top tables</Text>
        <Badge size="xs" variant="light" color="blue">{formatNumber(totalRows)} rows</Badge>
      </Group>
      {tableData.map((t) => (
        <Group key={t.name} justify="space-between">
          <Text size="xs" style={{ color: 'var(--mi-text-secondary)', fontSize: 11 }}>
            {t.name.replace(/_/g, ' ')}
          </Text>
          <Text size="xs" fw={600} style={{ color: 'var(--mi-text)', fontVariantNumeric: 'tabular-nums', fontSize: 11 }}>
            {formatNumber(t.rows)}
          </Text>
        </Group>
      ))}
    </Stack>
  );
}

/* -------------------------------------------------------------------------- */
/* Main Dashboard Page                                                         */
/* -------------------------------------------------------------------------- */
export function DashboardPage() {
  const navigate = useNavigate();
  const { setActiveChart } = useChartStore();
  const { data: stats, isLoading: statsLoading, isError: statsError, refetch: refetchStats } = useDashboardStats();
  const { data: dbStats, isLoading: dbLoading } = useDBStats();
  const { data: recentActivity } = useRecentActivity();
  const { data: chartsData } = useCharts();
  const { data: pipelineRuns } = usePipelineRuns();

  const charts = chartsData?.charts ?? [];

  const handleViewChart = useCallback((chartId: string) => {
    setActiveChart(chartId);
    navigate(`/charts/${chartId}`);
  }, [navigate, setActiveChart]);

  if (statsLoading && !stats) return <DashboardSkeleton />;

  const dashStats = stats as DashboardStats | undefined;

  return (
    <Box style={{ padding: 24, maxWidth: 1400, margin: '0 auto', width: '100%' }}>
      <Stack gap={20}>
        {/* Error banner */}
        {statsError && (
          <Alert icon={<IconAlertCircle size={18} />} title="Could not load dashboard stats" color="orange" radius="lg"
            styles={{ root: { backgroundColor: 'color-mix(in srgb, var(--mi-warning) 6%, var(--mi-surface))', borderColor: 'color-mix(in srgb, var(--mi-warning) 20%, transparent)' } }}>
            <Text size="sm" style={{ color: 'var(--mi-text-secondary)' }}>Showing available data below.</Text>
            <Button size="xs" variant="light" color="orange" mt={8} leftSection={<IconRefresh size={14} />} onClick={() => refetchStats()}>Retry</Button>
          </Alert>
        )}

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <Group justify="space-between" align="center">
            <Group gap={12}>
              <ThemeIcon size={36} radius="xl" variant="gradient" gradient={{ from: 'blue', to: 'cyan' }}>
                <IconActivity size={20} stroke={1.8} />
              </ThemeIcon>
              <Box>
                <Text fw={800} style={{ fontSize: 22, color: 'var(--mi-text)', lineHeight: 1.2 }}>Intelligence Hub</Text>
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', marginTop: 2 }}>Risk adjustment, quality metrics, and coding intelligence</Text>
              </Box>
            </Group>
            <Button variant="light" size="xs" leftSection={<IconRefresh size={14} />} onClick={() => refetchStats()}
              style={{ borderRadius: 'var(--mi-radius-full)' }}>
              Refresh
            </Button>
          </Group>
        </motion.div>

        {/* 6 Intelligence Tiles — 3x2 grid */}
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing={16}>
          {/* Tile 1: Risk Score Overview */}
          <IntelTile
            title="Risk Score Overview"
            icon={<IconShieldCheck size={14} stroke={2} color="#8B5CF6" />}
            accentColor="linear-gradient(90deg, #8B5CF6, #A78BFA)"
            index={0}
          >
            <RiskScoreOverview charts={charts} />
          </IntelTile>

          {/* Tile 2: HCC Category Distribution */}
          <IntelTile
            title="Top HCC Categories"
            icon={<IconBrain size={14} stroke={2} color="var(--mi-primary)" />}
            accentColor="linear-gradient(90deg, var(--mi-primary), var(--mi-accent))"
            index={1}
          >
            <HCCDistribution charts={charts} />
          </IntelTile>

          {/* Tile 3: Quality & Compliance */}
          <IntelTile
            title="Quality & Compliance"
            icon={<IconHeartRateMonitor size={14} stroke={2} color="#10B981" />}
            accentColor="linear-gradient(90deg, #10B981, #34D399)"
            index={2}
          >
            <QualityCompliance charts={charts} stats={dashStats} />
          </IntelTile>

          {/* Tile 4: Top Diagnoses */}
          <IntelTile
            title="Top Diagnoses"
            icon={<IconStethoscope size={14} stroke={2} color="#EC4899" />}
            accentColor="linear-gradient(90deg, #EC4899, #F472B6)"
            index={3}
          >
            <TopDiagnoses charts={charts} />
          </IntelTile>

          {/* Tile 5: Processing Pipeline */}
          <IntelTile
            title="Processing Pipeline"
            icon={<IconChartBar size={14} stroke={2} color="#F59E0B" />}
            accentColor="linear-gradient(90deg, #F59E0B, #FBBF24)"
            index={4}
          >
            <ProcessingSummary stats={dashStats} runs={pipelineRuns ?? []} />
          </IntelTile>

          {/* Tile 6: RAF Distribution */}
          <IntelTile
            title="RAF Distribution"
            icon={<IconTrendingUp size={14} stroke={2} color="#06B6D4" />}
            accentColor="linear-gradient(90deg, #06B6D4, #22D3EE)"
            index={5}
          >
            <RAFDistributionChart charts={charts} />
          </IntelTile>
        </SimpleGrid>

        {/* Bottom row: Recent Charts + DB Stats */}
        <SimpleGrid cols={{ base: 1, lg: 2 }} spacing={16}>
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.3 }}>
            <Box className="glass" style={{ borderRadius: 'var(--mi-radius-xl)', padding: 18, boxShadow: 'var(--mi-shadow-md)' }}>
              <Group gap={8} mb={12}>
                <IconFiles size={14} stroke={2} color="var(--mi-primary)" />
                <Text size="xs" fw={700} tt="uppercase" style={{ color: 'var(--mi-text-muted)', letterSpacing: '0.06em', fontSize: 10 }}>
                  Recent Charts
                </Text>
                <Badge size="xs" variant="light" color="blue">{charts.length}</Badge>
              </Group>
              <ScrollArea.Autosize mah={300} type="auto">
                <RecentChartsList charts={charts} onViewChart={handleViewChart} />
              </ScrollArea.Autosize>
            </Box>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45, duration: 0.3 }}>
            <Box className="glass" style={{ borderRadius: 'var(--mi-radius-xl)', padding: 18, boxShadow: 'var(--mi-shadow-md)' }}>
              <Group gap={8} mb={12}>
                <IconDatabase size={14} stroke={2} color="var(--mi-primary)" />
                <Text size="xs" fw={700} tt="uppercase" style={{ color: 'var(--mi-text-muted)', letterSpacing: '0.06em', fontSize: 10 }}>
                  Database
                </Text>
              </Group>
              {dbStats && !dbLoading ? (
                <DBStatsCompact dbStats={dbStats} />
              ) : dbLoading ? (
                <Stack gap={8}>
                  {[1, 2, 3, 4].map((i) => <Skeleton key={i} height={16} radius="md" />)}
                </Stack>
              ) : (
                <Text size="sm" c="dimmed">No DB stats available</Text>
              )}
            </Box>
          </motion.div>
        </SimpleGrid>
      </Stack>
    </Box>
  );
}
