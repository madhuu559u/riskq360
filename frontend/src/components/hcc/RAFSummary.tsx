import { Box, Text, Group, Stack, Badge } from '@mantine/core';
import {
  IconShieldCheck,
  IconUser,
  IconChartDonut2,
  IconArrowUp,
  IconArrowDown,
} from '@tabler/icons-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts';
import type { RAFSummary as RAFSummaryType } from '../../types/risk';
import { formatRAF, formatNumber } from '../../utils/formatters';

interface RAFSummaryProps {
  raf: RAFSummaryType;
}

const DONUT_COLORS = ['var(--mi-primary)', 'var(--mi-accent)'];

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number }>;
}

function CustomTooltipContent({ active, payload }: CustomTooltipProps) {
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
      <Text size="xs" fw={600} style={{ color: 'var(--mi-text)' }}>
        {entry.name}
      </Text>
      <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
        {formatRAF(entry.value)}
      </Text>
    </Box>
  );
}

export function RAFSummaryCard({ raf }: RAFSummaryProps) {
  const donutData = [
    { name: 'Demographic RAF', value: raf.demographic_raf },
    { name: 'HCC RAF', value: raf.hcc_raf },
  ];

  return (
    <Box
      className="glass"
      style={{
        borderRadius: 12,
        padding: 14,
        boxShadow: 'var(--mi-shadow-md)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Subtle gradient overlay */}
      <Box
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          background: 'linear-gradient(90deg, var(--mi-primary), var(--mi-accent))',
          borderRadius: 'var(--mi-radius-lg) var(--mi-radius-lg) 0 0',
        }}
      />

      <Group align="flex-start" gap={20} wrap="nowrap">
        {/* Left: RAF Score + Stats */}
        <Stack gap={12} style={{ flex: 1, minWidth: 0 }}>
          {/* Total RAF */}
          <Box>
            <Text
              size="xs"
              fw={500}
              tt="uppercase"
              style={{
                color: 'var(--mi-text-muted)',
                letterSpacing: '0.06em',
                fontSize: 10,
                marginBottom: 4,
              }}
            >
              Total RAF Score
            </Text>
            <Text
              fw={800}
              className="gradient-text"
              style={{
                fontSize: 36,
                lineHeight: 1,
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              {formatRAF(raf.total_raf_score)}
            </Text>
          </Box>

          {/* Breakdown row */}
          <Group gap={16}>
            <Box>
              <Group gap={4} mb={2}>
                <IconUser size={12} stroke={1.5} color="var(--mi-text-muted)" />
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>
                  Demographic
                </Text>
              </Group>
              <Text
                size="sm"
                fw={700}
                style={{
                  color: 'var(--mi-text)',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {formatRAF(raf.demographic_raf)}
              </Text>
            </Box>
            <Box
              style={{
                width: 1,
                height: 28,
                backgroundColor: 'var(--mi-border)',
              }}
            />
            <Box>
              <Group gap={4} mb={2}>
                <IconShieldCheck size={12} stroke={1.5} color="var(--mi-text-muted)" />
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>
                  HCC
                </Text>
              </Group>
              <Text
                size="sm"
                fw={700}
                style={{
                  color: 'var(--mi-text)',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {formatRAF(raf.hcc_raf)}
              </Text>
            </Box>
          </Group>

          {/* Stats chips */}
          <Group gap={8} wrap="wrap">
            <Badge
              size="sm"
              variant="light"
              color="blue"
              leftSection={<IconShieldCheck size={10} stroke={2} />}
              styles={{ root: { textTransform: 'none' } }}
            >
              {raf.payable_hcc_count} Payable HCC{raf.payable_hcc_count !== 1 ? 's' : ''}
            </Badge>
            {raf.suppressed_hcc_count > 0 && (
              <Badge
                size="sm"
                variant="light"
                color="gray"
                leftSection={<IconArrowDown size={10} stroke={2} />}
                styles={{ root: { textTransform: 'none' } }}
              >
                {raf.suppressed_hcc_count} Suppressed
              </Badge>
            )}
            {raf.segment && (
              <Badge
                size="sm"
                variant="light"
                color="violet"
                leftSection={<IconArrowUp size={10} stroke={2} />}
                styles={{ root: { textTransform: 'none' } }}
              >
                {raf.segment}
              </Badge>
            )}
          </Group>
        </Stack>

        {/* Right: Donut Chart */}
        <Box
          style={{
            width: 110,
            height: 110,
            flexShrink: 0,
            position: 'relative',
            minWidth: 1,
            minHeight: 1,
          }}
        >
          <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
            <PieChart>
              <Pie
                data={donutData}
                cx="50%"
                cy="50%"
                innerRadius={32}
                outerRadius={50}
                paddingAngle={3}
                dataKey="value"
                strokeWidth={0}
              >
                {donutData.map((_entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={DONUT_COLORS[index % DONUT_COLORS.length]}
                    style={{ filter: 'drop-shadow(0 1px 3px rgba(0,0,0,0.12))' }}
                  />
                ))}
              </Pie>
              <RechartsTooltip content={<CustomTooltipContent />} />
            </PieChart>
          </ResponsiveContainer>
          {/* Center label */}
          <Box
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              textAlign: 'center',
              pointerEvents: 'none',
            }}
          >
            <IconChartDonut2
              size={16}
              stroke={1.5}
              color="var(--mi-text-muted)"
            />
          </Box>
        </Box>
      </Group>

      {/* HCC Count row */}
      <Box
        style={{
          marginTop: 16,
          paddingTop: 12,
          borderTop: '1px solid var(--mi-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>
          Total HCCs: {formatNumber(raf.hcc_count)}
        </Text>
        <Text
          size="xs"
          style={{
            color: 'var(--mi-text-muted)',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {raf.hcc_details?.length ?? 0} categories
        </Text>
      </Box>
    </Box>
  );
}
