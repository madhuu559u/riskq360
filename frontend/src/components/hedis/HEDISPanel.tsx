import { useEffect, useMemo, useState, useCallback, useRef, type ReactNode } from 'react';
import {
  Box,
  Text,
  Stack,
  Group,
  Badge,
  Skeleton,
  Alert,
  Button,
  Collapse,
  RingProgress,
  TextInput,
  Divider,
  SegmentedControl,
  ActionIcon,
  Tooltip,
  HoverCard,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconHeartRateMonitor,
  IconAlertCircle,
  IconRefresh,
  IconCheck,
  IconX,
  IconMinus,
  IconChevronDown,
  IconChevronUp,
  IconAlertTriangle,
  IconArrowRight,
  IconSearch,
  IconShieldCheck,
  IconFileText,
  IconListCheck,
} from '@tabler/icons-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChartStore } from '../../stores/chartStore';
import { useHEDISMeasures, useAcceptHEDIS, useRejectHEDIS } from '../../hooks/useChart';
import type { HEDISMeasure, HEDISGapItem, HEDISEvidenceItem, MeasureStatus } from '../../types/hedis';
import { getMeasureStatusColor, getMeasureStatusLabel } from '../../utils/colors';
import { EvidenceSnippet } from '../shared/EvidenceSnippet';
import { ReviewModal } from '../shared/ReviewModal';

function HEDISSkeleton() {
  return (
    <Stack gap={16} p={16}>
      <Group gap={12}>
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} width={120} height={64} radius="md" style={{ flex: 1 }} />
        ))}
      </Group>
      {[1, 2, 3, 4].map((i) => (
        <Box
          key={i}
          style={{
            borderRadius: 'var(--mi-radius-lg)',
            padding: 16,
            border: '1px solid var(--mi-border)',
            backgroundColor: 'var(--mi-surface)',
          }}
        >
          <Group gap={10} mb={8}>
            <Skeleton width={70} height={24} radius="md" />
            <Skeleton width={220} height={16} />
            <Box style={{ flex: 1 }} />
            <Skeleton width={70} height={22} radius="md" />
          </Group>
          <Skeleton height={14} width="85%" />
        </Box>
      ))}
    </Stack>
  );
}

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
        <IconHeartRateMonitor size={32} stroke={1.2} color="var(--mi-text-muted)" />
      </Box>
      <Text size="md" fw={600} style={{ color: 'var(--mi-text)' }}>
        No Care Gap Data Available
      </Text>
      <Text size="sm" c="dimmed" ta="center" maw={340}>
        HEDIS quality measures will appear here once the chart has been processed through the pipeline.
      </Text>
    </Box>
  );
}

function StatusIcon({ status }: { status: MeasureStatus }) {
  const size = 16;
  const stroke = 2.5;
  if (status === 'met') return <IconCheck size={size} stroke={stroke} color="var(--mi-success)" />;
  if (status === 'gap') return <IconX size={size} stroke={stroke} color="var(--mi-error)" />;
  return <IconMinus size={size} stroke={stroke} color="var(--mi-text-muted)" />;
}

function StatCard({
  label,
  value,
  color,
  icon,
  active = false,
  onClick,
}: {
  label: string;
  value: number;
  color: string;
  icon: ReactNode;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <Box
      onClick={onClick}
      style={{
        flex: 1,
        minWidth: 72,
        padding: '8px 10px',
        borderRadius: 10,
        position: 'relative',
        overflow: 'hidden',
        cursor: onClick ? 'pointer' : 'default',
        border: active ? `1.5px solid ${color}` : '1px solid var(--mi-border)',
        background: active
          ? `color-mix(in srgb, ${color} 6%, var(--mi-surface))`
          : 'var(--mi-surface)',
        transform: active ? 'translateY(-1px)' : 'translateY(0)',
        boxShadow: active ? `0 2px 8px color-mix(in srgb, ${color} 15%, transparent)` : 'none',
        transition: 'all var(--mi-transition-fast)',
      }}
    >
      <Box style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: color, borderRadius: '10px 10px 0 0' }} />
      <Group gap={4} mb={2}>
        {icon}
        <Text size="xs" fw={700} tt="uppercase" style={{ color: 'var(--mi-text-muted)', letterSpacing: '0.04em', fontSize: 9 }}>
          {label}
        </Text>
      </Group>
      <Text fw={800} style={{ fontSize: 20, lineHeight: 1, color: 'var(--mi-text)', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </Text>
    </Box>
  );
}

function renderEvidenceMeta(ev: HEDISEvidenceItem) {
  const source = (ev.source ?? {}) as Record<string, unknown>;
  const page = Number(ev.page_number ?? source.page);
  const date = String(ev.date ?? '');
  const code = String(ev.code ?? '');
  const value = ev.value;

  return (
    <Group gap={6} wrap="wrap" mt={6}>
      {Number.isFinite(page) && page > 0 && (
        <Badge size="xs" variant="light" color="teal" radius="sm" styles={{ root: { textTransform: 'none' } }}>
          Page {page}
        </Badge>
      )}
      {date && (
        <Badge size="xs" variant="light" color="blue" radius="sm" styles={{ root: { textTransform: 'none' } }}>
          {date}
        </Badge>
      )}
      {code && (
        <Badge size="xs" variant="light" color="violet" radius="sm" styles={{ root: { textTransform: 'none' } }}>
          {code}
        </Badge>
      )}
      {value !== undefined && value !== null && (
        <Badge size="xs" variant="light" color="grape" radius="sm" styles={{ root: { textTransform: 'none' } }}>
          {String(value)}
        </Badge>
      )}
    </Group>
  );
}


