import { Box, Text, Tooltip } from '@mantine/core';

interface ConfidenceBarProps {
  confidence: number;
  label?: string;
  showLabel?: boolean;
  size?: 'xs' | 'sm' | 'md';
  width?: number | string;
}

function getConfidenceGradient(value: number): string {
  if (value >= 0.8) return 'linear-gradient(90deg, #10B981, #34D399)';
  if (value >= 0.6) return 'linear-gradient(90deg, #F59E0B, #FBBF24)';
  if (value >= 0.4) return 'linear-gradient(90deg, #F97316, #FB923C)';
  return 'linear-gradient(90deg, #EF4444, #F87171)';
}

function getConfidenceLabel(value: number): string {
  if (value >= 0.9) return 'Very High';
  if (value >= 0.8) return 'High';
  if (value >= 0.6) return 'Moderate';
  if (value >= 0.4) return 'Low';
  return 'Very Low';
}

const SIZE_MAP = {
  xs: { height: 4, fontSize: 10 as const },
  sm: { height: 6, fontSize: 11 as const },
  md: { height: 8, fontSize: 12 as const },
} as const;

export function ConfidenceBar({
  confidence,
  label,
  showLabel = true,
  size = 'sm',
  width = '100%',
}: ConfidenceBarProps) {
  const pct = Math.max(0, Math.min(1, confidence)) * 100;
  const sizeConfig = SIZE_MAP[size];
  const displayLabel = label ?? `${pct.toFixed(0)}%`;
  const tooltipLabel = `${getConfidenceLabel(confidence)} (${(confidence * 100).toFixed(1)}%)`;

  return (
    <Tooltip label={tooltipLabel} withArrow>
      <Box
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          width,
          minWidth: 0,
        }}
      >
        <Box
          style={{
            flex: 1,
            height: sizeConfig.height,
            borderRadius: 'var(--mi-radius-full)',
            backgroundColor: 'var(--mi-border)',
            overflow: 'hidden',
            minWidth: 0,
          }}
        >
          <Box
            style={{
              width: `${pct}%`,
              height: '100%',
              borderRadius: 'var(--mi-radius-full)',
              background: getConfidenceGradient(confidence),
              transition: 'width var(--mi-transition-normal)',
            }}
          />
        </Box>
        {showLabel && (
          <Text
            size="xs"
            fw={600}
            style={{
              fontSize: sizeConfig.fontSize,
              color: 'var(--mi-text-secondary)',
              flexShrink: 0,
              fontVariantNumeric: 'tabular-nums',
              minWidth: 28,
              textAlign: 'right',
            }}
          >
            {displayLabel}
          </Text>
        )}
      </Box>
    </Tooltip>
  );
}
