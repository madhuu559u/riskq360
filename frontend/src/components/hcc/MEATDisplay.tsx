import { Group, Box, Text, Tooltip } from '@mantine/core';
import { IconCheck, IconX } from '@tabler/icons-react';
import type { MEATEvidence } from '../../types/risk';

interface MEATDisplayProps {
  meat: MEATEvidence | null;
  compact?: boolean;
}

interface LetterConfig {
  key: keyof Pick<MEATEvidence, 'monitored' | 'evaluated' | 'assessed' | 'treated'>;
  letter: string;
  fullName: string;
  textKey: keyof Pick<MEATEvidence, 'monitoring_text' | 'evaluation_text' | 'assessment_text' | 'treatment_text'>;
}

const MEAT_LETTERS: LetterConfig[] = [
  { key: 'monitored', letter: 'M', fullName: 'Monitoring', textKey: 'monitoring_text' },
  { key: 'evaluated', letter: 'E', fullName: 'Evaluation', textKey: 'evaluation_text' },
  { key: 'assessed', letter: 'A', fullName: 'Assessment', textKey: 'assessment_text' },
  { key: 'treated', letter: 'T', fullName: 'Treatment', textKey: 'treatment_text' },
];

export function MEATDisplay({ meat, compact = false }: MEATDisplayProps) {
  if (!meat) {
    return (
      <Group gap={3}>
        {MEAT_LETTERS.map((item) => (
          <Tooltip key={item.letter} label={`${item.fullName}: No data`} withArrow>
            <Box
              style={{
                width: compact ? 22 : 26,
                height: compact ? 22 : 26,
                borderRadius: 'var(--mi-radius-sm)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'var(--mi-surface-hover)',
                border: '1px solid var(--mi-border)',
              }}
            >
              <Text
                size="xs"
                fw={700}
                style={{
                  fontSize: compact ? 10 : 11,
                  color: 'var(--mi-text-muted)',
                  lineHeight: 1,
                }}
              >
                {item.letter}
              </Text>
            </Box>
          </Tooltip>
        ))}
      </Group>
    );
  }

  const metCount = MEAT_LETTERS.filter((item) => meat[item.key]).length;

  return (
    <Group gap={3}>
      {MEAT_LETTERS.map((item) => {
        const isMet = meat[item.key];
        const evidenceText = meat[item.textKey];
        const tooltipContent = isMet
          ? evidenceText
            ? `${item.fullName}: ${evidenceText}`
            : `${item.fullName}: Present`
          : `${item.fullName}: Not found`;

        return (
          <Tooltip
            key={item.letter}
            label={tooltipContent}
            withArrow
            multiline
            maw={320}
            styles={{
              tooltip: {
                fontSize: 12,
                lineHeight: 1.4,
                whiteSpace: 'normal',
              },
            }}
          >
            <Box
              style={{
                width: compact ? 22 : 26,
                height: compact ? 22 : 26,
                borderRadius: 'var(--mi-radius-sm)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: isMet
                  ? 'color-mix(in srgb, var(--mi-success) 12%, var(--mi-surface))'
                  : 'var(--mi-surface-hover)',
                border: isMet
                  ? '1px solid color-mix(in srgb, var(--mi-success) 30%, transparent)'
                  : '1px solid var(--mi-border)',
                position: 'relative',
                transition: 'all var(--mi-transition-fast)',
                cursor: 'default',
              }}
            >
              <Text
                size="xs"
                fw={700}
                style={{
                  fontSize: compact ? 10 : 11,
                  color: isMet ? 'var(--mi-success)' : 'var(--mi-text-muted)',
                  lineHeight: 1,
                }}
              >
                {item.letter}
              </Text>
              {/* Small check/x indicator at top-right corner */}
              <Box
                style={{
                  position: 'absolute',
                  top: -3,
                  right: -3,
                  width: compact ? 10 : 12,
                  height: compact ? 10 : 12,
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: isMet ? 'var(--mi-success)' : 'var(--mi-text-muted)',
                }}
              >
                {isMet ? (
                  <IconCheck size={compact ? 6 : 8} stroke={3} color="#FFFFFF" />
                ) : (
                  <IconX size={compact ? 6 : 8} stroke={3} color="#FFFFFF" />
                )}
              </Box>
            </Box>
          </Tooltip>
        );
      })}
      {/* Summary fraction */}
      {!compact && (
        <Text
          size="xs"
          fw={600}
          style={{
            color: metCount === 4 ? 'var(--mi-success)' : metCount >= 2 ? 'var(--mi-warning)' : 'var(--mi-text-muted)',
            marginLeft: 4,
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {metCount}/4
        </Text>
      )}
    </Group>
  );
}