function coerceMeasureStatus(status: unknown, fallback: MeasureStatus): MeasureStatus {
  const value = String(status ?? '').toLowerCase();
  if (
    value === 'met' ||
    value === 'gap' ||
    value === 'not_applicable' ||
    value === 'excluded' ||
    value === 'indeterminate' ||
    value === 'inactive'
  ) {
    return value as MeasureStatus;
  }
  return fallback;
}

function summarizeEvidence(ev: HEDISEvidenceItem): string {
  const source = (ev.source ?? {}) as Record<string, unknown>;
  const parts: string[] = [];
  const type = String(ev.type ?? '').trim();
  if (type && type.toLowerCase() !== 'evidence') parts.push(type);
  if (ev.code) parts.push(`Code: ${String(ev.code)}`);
  if (ev.system) parts.push(`System: ${String(ev.system)}`);
  if (ev.value !== undefined && ev.value !== null) parts.push(`Value: ${String(ev.value)}`);
  if (ev.date) parts.push(`Date: ${String(ev.date)}`);
  if (ev.systolic !== undefined && ev.diastolic !== undefined) parts.push(`BP: ${ev.systolic}/${ev.diastolic}`);
  if (ev.location) parts.push(`Location: ${String(ev.location)}`);
  if (!parts.length && source.exact_quote) parts.push('Source quote available');
  return parts.join(' | ') || 'No quoted evidence persisted in strict payload';
}

