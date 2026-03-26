import { useMemo, useState, useCallback } from 'react';
import {
  Box,
  Text,
  Stack,
  Accordion,
  Badge,
  Group,
  Skeleton,
  Alert,
  Button,
  Collapse,
  ActionIcon,
  Tooltip,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconShieldCheck,
  IconAlertCircle,
  IconRefresh,
  IconChevronDown,
  IconChevronUp,
  IconBan,
  IconArrowNarrowRight,
  IconCheck,
  IconX,
} from '@tabler/icons-react';
import { motion } from 'framer-motion';
import { useChartStore } from '../../stores/chartStore';
import { useHCCPack, useHierarchy, useAcceptHCC, useRejectHCC } from '../../hooks/useChart';
import type { HCCCode, UnsupportedCandidate } from '../../types/risk';
import { formatRAF, formatConfidence } from '../../utils/formatters';
import { RAFSummaryCard } from './RAFSummary';
import { HCCCard } from './HCCCard';
import { ReviewModal } from '../shared/ReviewModal';

/* -------------------------------------------------------------------------- */
/* Loading Skeleton                                                            */
/* -------------------------------------------------------------------------- */
function HCCPackSkeleton() {
  return (
    <Stack gap={16} p={16}>
      {/* RAF Summary skeleton */}
      <Box
        style={{
          borderRadius: 'var(--mi-radius-lg)',
          padding: 20,
          border: '1px solid var(--mi-border)',
          backgroundColor: 'var(--mi-surface)',
        }}
      >
        <Skeleton width={100} height={12} mb={8} />
        <Skeleton width={120} height={36} mb={16} />
        <Group gap={16} mb={12}>
          <Skeleton width={70} height={40} />
          <Skeleton width={70} height={40} />
        </Group>
        <Group gap={8}>
          <Skeleton width={100} height={22} radius="md" />
          <Skeleton width={80} height={22} radius="md" />
        </Group>
      </Box>

      {/* HCC cards skeleton */}
      {[1, 2, 3].map((i) => (
        <Box
          key={i}
          style={{
            borderRadius: 'var(--mi-radius-lg)',
            padding: 16,
            border: '1px solid var(--mi-border)',
            backgroundColor: 'var(--mi-surface)',
          }}
        >
          <Group gap={10}>
            <Skeleton width={8} height={8} circle />
            <Skeleton width={70} height={24} radius="md" />
            <Skeleton width={200} height={16} />
            <Box style={{ flex: 1 }} />
            <Skeleton width={50} height={22} radius="md" />
            <Skeleton width={50} height={22} radius="md" />
          </Group>
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
        <IconShieldCheck size={32} stroke={1.2} color="var(--mi-text-muted)" />
      </Box>
      <Text size="md" fw={600} style={{ color: 'var(--mi-text)' }}>
        No HCC Data Available
      </Text>
      <Text size="sm" c="dimmed" ta="center" maw={300}>
        HCC pack data will appear here once the chart has been processed through the risk adjustment pipeline.
      </Text>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Unsupported Candidate Row                                                   */
/* -------------------------------------------------------------------------- */
function UnsupportedCandidateRow({ candidate }: { candidate: UnsupportedCandidate }) {
  return (
    <Box
      style={{
        padding: '10px 14px',
        borderRadius: 'var(--mi-radius-md)',
        backgroundColor: 'var(--mi-surface)',
        border: '1px solid var(--mi-border)',
      }}
    >
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <Group gap={8} align="center" style={{ minWidth: 0 }}>
          <Badge
            size="sm"
            variant="outline"
            color="gray"
            radius="md"
            styles={{
              root: {
                fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                fontWeight: 600,
                textTransform: 'none',
                opacity: 0.7,
                flexShrink: 0,
              },
            }}
          >
            {candidate.icd10_code}
          </Badge>
          <Text
            size="xs"
            style={{
              color: 'var(--mi-text-muted)',
              minWidth: 0,
            }}
            lineClamp={1}
          >
            {candidate.icd10_description}
          </Text>
        </Group>
        <Text
          size="xs"
          fw={600}
          style={{
            color: 'var(--mi-text-muted)',
            flexShrink: 0,
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {formatConfidence(candidate.confidence)}
        </Text>
      </Group>
      <Text
        size="xs"
        mt={6}
        style={{ color: 'var(--mi-error)', opacity: 0.8 }}
      >
        Reason: {candidate.reason}
      </Text>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Hierarchy Section                                                           */
/* -------------------------------------------------------------------------- */
function HierarchySection({ chartId }: { chartId: string }) {
  const { data: hierarchy, isLoading } = useHierarchy(chartId);
  const [opened, { toggle }] = useDisclosure(false);

  const details = hierarchy?.hierarchy_details;

  if (isLoading) return null;
  if (!details || details.length === 0) return null;

  return (
    <Box>
      <Button
        variant="subtle"
        color="gray"
        size="xs"
        onClick={toggle}
        rightSection={opened ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
        styles={{
          root: {
            fontWeight: 600,
            fontSize: 12,
            padding: '4px 8px',
          },
        }}
      >
        Hierarchy Details ({details.length})
      </Button>
      <Collapse in={opened}>
        <Stack gap={6} mt={8}>
          {details.map((detail, idx) => (
            <Group
              key={idx}
              gap={8}
              style={{
                padding: '8px 12px',
                borderRadius: 'var(--mi-radius-md)',
                backgroundColor: 'var(--mi-surface)',
                border: '1px solid var(--mi-border)',
              }}
            >
              <Badge
                size="xs"
                variant="light"
                color="red"
                styles={{
                  root: {
                    fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                    textTransform: 'none',
                    textDecoration: 'line-through',
                  },
                }}
              >
                HCC {detail.suppressed}
              </Badge>
              <IconArrowNarrowRight size={14} stroke={1.5} color="var(--mi-text-muted)" />
              <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>
                suppressed by
              </Text>
              <Badge
                size="xs"
                variant="light"
                color="blue"
                styles={{
                  root: {
                    fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                    textTransform: 'none',
                  },
                }}
              >
                HCC {detail.by}
              </Badge>
              {detail.group && (
                <Badge
                  size="xs"
                  variant="outline"
                  color="gray"
                  styles={{ root: { textTransform: 'none' } }}
                >
                  {detail.group}
                </Badge>
              )}
            </Group>
          ))}
        </Stack>
      </Collapse>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Main HCC Pack Panel                                                         */
/* -------------------------------------------------------------------------- */
export function HCCPackPanel() {
  const activeChartId = useChartStore((s) => s.activeChartId);
  const { data: hccPack, isLoading, isError, refetch } = useHCCPack(activeChartId);
  const [unsupportedOpen, { toggle: toggleUnsupported }] = useDisclosure(false);
  const acceptHCCMutation = useAcceptHCC();
  const rejectHCCMutation = useRejectHCC();
  const [reviewModal, setReviewModal] = useState<{
    open: boolean;
    action: 'accept' | 'reject';
    id: number | string;
    label: string;
  }>({ open: false, action: 'accept', id: 0, label: '' });

  const handleReviewConfirm = useCallback((notes: string) => {
    const { action, id } = reviewModal;
    const payload = { reviewer: 'RiskQ360', notes: notes || null };
    if (action === 'accept') {
      acceptHCCMutation.mutate({ id, payload });
    } else {
      rejectHCCMutation.mutate({ id, payload });
    }
    setReviewModal((m) => ({ ...m, open: false }));
  }, [reviewModal, acceptHCCMutation, rejectHCCMutation]);

  /* Sort HCCs by RAF weight descending */
  const sortedHCCs = useMemo<HCCCode[]>(() => {
    if (!hccPack?.payable_hccs) return [];
    return [...hccPack.payable_hccs].sort((a, b) => b.raf_weight - a.raf_weight);
  }, [hccPack?.payable_hccs]);

  const unsupported = hccPack?.unsupported_candidates ?? [];
  const raf = hccPack?.raf_summary;

  /* Loading */
  if (isLoading) {
    return <HCCPackSkeleton />;
  }

  /* Error */
  if (isError) {
    return (
      <Box p={16}>
        <Alert
          icon={<IconAlertCircle size={18} />}
          title="Failed to load HCC data"
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
            There was an error loading the HCC pack data. The chart may still be processing.
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
  if (!hccPack || sortedHCCs.length === 0) {
    return <EmptyState />;
  }

  return (
    <Box
      style={{
        height: '100%',
        overflow: 'auto',
        padding: 12,
      }}
    >
      <Stack gap={12}>
        {/* RAF Summary Card */}
        {raf && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
          >
            <RAFSummaryCard raf={raf} />
          </motion.div>
        )}

        {/* Section Header */}
        <Group justify="space-between" align="center">
          <Group gap={8} align="center">
            <IconShieldCheck size={16} stroke={1.5} color="var(--mi-primary)" />
            <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
              Payable HCCs
            </Text>
            <Badge size="sm" variant="light" color="blue" radius="md">
              {sortedHCCs.length}
            </Badge>
          </Group>
          <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontVariantNumeric: 'tabular-nums' }}>
            Total RAF: {formatRAF(raf?.total_raf_score ?? 0)}
          </Text>
        </Group>

        {/* HCC Accordion List */}
        <Accordion
          variant="separated"
          radius="lg"
          chevronPosition="left"
          multiple
          styles={{
            root: {
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            },
            item: {
              border: 'none',
              backgroundColor: 'transparent',
            },
            chevron: {
              display: 'none',
            },
          }}
        >
          {sortedHCCs.map((hcc, index) => (
            <motion.div
              key={hcc.hcc_code || `hcc-${index}`}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: Math.min(index * 0.04, 0.3),
                duration: 0.25,
                ease: [0.4, 0, 0.2, 1],
              }}
            >
              <Box style={{ position: 'relative' }}>
                <HCCCard hcc={hcc} />
                {/* Review buttons overlaid at top-right of each card */}
                {!!(hcc as unknown as Record<string, unknown>).id && (
                  <Group
                    gap={4}
                    style={{
                      position: 'absolute',
                      top: 8,
                      right: 48,
                      zIndex: 5,
                    }}
                  >
                    <Tooltip label="Accept HCC" withArrow>
                      <ActionIcon
                        size="xs"
                        variant="light"
                        color="green"
                        onClick={(e) => {
                          e.stopPropagation();
                          const hccId = (hcc as unknown as Record<string, unknown>).id;
                          setReviewModal({ open: true, action: 'accept', id: hccId as number, label: `HCC ${hcc.hcc_code} - ${hcc.hcc_description}` });
                        }}
                      >
                        <IconCheck size={12} stroke={2} />
                      </ActionIcon>
                    </Tooltip>
                    <Tooltip label="Reject HCC" withArrow>
                      <ActionIcon
                        size="xs"
                        variant="light"
                        color="red"
                        onClick={(e) => {
                          e.stopPropagation();
                          const hccId = (hcc as unknown as Record<string, unknown>).id;
                          setReviewModal({ open: true, action: 'reject', id: hccId as number, label: `HCC ${hcc.hcc_code} - ${hcc.hcc_description}` });
                        }}
                      >
                        <IconX size={12} stroke={2} />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                )}
              </Box>
            </motion.div>
          ))}
        </Accordion>

        {/* Hierarchy Section */}
        {activeChartId && <HierarchySection chartId={activeChartId} />}

        {/* Unsupported Candidates */}
        {unsupported.length > 0 && (
          <Box>
            <Button
              variant="subtle"
              color="gray"
              size="xs"
              onClick={toggleUnsupported}
              leftSection={<IconBan size={14} stroke={1.5} />}
              rightSection={
                unsupportedOpen ? (
                  <IconChevronUp size={14} />
                ) : (
                  <IconChevronDown size={14} />
                )
              }
              styles={{
                root: {
                  fontWeight: 600,
                  fontSize: 12,
                  padding: '4px 8px',
                },
              }}
            >
              Unsupported Candidates ({unsupported.length})
            </Button>
            <Collapse in={unsupportedOpen}>
              <Stack gap={8} mt={8}>
                <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>
                  These ICD codes were identified but did not meet the criteria for payable HCC status.
                </Text>
                {unsupported.map((candidate, idx) => (
                  <motion.div
                    key={`${candidate.icd10_code}-${idx}`}
                    initial={{ opacity: 0, x: -4 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.03, duration: 0.2 }}
                  >
                    <UnsupportedCandidateRow candidate={candidate} />
                  </motion.div>
                ))}
              </Stack>
            </Collapse>
          </Box>
        )}
      </Stack>

      {/* Review Modal */}
      <ReviewModal
        opened={reviewModal.open}
        onClose={() => setReviewModal((m) => ({ ...m, open: false }))}
        onConfirm={handleReviewConfirm}
        action={reviewModal.action}
        itemType="HCC"
        itemLabel={reviewModal.label}
        isPending={acceptHCCMutation.isPending || rejectHCCMutation.isPending}
      />
    </Box>
  );
}
