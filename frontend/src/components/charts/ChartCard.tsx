import { useNavigate } from 'react-router-dom';
import { Box, Text, Group, Badge } from '@mantine/core';
import {
  IconShieldCheck,
  IconFileDescription,
  IconCircleCheck,
  IconAlertCircle,
} from '@tabler/icons-react';
import { motion } from 'framer-motion';
import type { Chart } from '../../types/chart';
import { useChartStore } from '../../stores/chartStore';
import { getStatusColor } from '../../utils/colors';
import { formatChartId, formatRAF, formatRelativeTime } from '../../utils/formatters';

interface ChartCardProps {
  chart: Chart;
  index: number;
}

const STATUS_DOT: Record<string, string> = {
  completed: 'var(--mi-success)',
  processing: 'var(--mi-warning)',
  running: 'var(--mi-warning)',
  uploaded: 'var(--mi-info)',
  failed: 'var(--mi-error)',
};

export function ChartCard({ chart, index }: ChartCardProps) {
  const navigate = useNavigate();
  const { setActiveChart } = useChartStore();

  const handleClick = () => {
    setActiveChart(chart.chart_id);
    navigate(`/charts/${chart.chart_id}`);
  };

  const raf = chart.raf_summary;
  const hedis = chart.hedis_summary;
  const dotColor = STATUS_DOT[chart.status] ?? 'var(--mi-text-muted)';
  const isActive = chart.status === 'processing' || chart.status === 'running';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.03, 0.3), duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
    >
      <Box
        onClick={handleClick}
        style={{
          cursor: 'pointer',
          padding: '10px 14px',
          borderRadius: 10,
          backgroundColor: 'var(--mi-surface)',
          border: '1px solid var(--mi-border)',
          transition: 'all var(--mi-transition-fast)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--mi-primary) 40%, transparent)';
          e.currentTarget.style.boxShadow = 'var(--mi-shadow-md)';
          e.currentTarget.style.transform = 'translateY(-1px)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'var(--mi-border)';
          e.currentTarget.style.boxShadow = 'none';
          e.currentTarget.style.transform = 'translateY(0)';
        }}
      >
        {/* Row 1: Status dot + filename + status badge + time */}
        <Group justify="space-between" align="center" gap={8} mb={6} wrap="nowrap">
          <Group gap={8} align="center" wrap="nowrap" style={{ minWidth: 0, flex: 1 }}>
            <Box
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                backgroundColor: dotColor,
                flexShrink: 0,
                boxShadow: isActive ? `0 0 6px ${dotColor}` : 'none',
                animation: isActive ? 'mi-pulse-glow 2s infinite' : 'none',
              }}
            />
            <Box style={{ minWidth: 0 }}>
              <Text
                size="sm"
                fw={600}
                style={{ color: 'var(--mi-text)', lineHeight: 1.2 }}
                lineClamp={1}
              >
                {formatChartId(chart.chart_id, chart.filename)}
              </Text>
              {chart.patient_name && (
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10, lineHeight: 1.2 }} lineClamp={1}>
                  {chart.patient_name}
                </Text>
              )}
            </Box>
          </Group>

          <Group gap={6} wrap="nowrap" style={{ flexShrink: 0 }}>
            <Badge
              size="xs"
              variant="light"
              color={getStatusColor(chart.status)}
              radius="sm"
              styles={{ root: { textTransform: 'none', fontWeight: 600, fontSize: 10 } }}
            >
              {chart.status}
            </Badge>
            <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10, whiteSpace: 'nowrap' }}>
              {chart.completed_at
                ? formatRelativeTime(chart.completed_at)
                : chart.started_at
                  ? formatRelativeTime(chart.started_at)
                  : '--'}
            </Text>
          </Group>
        </Group>

        {/* Row 2: RAF score + HCCs + MET + GAP + pages */}
        <Group gap={8} wrap="wrap">
          {/* RAF Score */}
          {raf && raf.total_raf_score > 0 ? (
            <Badge
              size="sm"
              variant="filled"
              radius="sm"
              styles={{
                root: {
                  background: 'linear-gradient(135deg, var(--mi-primary), var(--mi-accent))',
                  textTransform: 'none',
                  fontWeight: 700,
                  fontVariantNumeric: 'tabular-nums',
                  fontSize: 11,
                  paddingLeft: 8,
                  paddingRight: 8,
                },
              }}
            >
              RAF {formatRAF(raf.total_raf_score)}
            </Badge>
          ) : chart.status === 'completed' ? (
            <Badge
              size="sm"
              variant="light"
              color="gray"
              radius="sm"
              styles={{ root: { textTransform: 'none', fontSize: 10 } }}
            >
              RAF --
            </Badge>
          ) : null}

          {/* HCC count */}
          {raf && raf.payable_hcc_count > 0 && (
            <Badge
              size="sm"
              variant="light"
              color="blue"
              radius="sm"
              leftSection={<IconShieldCheck size={10} stroke={2} />}
              styles={{ root: { textTransform: 'none', fontWeight: 600, fontSize: 10 } }}
            >
              {raf.payable_hcc_count} HCC{raf.payable_hcc_count !== 1 ? 's' : ''}
            </Badge>
          )}

          {/* HEDIS MET */}
          {hedis && hedis.met_count > 0 && (
            <Badge
              size="sm"
              variant="light"
              color="green"
              radius="sm"
              leftSection={<IconCircleCheck size={10} stroke={2} />}
              styles={{ root: { textTransform: 'none', fontWeight: 600, fontSize: 10 } }}
            >
              {hedis.met_count} MET
            </Badge>
          )}

          {/* HEDIS GAP */}
          {hedis && hedis.gap_count > 0 && (
            <Badge
              size="sm"
              variant="light"
              color="red"
              radius="sm"
              leftSection={<IconAlertCircle size={10} stroke={2} />}
              styles={{ root: { textTransform: 'none', fontWeight: 600, fontSize: 10 } }}
            >
              {hedis.gap_count} GAP{hedis.gap_count !== 1 ? 's' : ''}
            </Badge>
          )}

          {/* Pages */}
          {chart.pages_processed != null && (
            <Badge
              size="sm"
              variant="light"
              color="gray"
              radius="sm"
              leftSection={<IconFileDescription size={10} stroke={1.8} />}
              styles={{ root: { textTransform: 'none', fontWeight: 500, fontSize: 10 } }}
            >
              {chart.pages_processed} pg
            </Badge>
          )}
        </Group>
      </Box>
    </motion.div>
  );
}