function humanizeToken(raw: string): string {
  const value = String(raw || '').trim();
  if (!value) return '';
  return value
    .replace(/^VS_/, '')
    .replace(/_/g, ' ')
    .replace(/\bICD10\b/g, 'ICD-10')
    .replace(/\bCPT\b/g, 'CPT')
    .replace(/\bHCPCS\b/g, 'HCPCS')
    .replace(/\bLOINC\b/g, 'LOINC')
    .toLowerCase()
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function buildMeaningfulGapText(gap: {
  description?: string;
  required_event?: string;
  required_event_name?: string;
  actionable_reason?: string;
  window?: string;
}): string {
  const actionable = String(gap.actionable_reason ?? '').trim();
  if (actionable) return actionable;

  const base = String(gap.description ?? '').trim();
  const required = String(gap.required_event ?? '').trim();
  const requiredName = String(gap.required_event_name ?? '').trim();
  const reqHuman = requiredName || humanizeToken(required);
  if (!base && required) return `No evidence found for required event: ${reqHuman}.`;
  if (base.toLowerCase().startsWith('missing procedure from ') && required) {
    return `Required screening/procedure not found in chart: ${reqHuman}.`;
  }
  if (base.toLowerCase().startsWith('missing diagnosis') && required) {
    return `Required diagnosis evidence not found: ${reqHuman}.`;
  }
  if (base.toLowerCase().startsWith('missing') && required) {
    return `${humanizeToken(base)} (${reqHuman}).`;
  }
  if (base && !base.includes('VS_')) return base;
  return humanizeToken(base) || `Evidence gap for ${reqHuman}.`;
}

function hasQuotedEvidence(items: HEDISEvidenceItem[] | undefined): boolean {
  if (!items?.length) return false;
  return items.some((ev) => {
    const source = (ev.source ?? {}) as Record<string, unknown>;
    return Boolean(String(ev.exact_quote ?? source.exact_quote ?? '').trim());
  });
}
function MeasureCard({ measure, index, viewMode, onAccept, onReject, isOpen, onToggle }: {
  measure: HEDISMeasure;
  index: number;
  viewMode: 'strict' | 'preview';
  onAccept?: (id: string | number) => void;
  onReject?: (id: string | number) => void;
  isOpen?: boolean;
  onToggle?: () => void;
}) {
  const [internalOpened, { toggle: internalToggle }] = useDisclosure(false);
  const opened = isOpen ?? internalOpened;
  const toggle = onToggle ?? internalToggle;
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (opened && cardRef.current) {
      setTimeout(() => {
        cardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 100);
    }
  }, [opened]);
  const evidenceItems = measure.evidence ?? [];
  const previewEvidence = measure.clinical_only_preview?.evidence_used ?? [];
  const previewActive = viewMode === 'preview' && Boolean(measure.clinical_only_preview);
  const effectiveStatus = previewActive
    ? coerceMeasureStatus(measure.clinical_only_preview?.status, measure.status)
    : measure.status;
  const effectiveEvidence = previewActive ? previewEvidence : evidenceItems;
  const effectiveGaps = previewActive
    ? (measure.clinical_only_preview?.gaps ?? measure.gaps ?? [])
    : (measure.gaps ?? []);
  const effectiveReasons = previewActive
    ? (measure.clinical_only_preview?.compliance_reason ?? [])
    : (measure.compliance_reason ?? []);
  const effectiveTrace = previewActive
    ? (measure.clinical_only_preview?.trace ?? measure.trace ?? [])
    : (measure.trace ?? []);
  const statusColor = getMeasureStatusColor(effectiveStatus);
  const statusLabel = getMeasureStatusLabel(effectiveStatus);
  const hasExpandableContent =
    evidenceItems.length > 0 ||
    Boolean(measure.decision_reasoning) ||
    Boolean(measure.clinical_only_preview) ||
    (measure.trace?.length ?? 0) > 0 ||
    effectiveGaps.length > 0;

  return (
    <motion.div
      ref={cardRef}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ delay: Math.min(index * 0.03, 0.25), duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
    >
      <Box
        style={{
          borderRadius: 10,
          backgroundColor: 'var(--mi-surface)',
          border: opened ? `1px solid color-mix(in srgb, var(--mantine-color-${statusColor}-5, ${statusColor}) 30%, var(--mi-border))` : '1px solid var(--mi-border)',
          overflow: 'hidden',
          transition: 'all var(--mi-transition-fast)',
          boxShadow: opened ? 'var(--mi-shadow-sm)' : 'none',
        }}
      >
        <Box
          onClick={hasExpandableContent ? toggle : undefined}
          style={{
            padding: '10px 12px',
            cursor: hasExpandableContent ? 'pointer' : 'default',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <Box
            style={{
              width: 28,
              height: 28,
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: `color-mix(in srgb, var(--mantine-color-${statusColor}-5, ${statusColor}) 10%, var(--mi-surface))`,
              border: `1px solid color-mix(in srgb, var(--mantine-color-${statusColor}-5, ${statusColor}) 20%, transparent)`,
              flexShrink: 0,
            }}
          >
            <StatusIcon status={effectiveStatus} />
          </Box>

          <Badge
            size="sm"
            variant="filled"
            color="blue"
            radius="md"
            styles={{
              root: {
                fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                fontWeight: 700,
                fontSize: 10,
                textTransform: 'none',
                flexShrink: 0,
              },
            }}
          >
            {measure.measure_code}
          </Badge>

          <HoverCard openDelay={300} position="bottom" width={340} shadow="lg" withArrow>
            <HoverCard.Target>
              <Text size="sm" fw={600} style={{ color: 'var(--mi-text)', flex: 1, minWidth: 0, cursor: 'default' }} lineClamp={1}>
                {measure.measure_name}
              </Text>
            </HoverCard.Target>
            <HoverCard.Dropdown
              className="glass"
              style={{
                padding: 14,
                borderRadius: 'var(--mi-radius-lg)',
                boxShadow: 'var(--mi-shadow-lg)',
              }}
            >
              <Stack gap={10}>
                <Group gap={8} align="center">
                  <Badge
                    size="md"
                    variant="filled"
                    color="blue"
                    radius="md"
                    styles={{ root: { fontFamily: '"JetBrains Mono", "Fira Code", monospace', fontWeight: 700, textTransform: 'none' } }}
                  >
                    {measure.measure_code}
                  </Badge>
                  <Badge size="sm" color={statusColor} variant="light" radius="md" styles={{ root: { textTransform: 'none' } }}>
                    {statusLabel}
                  </Badge>
                </Group>
                <Text size="sm" fw={600} style={{ color: 'var(--mi-text)', lineHeight: 1.4 }}>
                  {measure.measure_name}
                </Text>
                <Group gap={12}>
                  <Box>
                    <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 9 }}>Eligible</Text>
                    <Text size="xs" fw={600} style={{ color: 'var(--mi-text)' }}>{measure.eligible ? 'Yes' : 'No'}</Text>
                  </Box>
                  <Box>
                    <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 9 }}>Evidence</Text>
                    <Text size="xs" fw={600} style={{ color: 'var(--mi-text)' }}>{effectiveEvidence.length}</Text>
                  </Box>
                  <Box>
                    <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 9 }}>Gaps</Text>
                    <Text size="xs" fw={600} style={{ color: effectiveGaps.length > 0 ? 'var(--mi-error)' : 'var(--mi-text)' }}>{effectiveGaps.length}</Text>
                  </Box>
                </Group>
                {(measure.eligibility_reason?.length ?? 0) > 0 && (
                  <Box>
                    <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 9, marginBottom: 2 }}>Eligibility</Text>
                    <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }} lineClamp={2}>
                      {(measure.eligibility_reason ?? []).slice(0, 2).join(' | ')}
                    </Text>
                  </Box>
                )}
                {effectiveReasons.length > 0 && (
                  <Box
                    style={{
                      padding: '6px 10px',
                      borderRadius: 'var(--mi-radius-sm)',
                      backgroundColor: `color-mix(in srgb, var(--mantine-color-${statusColor}-5, ${statusColor}) 6%, var(--mi-surface))`,
                    }}
                  >
                    <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }} lineClamp={2}>
                      {effectiveReasons[0]}
                    </Text>
                  </Box>
                )}
              </Stack>
            </HoverCard.Dropdown>
          </HoverCard>

          <Badge size="sm" color={statusColor} variant="light" radius="md" styles={{ root: { textTransform: 'none', flexShrink: 0 } }}>
            {statusLabel}{previewActive ? ' (Preview)' : ''}
          </Badge>

          {/* Accept/Reject buttons */}
          {(measure.id || measure.measure_id) && onAccept && onReject && (
            <Group gap={3} style={{ flexShrink: 0 }} onClick={(e) => e.stopPropagation()}>
              <Tooltip label="Accept measure" withArrow>
                <ActionIcon size="xs" variant="light" color="green" onClick={() => onAccept(measure.id ?? measure.measure_id ?? '')}>
                  <IconCheck size={12} stroke={2} />
                </ActionIcon>
              </Tooltip>
              <Tooltip label="Reject measure" withArrow>
                <ActionIcon size="xs" variant="light" color="red" onClick={() => onReject(measure.id ?? measure.measure_id ?? '')}>
                  <IconX size={12} stroke={2} />
                </ActionIcon>
              </Tooltip>
            </Group>
          )}

          {hasExpandableContent && (
            <Box style={{ flexShrink: 0, color: 'var(--mi-text-muted)' }}>
              {opened ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
            </Box>
          )}
        </Box>

        <Collapse in={opened}>
          <Box style={{ padding: '0 16px 14px', borderTop: '1px solid var(--mi-border)', marginTop: -1, paddingTop: 14 }}>
            <Stack gap={10}>
              {measure.decision_reasoning && (
                <Box
                  style={{
                    padding: '10px 12px',
                    borderRadius: 'var(--mi-radius-md)',
                    backgroundColor: 'color-mix(in srgb, var(--mi-info) 6%, var(--mi-surface))',
                    border: '1px solid color-mix(in srgb, var(--mi-info) 15%, transparent)',
                  }}
                >
                  <Text size="xs" fw={700} mb={4} style={{ color: 'var(--mi-text)' }}>
                    Decision Summary
                  </Text>
                  <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                    Rule Trace: {measure.decision_reasoning.rule_trace_count ?? 0} | Evidence: {measure.decision_reasoning.evidence_count ?? 0}
                  </Text>
                  {(measure.decision_reasoning.evidence_pages?.length ?? 0) > 0 && (
                    <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                      Pages: {(measure.decision_reasoning.evidence_pages ?? []).join(', ')}
                    </Text>
                  )}
                </Box>
              )}

              {measure.measure_definition && (
                <Box
                  style={{
                    padding: '10px 12px',
                    borderRadius: 'var(--mi-radius-md)',
                    backgroundColor: 'color-mix(in srgb, var(--mi-primary) 5%, var(--mi-surface))',
                    border: '1px solid color-mix(in srgb, var(--mi-primary) 16%, transparent)',
                  }}
                >
                  <Text size="xs" fw={700} mb={4} style={{ color: 'var(--mi-text)' }}>
                    Measure Rule Definition
                  </Text>
                  <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                    {(measure.measure_definition.domain ? `${humanizeToken(measure.measure_definition.domain)} | ` : '')}
                    Age: {measure.measure_definition.eligibility?.age ?? 'Any'} | Gender: {measure.measure_definition.eligibility?.gender ?? 'All'}
                    {measure.measure_definition.eligibility?.continuous_enrollment_required ? ' | Continuous enrollment required' : ''}
                  </Text>

                  {(measure.measure_definition.denominator_rules?.length ?? 0) > 0 && (
                    <Text size="xs" mt={4} style={{ color: 'var(--mi-text-secondary)' }}>
                      Denominator: {(measure.measure_definition.denominator_rules ?? []).slice(0, 2).join(' | ')}
                    </Text>
                  )}

                  {(measure.measure_definition.numerator_logic?.any_of?.length ?? 0) > 0 && (
                    <Text size="xs" mt={4} style={{ color: 'var(--mi-text-secondary)' }}>
                      Numerator (Any): {(measure.measure_definition.numerator_logic?.any_of ?? []).slice(0, 2).join(' | ')}
                    </Text>
                  )}

                  {(measure.measure_definition.numerator_logic?.all_of?.length ?? 0) > 0 && (
                    <Text size="xs" mt={4} style={{ color: 'var(--mi-text-secondary)' }}>
                      Numerator (All): {(measure.measure_definition.numerator_logic?.all_of ?? []).slice(0, 2).join(' | ')}
                    </Text>
                  )}
                </Box>
              )}

              {(measure.eligibility_reason?.length ?? 0) > 0 && (
                <Box>
                  <Text size="xs" fw={600} mb={6} style={{ color: 'var(--mi-text-muted)' }}>Eligibility</Text>
                  <Stack gap={4}>
                    {(measure.eligibility_reason ?? []).slice(0, 3).map((r, i) => (
                      <Text key={i} size="xs" style={{ color: 'var(--mi-text-secondary)' }}>{r}</Text>
                    ))}
                  </Stack>
                </Box>
              )}

              {effectiveReasons.length > 0 && (
                <Box>
                  <Text size="xs" fw={600} mb={6} style={{ color: 'var(--mi-text-muted)' }}>
                    {previewActive ? 'Expanded Reasoning' : 'Verified Reasoning'}
                  </Text>
                  <Stack gap={4}>
                    {effectiveReasons.slice(0, 3).map((r, i) => (
                      <Text key={i} size="xs" style={{ color: 'var(--mi-text-secondary)' }}>{r}</Text>
                    ))}
                  </Stack>
                </Box>
              )}

              {effectiveTrace.length > 0 && (
                <Box>
                  <Text size="xs" fw={600} mb={6} style={{ color: 'var(--mi-text-muted)' }}>
                    Rule Evaluation
                  </Text>
                  <Stack gap={6}>
                    {effectiveTrace.slice(0, 5).map((t, i) => (
                      <Box key={i} style={{ padding: '6px 8px', borderRadius: 'var(--mi-radius-sm)', border: '1px solid var(--mi-border)' }}>
                        <Group gap={6} mb={2}>
                          <Badge size="xs" variant="light" color={t.result ? 'green' : 'red'} styles={{ root: { textTransform: 'none' } }}>
                            {t.result ? 'Pass' : 'Fail'}
                          </Badge>
                          <Text size="xs" fw={600} style={{ color: 'var(--mi-text)' }}>
                            {humanizeToken(String(t.rule ?? 'rule'))}
                          </Text>
                        </Group>
                        {t.detail && (
                          <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                            {String(t.detail)}
                          </Text>
                        )}
                      </Box>
                    ))}
                  </Stack>
                </Box>
              )}

              {effectiveEvidence.length > 0 && (
                <Box>
                  <Text size="xs" fw={600} mb={8} style={{ color: 'var(--mi-text-muted)' }}>
                    {previewActive ? 'Expanded Evidence' : 'Verified Evidence'} ({effectiveEvidence.length})
                  </Text>
                  <Stack gap={8}>
                    {effectiveEvidence.slice(0, 6).map((ev, idx) => {
                      const source = (ev.source ?? {}) as Record<string, unknown>;
                      const quote = String(ev.exact_quote ?? source.exact_quote ?? '');
                      const pageHint = Number(ev.page_number ?? source.page) || undefined;
                      const clickText = quote || String(ev.code ?? ev.value ?? summarizeEvidence(ev));
                      return (
                        <Box key={idx}>
                          <EvidenceSnippet
                            text={clickText}
                            type="hedis"
                            label={`${measure.measure_code} evidence`}
                            meta={{
                              pageHint,
                              code: String(ev.code ?? ''),
                              description: String(measure.measure_name ?? ''),
                              dateOfService: String(ev.date ?? ''),
                              exactQuote: quote || undefined,
                              pdf: String(source.pdf ?? ''),
                              charStart: Number(source.char_start) || undefined,
                              charEnd: Number(source.char_end) || undefined,
                            }}
                          />
                          {renderEvidenceMeta(ev)}
                        </Box>
                      );
                    })}
                  </Stack>
                </Box>
              )}

              {measure.clinical_only_preview && !previewActive && (
                <Box
                  style={{
                    padding: '10px 12px',
                    borderRadius: 'var(--mi-radius-md)',
                    backgroundColor: 'color-mix(in srgb, var(--mi-warning) 6%, var(--mi-surface))',
                    border: '1px solid color-mix(in srgb, var(--mi-warning) 18%, transparent)',
                  }}
                >
                  <Group justify="space-between" mb={6}>
                    <Text size="xs" fw={700} style={{ color: 'var(--mi-text)' }}>
                      Expanded Evidence Snapshot
                    </Text>
                    <Badge size="xs" variant="light" color={getMeasureStatusColor(measure.clinical_only_preview.status as MeasureStatus)} styles={{ root: { textTransform: 'none' } }}>
                      {String(measure.clinical_only_preview.status ?? 'not_applicable').replace('_', ' ')}
                    </Badge>
                  </Group>

                  {(measure.clinical_only_preview.compliance_reason?.length ?? 0) > 0 && (
                    <Text size="xs" mb={6} style={{ color: 'var(--mi-text-secondary)' }}>
                      {(measure.clinical_only_preview.compliance_reason ?? []).slice(0, 2).join(' | ')}
                    </Text>
                  )}

                  {previewEvidence.length > 0 && (
                    <Stack gap={8}>
                      {previewEvidence.slice(0, 4).map((ev, idx) => {
                        const source = (ev.source ?? {}) as Record<string, unknown>;
                        const quote = String(ev.exact_quote ?? source.exact_quote ?? '');
                        const pageHint = Number(ev.page_number ?? source.page) || undefined;
                        const clickText = quote || String(ev.code ?? ev.value ?? summarizeEvidence(ev));
                        return (
                          <Box key={idx}>
                            <EvidenceSnippet
                              text={clickText}
                              type="hedis"
                              label={`${measure.measure_code} preview`}
                              meta={{
                                pageHint,
                                code: String(ev.code ?? ''),
                                description: String(measure.measure_name ?? ''),
                                dateOfService: String(ev.date ?? ''),
                                exactQuote: quote || undefined,
                                pdf: String(source.pdf ?? ''),
                                charStart: Number(source.char_start) || undefined,
                                charEnd: Number(source.char_end) || undefined,
                              }}
                            />
                            {renderEvidenceMeta(ev)}
                          </Box>
                        );
                      })}
                    </Stack>
                  )}
                </Box>
              )}

              {effectiveGaps.length > 0 && (
                <Box>
                  <Text size="xs" fw={600} mb={6} style={{ color: 'var(--mi-text-muted)' }}>Measure Gaps</Text>
                  <Stack gap={6}>
                    {effectiveGaps.slice(0, 3).map((g, idx) => (
                      <Box key={idx} style={{ padding: '6px 8px', borderRadius: 'var(--mi-radius-sm)', backgroundColor: 'color-mix(in srgb, var(--mi-warning) 6%, var(--mi-surface))' }}>
                        <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                          {buildMeaningfulGapText(g)}
                        </Text>
                        {(g.required_event || g.window) && (
                          <Text size="xs" style={{ color: 'var(--mi-text-muted)', marginTop: 2 }}>
                            Rule: {g.required_event_name ?? (g.required_event ? humanizeToken(g.required_event) : 'n/a')}
                            {g.window ? ` | Window: ${g.window}` : ''}
                          </Text>
                        )}
                      </Box>
                    ))}
                  </Stack>
                </Box>
              )}
            </Stack>
          </Box>
        </Collapse>
      </Box>
    </motion.div>
  );
}

