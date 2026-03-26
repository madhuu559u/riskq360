import { Badge } from '@mantine/core';
import {
  IconCheck,
  IconX,
  IconClock,
  IconHistory,
  IconUsers,
  IconQuestionMark,
} from '@tabler/icons-react';
import type { NegationStatus } from '../../types/clinical';
import { getNegationColor, getNegationLabel } from '../../utils/colors';

interface NegationBadgeProps {
  status: NegationStatus;
  size?: 'xs' | 'sm' | 'md' | 'lg';
}

const NEGATION_ICONS: Record<NegationStatus, typeof IconCheck> = {
  active: IconCheck,
  negated: IconX,
  resolved: IconClock,
  historical: IconHistory,
  family_history: IconUsers,
  uncertain: IconQuestionMark,
};

export function NegationBadge({ status, size = 'sm' }: NegationBadgeProps) {
  const Icon = NEGATION_ICONS[status] ?? IconQuestionMark;
  const color = getNegationColor(status);
  const label = getNegationLabel(status);
  const iconSize = size === 'xs' ? 10 : size === 'sm' ? 12 : 14;

  return (
    <Badge
      size={size}
      color={color}
      variant="light"
      radius="md"
      leftSection={<Icon size={iconSize} stroke={2} />}
      styles={{
        root: {
          textTransform: 'none',
          fontWeight: 600,
          letterSpacing: '0.01em',
        },
      }}
    >
      {label}
    </Badge>
  );
}