function GapCard({ gap, index }: { gap: HEDISGapItem; index: number }) {
  const priorityColor = gap.priority === 'high' ? 'red' : gap.priority === 'medium' ? 'yellow' : 'blue';
  return (
    <motion.div initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.04, duration: 0.2 }}>
      <Box
        style={{
          padding: '10px 12px',
          borderRadius: 10,
          backgroundColor: 'color-mix(in srgb, var(--mi-error) 4%, var(--mi-surface))',
          border: '1px solid color-mix(in srgb, var(--mi-error) 15%, transparent)',
        }}
      >
        <Group justify="space-between" align="flex-start" mb={6} wrap="nowrap">
          <Group gap={8} align="center" style={{ minWidth: 0 }}>
            <IconAlertTriangle size={14} stroke={2} color="var(--mi-error)" style={{ flexShrink: 0 }} />
            <Badge
              size="xs"
              variant="filled"
              color="blue"
              radius="md"
              styles={{ root: { fontFamily: '"JetBrains Mono", "Fira Code", monospace', fontWeight: 700, fontSize: 10, textTransform: 'none', flexShrink: 0 } }}
            >
              {gap.measure_code}
            </Badge>
            <Text size="sm" fw={600} style={{ color: 'var(--mi-text)', minWidth: 0 }} lineClamp={1}>
              {gap.measure_name}
            </Text>
          </Group>
          <Badge size="xs" color={priorityColor} variant="light" radius="sm" styles={{ root: { textTransform: 'capitalize', flexShrink: 0 } }}>
            {gap.priority}
          </Badge>
        </Group>

        <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }} mb={6}>{gap.gap_description}</Text>
        {gap.missing_evidence && <Text size="xs" style={{ color: 'var(--mi-text-muted)' }} mb={6}>Missing: {gap.missing_evidence}</Text>}
        {gap.recommended_action && (
          <Group gap={6} mt={4}>
            <IconArrowRight size={12} stroke={2} color="var(--mi-primary)" />
            <Text size="xs" fw={500} style={{ color: 'var(--mi-primary)' }}>{gap.recommended_action}</Text>
          </Group>
        )}
      </Box>
    </motion.div>
  );
}

export function HEDISPanel() {
  const activeChartId = useChartStore((s) => s.activeChartId);
  const { data: hedisData, isLoading, isError, refetch } = useHEDISMeasures(activeChartId);
  const acceptHEDISMutation = useAcceptHEDIS();
  const rejectHEDISMutation = useRejectHEDIS();
  const [gapsOpen, { toggle: toggleGaps }] = useDisclosure(true);
  const [inactiveOpen, { toggle: toggleInactive }] = useDisclosure(false);
  const [search, setSearch] = useState('');
  const [viewMode, setViewMode] = useState<'strict' | 'preview'>('strict');
  const [statusFilter, setStatusFilter] = useState<'all' | 'applicable' | 'met' | 'gap' | 'indeterminate'>('all');
  const [openedMeasures, setOpenedMeasures] = useState<Set<string>>(new Set());
  const [reviewModal, setReviewModal] = useState<{
    open: boolean;
    action: 'accept' | 'reject';
    id: number | string;
    label: string;
  }>({ open: false, action: 'accept', id: 0, label: '' });

  const handleAcceptClick = useCallback((id: string | number) => {
    const m = measures.find((m) => (m.id ?? m.measure_id) === id);
    setReviewModal({ open: true, action: 'accept', id, label: `${m?.measure_code ?? ''} - ${m?.measure_name ?? ''}` });
  }, []);

  const handleRejectClick = useCallback((id: string | number) => {
    const m = measures.find((m) => (m.id ?? m.measure_id) === id);
    setReviewModal({ open: true, action: 'reject', id, label: `${m?.measure_code ?? ''} - ${m?.measure_name ?? ''}` });
  }, []);

  const handleReviewConfirm = useCallback((notes: string) => {
    const { action, id } = reviewModal;
    const payload = { reviewer: 'RiskQ360', notes: notes || null };
    if (action === 'accept') {
      acceptHEDISMutation.mutate({ id, payload });
    } else {
      rejectHEDISMutation.mutate({ id, payload });
    }
    setReviewModal((m) => ({ ...m, open: false }));
  }, [reviewModal, acceptHEDISMutation, rejectHEDISMutation]);

  const measures = hedisData?.measures ?? [];
  const gaps = hedisData?.gaps ?? [];
  const strictSummary = hedisData?.summary;
  const previewSummary = hedisData?.summary_preview;
  const previewAvailable = useMemo(
    () => measures.some((m) => Boolean(m.clinical_only_preview)),
    [measures],
  );
  const effectiveSummary = viewMode === 'preview' ? (previewSummary ?? strictSummary) : strictSummary;

  const strictHasQuotedEvidence = useMemo(
    () => measures.some((m) => hasQuotedEvidence(m.evidence)),
    [measures],
  );
  const previewHasQuotedEvidence = useMemo(
    () => measures.some((m) => hasQuotedEvidence(m.clinical_only_preview?.evidence_used)),
    [measures],
  );

  useEffect(() => {
    if (!hedisData) return;
    if (hedisData.default_view_mode === 'clinical_preview' && previewAvailable) {
      setViewMode('preview');
      return;
    }
    setViewMode('strict');
  }, [activeChartId, hedisData, previewAvailable]);

  useEffect(() => {
    if (viewMode !== 'strict') return;
    if (!strictHasQuotedEvidence && previewHasQuotedEvidence) {
      setViewMode('preview');
    }
  }, [previewHasQuotedEvidence, strictHasQuotedEvidence, viewMode]);

  useEffect(() => {
    if (!previewAvailable && viewMode === 'preview') {
      setViewMode('strict');
    }
  }, [previewAvailable, viewMode]);

  const activeMeasures = measures.filter((m) => m.status !== 'inactive');
  const inactiveMeasures = measures.filter((m) => m.status === 'inactive');

  const totalEligible = effectiveSummary?.applicable ?? hedisData?.total_eligible ?? activeMeasures.filter((m) => m.eligible).length;
  const totalMet = effectiveSummary?.met ?? hedisData?.total_met ?? activeMeasures.filter((m) => m.status === 'met').length;
  const totalGaps = effectiveSummary?.gap ?? hedisData?.total_gaps ?? gaps.length;
  const totalIndeterminate = effectiveSummary?.indeterminate ?? activeMeasures.filter((m) => m.status === 'indeterminate').length;
  const complianceRate = totalEligible > 0 ? Math.round((totalMet / totalEligible) * 100) : 0;

  const filteredActive = useMemo(() => {
    const getEffectiveStatus = (m: HEDISMeasure): MeasureStatus =>
      viewMode === 'preview' && m.clinical_only_preview?.status
        ? coerceMeasureStatus(m.clinical_only_preview.status, m.status)
        : m.status;
    const statusRank: Record<MeasureStatus, number> = {
      met: 0,
      gap: 1,
      indeterminate: 2,
      not_applicable: 3,
      excluded: 4,
      inactive: 5,
    };
    const q = search.trim().toLowerCase();
    return activeMeasures
      .filter((m) => {
        const status = getEffectiveStatus(m);
        const applicable = viewMode === 'preview' && m.clinical_only_preview
          ? Boolean(m.clinical_only_preview.applicable)
          : Boolean(m.eligible);
        if (statusFilter === 'applicable' && !applicable) return false;
        if (statusFilter === 'met' && status !== 'met') return false;
        if (statusFilter === 'gap' && status !== 'gap') return false;
        if (statusFilter === 'indeterminate' && status !== 'indeterminate') return false;
        if (!q) return true;
        return (
          m.measure_code.toLowerCase().includes(q) ||
          m.measure_name.toLowerCase().includes(q) ||
          String(status).toLowerCase().includes(q)
        );
      })
      .sort((a, b) => {
        const sa = getEffectiveStatus(a);
        const sb = getEffectiveStatus(b);
        const byStatus = (statusRank[sa] ?? 9) - (statusRank[sb] ?? 9);
        if (byStatus !== 0) return byStatus;
        return a.measure_code.localeCompare(b.measure_code);
      });
  }, [activeMeasures, search, statusFilter, viewMode]);

  const filteredInactive = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return inactiveMeasures;
    return inactiveMeasures.filter((m) =>
      m.measure_code.toLowerCase().includes(q) ||
      m.measure_name.toLowerCase().includes(q),
    );
  }, [inactiveMeasures, search]);

  if (isLoading) return <HEDISSkeleton />;

  if (isError) {
    return (
      <Box p={16}>
        <Alert icon={<IconAlertCircle size={18} />} title="Failed to load HEDIS data" color="red" radius="md">
          <Text size="sm" style={{ color: 'var(--mi-text-secondary)' }}>
            There was an error loading HEDIS quality measure data. The chart may still be processing.
          </Text>
          <Button size="xs" variant="light" color="red" mt={8} leftSection={<IconRefresh size={14} />} onClick={() => refetch()}>
            Retry
          </Button>
        </Alert>
      </Box>
    );
  }

  if (!hedisData || measures.length === 0) return <EmptyState />;

  const canToggleEvidenceMode = previewAvailable;

  return (
    <Box style={{ height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column', padding: '8px 10px' }}>
      <Stack gap={8} style={{ flexShrink: 0 }}>
        <Group gap={8} wrap="nowrap">
          <StatCard
            label="Applicable"
            value={Number(totalEligible)}
            color="var(--mi-info)"
            icon={<IconHeartRateMonitor size={11} stroke={2} color="var(--mi-info)" />}
            active={statusFilter === 'applicable'}
            onClick={() => {
              const next = statusFilter === 'applicable' ? 'all' : 'applicable';
              setStatusFilter(next);
              setOpenedMeasures(new Set());
            }}
          />
          <StatCard
            label="Met"
            value={Number(totalMet)}
            color="var(--mi-success)"
            icon={<IconCheck size={11} stroke={2.5} color="var(--mi-success)" />}
            active={statusFilter === 'met'}
            onClick={() => {
              const next = statusFilter === 'met' ? 'all' : 'met';
              setStatusFilter(next);
              if (next === 'met') {
                const first = activeMeasures.find((m) => m.status === 'met');
                if (first) setOpenedMeasures(new Set([first.measure_id || first.id || first.measure_code || '']));
              } else {
                setOpenedMeasures(new Set());
              }
            }}
          />
          <StatCard
            label="Gap"
            value={Number(totalGaps)}
            color="var(--mi-error)"
            icon={<IconX size={11} stroke={2.5} color="var(--mi-error)" />}
            active={statusFilter === 'gap'}
            onClick={() => {
              const next = statusFilter === 'gap' ? 'all' : 'gap';
              setStatusFilter(next);
              if (next === 'gap') {
                const first = activeMeasures.find((m) => m.status === 'gap');
                if (first) setOpenedMeasures(new Set([first.measure_id || first.id || first.measure_code || '']));
              } else {
                setOpenedMeasures(new Set());
              }
            }}
          />
          <StatCard
            label="Indeterminate"
            value={Number(totalIndeterminate)}
            color="var(--mi-warning)"
            icon={<IconAlertTriangle size={11} stroke={2.5} color="var(--mi-warning)" />}
            active={statusFilter === 'indeterminate'}
            onClick={() => {
              const next = statusFilter === 'indeterminate' ? 'all' : 'indeterminate';
              setStatusFilter(next);
              setOpenedMeasures(new Set());
            }}
          />

          <Box
            style={{ minWidth: 90, padding: '6px 8px', borderRadius: 10, display: 'flex', alignItems: 'center', gap: 6, border: '1px solid var(--mi-border)', background: 'var(--mi-surface)' }}
          >
            <RingProgress
              size={38}
              thickness={4}
              roundCaps
              sections={[{ value: complianceRate, color: complianceRate >= 80 ? 'var(--mi-success)' : complianceRate >= 50 ? 'var(--mi-warning)' : 'var(--mi-error)' }]}
              label={<Text size="xs" fw={800} ta="center" style={{ fontSize: 9, fontVariantNumeric: 'tabular-nums', color: 'var(--mi-text)' }}>{complianceRate}%</Text>}
            />
            <Box>
              <Text size="xs" fw={700} tt="uppercase" style={{ color: 'var(--mi-text-muted)', letterSpacing: '0.04em', fontSize: 8 }}>
                Compliance
              </Text>
              <Text size="xs" fw={700} style={{ color: 'var(--mi-text)', fontSize: 11 }}>{totalMet}/{totalEligible}</Text>
            </Box>
          </Box>
        </Group>

        <Group gap={6} wrap="wrap">
          {hedisData.measurement_year && (
            <Badge size="xs" variant="light" color="violet" radius="md" styles={{ root: { textTransform: 'none' } }}>
              Year: {hedisData.measurement_year}
            </Badge>
          )}
          <Badge size="xs" variant="light" color="blue" radius="md" styles={{ root: { textTransform: 'none' } }}>
            Active: {activeMeasures.length}
          </Badge>
          <Badge size="xs" variant="light" color="gray" radius="md" styles={{ root: { textTransform: 'none' } }}>
            Inactive: {inactiveMeasures.length}
          </Badge>
          {canToggleEvidenceMode ? (
            <SegmentedControl
              size="xs"
              value={viewMode}
              onChange={(v: string) => setViewMode(v as 'strict' | 'preview')}
              data={[
                { label: 'Authoritative', value: 'strict' },
                { label: 'Clinical Preview', value: 'preview' },
              ]}
            />
          ) : (
            <Badge size="xs" variant="light" color="teal" radius="md" styles={{ root: { textTransform: 'none' } }}>
              View: Authoritative
            </Badge>
          )}
        </Group>

        {canToggleEvidenceMode && (
          <Text size="xs" style={{ color: 'var(--mi-text-muted)', marginTop: -2 }}>
            {viewMode === 'strict'
              ? 'Authoritative uses strict denominator/enrollment evidence only.'
              : 'Clinical Preview shows expanded signal-based reasoning when strict evidence is incomplete.'}
          </Text>
        )}

        <TextInput
          placeholder="Search code, measure, status..."
          leftSection={<IconSearch size={13} stroke={1.5} />}
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
          size="xs"
          styles={{ input: { backgroundColor: 'var(--mi-surface)', borderColor: 'var(--mi-border)', color: 'var(--mi-text)', fontSize: 12 } }}
        />

        <Group justify="space-between" align="center">
          <Group gap={8}>
            <IconShieldCheck size={15} stroke={1.5} color="var(--mi-primary)" />
            <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>Active HEDIS Measures</Text>
            <Badge size="xs" variant="light" color="blue" radius="md">{filteredActive.length}</Badge>
          </Group>
          {statusFilter !== 'all' && (
            <Button size="compact-xs" variant="subtle" color="gray" onClick={() => setStatusFilter('all')}>
              Clear Filter
            </Button>
          )}
        </Group>
      </Stack>

      <Box style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', paddingTop: 8, paddingRight: 4 }}>
        <Stack gap={8}>
          <AnimatePresence mode="popLayout">
            {filteredActive.map((measure, idx) => {
              const key = measure.measure_id || measure.id || measure.measure_code || `measure-${idx}`;
              const keyStr = String(key);
              return (
                <MeasureCard
                  key={key}
                  measure={measure}
                  index={idx}
                  viewMode={viewMode}
                  onAccept={handleAcceptClick}
                  onReject={handleRejectClick}
                  isOpen={openedMeasures.has(keyStr)}
                  onToggle={() => {
                    setOpenedMeasures((prev) => {
                      const next = new Set(prev);
                      if (next.has(keyStr)) next.delete(keyStr);
                      else next.add(keyStr);
                      return next;
                    });
                  }}
                />
              );
            })}
          </AnimatePresence>
          {filteredActive.length === 0 && search.trim() && (
            <Text size="sm" c="dimmed" ta="center" py={20}>No active measures matching "{search}"</Text>
          )}
        </Stack>

        {inactiveMeasures.length > 0 && (
          <Box>
            <Button
              variant="subtle"
              color="gray"
              size="xs"
              onClick={toggleInactive}
              leftSection={<IconFileText size={14} stroke={1.5} />}
              rightSection={inactiveOpen ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
              styles={{ root: { fontWeight: 600, fontSize: 12, padding: '4px 8px' } }}
            >
              Inactive Measures ({filteredInactive.length})
            </Button>
            <Collapse in={inactiveOpen}>
              <Stack gap={6} mt={8}>
                {filteredInactive.map((m, idx) => (
                  <Box key={`${m.measure_code}-${idx}`} style={{ padding: '8px 10px', borderRadius: 'var(--mi-radius-md)', border: '1px solid var(--mi-border)', backgroundColor: 'var(--mi-surface)' }}>
                    <Group justify="space-between" wrap="nowrap">
                      <Group gap={8} style={{ minWidth: 0 }}>
                        <Badge size="xs" variant="filled" color="gray" styles={{ root: { textTransform: 'none', fontFamily: '"JetBrains Mono", "Fira Code", monospace' } }}>{m.measure_code}</Badge>
                        <Text size="xs" fw={600} lineClamp={1} style={{ color: 'var(--mi-text)' }}>{m.measure_name}</Text>
                      </Group>
                      <Badge size="xs" color="gray" variant="light" styles={{ root: { textTransform: 'none' } }}>Inactive</Badge>
                    </Group>
                  </Box>
                ))}
              </Stack>
            </Collapse>
          </Box>
        )}

        {gaps.length > 0 && (
          <Box>
            <Button
              variant="subtle"
              color="red"
              size="xs"
              onClick={toggleGaps}
              leftSection={<IconListCheck size={14} stroke={1.5} />}
              rightSection={gapsOpen ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
              styles={{ root: { fontWeight: 600, fontSize: 12, padding: '4px 8px' } }}
            >
              Care Gaps ({gaps.length})
            </Button>
            <Collapse in={gapsOpen}>
              <Divider my={8} />
              <Stack gap={8} mt={8}>
                {gaps.map((gap, idx) => (
                  <GapCard key={`${gap.measure_code}-${idx}`} gap={gap} index={idx} />
                ))}
              </Stack>
            </Collapse>
          </Box>
        )}
      </Box>

      {/* Review Modal */}
      <ReviewModal
        opened={reviewModal.open}
        onClose={() => setReviewModal((m) => ({ ...m, open: false }))}
        onConfirm={handleReviewConfirm}
        action={reviewModal.action}
        itemType="HEDIS"
        itemLabel={reviewModal.label}
        isPending={acceptHEDISMutation.isPending || rejectHEDISMutation.isPending}
      />
    </Box>
  );
}



















