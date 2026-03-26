import { useState, useMemo, useCallback } from 'react';
import {
  Box,
  Text,
  TextInput,
  MultiSelect,
  Select,
  Group,
  Stack,
  Badge,
  Button,
  Skeleton,
  Alert,
  ActionIcon,
  Tooltip,
  HoverCard,
} from '@mantine/core';
import {
  IconSearch,
  IconStethoscope,
  IconAlertCircle,
  IconRefresh,
  IconCheck,
  IconX,
  IconFilter,
  IconSortAscending,
  IconSortDescending,
  IconPlus,
  IconTrash,
  IconDeviceFloppy,
  IconRobot,
  IconUser,
  IconQuote,
} from '@tabler/icons-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChartStore } from '../../stores/chartStore';
import {
  useDiagnoses,
  useAcceptDiagnosis,
  useRejectDiagnosis2,
  useDeleteDiagnosis,
  useAddDiagnosis,
  useSaveDocument,
} from '../../hooks/useChart';
import type { Diagnosis, NegationStatus } from '../../types/clinical';
import { formatDate, formatConfidence } from '../../utils/formatters';
import { getNegationColor, getNegationLabel } from '../../utils/colors';
import { NegationBadge } from '../shared/NegationBadge';
import { ConfidenceBar } from '../shared/ConfidenceBar';
import { usePDFStore } from '../../stores/pdfStore';
import { ReviewModal } from '../shared/ReviewModal';
import { AddDiagnosisModal } from '../shared/AddDiagnosisModal';
import { CodingHelperModal } from '../shared/CodingHelperModal';
import type { CodingHelperResult } from '../../api/review';

/* -------------------------------------------------------------------------- */
/* Constants                                                                   */
/* -------------------------------------------------------------------------- */
const ALL_NEGATION_STATUSES: NegationStatus[] = [
  'active',
  'negated',
  'resolved',
  'historical',
  'family_history',
  'uncertain',
];

const NEGATION_SELECT_DATA = ALL_NEGATION_STATUSES.map((s) => ({
  value: s,
  label: getNegationLabel(s),
}));

type SortField = 'icd' | 'description' | 'date';
type SortDir = 'asc' | 'desc';

const SORT_OPTIONS = [
  { value: 'icd', label: 'ICD Code' },
  { value: 'description', label: 'Alphabetical' },
  { value: 'date', label: 'Date of Service' },
];

const NEGATION_BORDER_CSS: Record<string, string> = {
  active: 'var(--mi-success)',
  negated: 'var(--mi-error)',
  resolved: 'var(--mi-info)',
  historical: 'var(--mi-text-muted)',
  family_history: 'var(--mantine-color-violet-5, #7C3AED)',
  uncertain: 'var(--mi-warning)',
};

const NEGATION_EXPLANATIONS: Record<string, string> = {
  active: 'Currently present and being managed',
  negated: 'Explicitly denied or ruled out',
  resolved: 'Was present but no longer active',
  historical: 'Past occurrence, unclear if still active',
  family_history: 'Condition in a family member',
  uncertain: 'Possible, suspected, or differential',
};

/* -------------------------------------------------------------------------- */
/* Loading Skeleton                                                            */
/* -------------------------------------------------------------------------- */
function DiagnosesSkeleton() {
  return (
    <Stack gap={12} p={16}>
      <Group gap={8}>
        <Skeleton width={200} height={34} radius="md" />
        <Skeleton width={160} height={34} radius="md" />
        <Skeleton width={120} height={34} radius="md" />
      </Group>
      {[1, 2, 3, 4, 5].map((i) => (
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
            <Skeleton width={70} height={22} radius="md" />
            <Skeleton width={220} height={16} />
          </Group>
          <Group gap={8}>
            <Skeleton width={60} height={18} radius="md" />
            <Skeleton width={80} height={18} radius="md" />
            <Skeleton width={90} height={14} />
          </Group>
        </Box>
      ))}
    </Stack>
  );
}

/* -------------------------------------------------------------------------- */
/* Empty State                                                                 */
/* -------------------------------------------------------------------------- */
function EmptyState({ hasFilters }: { hasFilters: boolean }) {
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
        <IconStethoscope size={32} stroke={1.2} color="var(--mi-text-muted)" />
      </Box>
      <Text size="md" fw={600} style={{ color: 'var(--mi-text)' }}>
        {hasFilters ? 'No Matching Diagnoses' : 'No Diagnoses Found'}
      </Text>
      <Text size="sm" c="dimmed" ta="center" maw={300}>
        {hasFilters
          ? 'Try adjusting your filters or search query to see more results.'
          : 'Diagnosis data will appear here once the chart has been processed.'}
      </Text>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Source Badge                                                                 */
/* -------------------------------------------------------------------------- */
function SourceBadge({ description }: { description: string }) {
  const isCoder = description?.startsWith('[Coder-added]');
  return (
    <Tooltip label={isCoder ? 'Added by coder' : 'AI-extracted'} withArrow>
      <Badge
        size="xs"
        variant="light"
        color={isCoder ? 'teal' : 'blue'}
        leftSection={isCoder ? <IconUser size={9} /> : <IconRobot size={9} />}
        styles={{ root: { textTransform: 'none', fontSize: 9 } }}
      >
        {isCoder ? 'Coder' : 'AI'}
      </Badge>
    </Tooltip>
  );
}

/* -------------------------------------------------------------------------- */
/* Diagnosis Card                                                              */
/* -------------------------------------------------------------------------- */
interface DiagnosisCardProps {
  diagnosis: Diagnosis;
  index: number;
  onAccept: (id: number | string) => void;
  onReject: (id: number | string) => void;
  onDelete: (id: number | string) => void;
  isReviewing: boolean;
}

function DiagnosisCard({ diagnosis, index, onAccept, onReject, onDelete, isReviewing }: DiagnosisCardProps) {
  const isCoder = diagnosis.description?.startsWith('[Coder-added]');
  const displayDesc = isCoder
    ? diagnosis.description.replace(/^\[Coder-added\]\s*/, '')
    : diagnosis.description;
  const navigateToText = usePDFStore((s) => s.navigateToText);
  const confidence = (diagnosis as unknown as Record<string, unknown>).confidence as number | undefined;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{
        delay: Math.min(index * 0.03, 0.3),
        duration: 0.2,
        ease: [0.4, 0, 0.2, 1],
      }}
    >
      <HoverCard openDelay={300} position="right" width={360} shadow="lg" withArrow>
        <HoverCard.Target>
          <Box
            style={{
              padding: '8px 10px',
              borderRadius: 8,
              backgroundColor: 'var(--mi-surface)',
              border: '1px solid var(--mi-border)',
              borderLeft: `3px solid ${NEGATION_BORDER_CSS[diagnosis.negation_status] ?? 'var(--mi-border)'}`,
              transition: 'all var(--mi-transition-fast)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--mi-primary) 25%, transparent)';
              e.currentTarget.style.borderLeftColor = NEGATION_BORDER_CSS[diagnosis.negation_status] ?? 'var(--mi-border)';
              e.currentTarget.style.boxShadow = 'var(--mi-shadow-sm)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--mi-border)';
              e.currentTarget.style.borderLeftColor = NEGATION_BORDER_CSS[diagnosis.negation_status] ?? 'var(--mi-border)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            {/* Row 1: ICD Code + Description + Badges + Actions — all on one line */}
            <Group justify="space-between" align="center" wrap="nowrap" gap={6}>
              <Group gap={6} align="center" style={{ minWidth: 0, flex: 1 }} wrap="nowrap">
                <Badge
                  size="sm"
                  variant="filled"
                  color="violet"
                  radius="md"
                  styles={{
                    root: {
                      fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                      fontWeight: 700,
                      fontSize: 10,
                      textTransform: 'none',
                      flexShrink: 0,
                      padding: '0 6px',
                      height: 20,
                    },
                  }}
                >
                  {diagnosis.icd10_code}
                </Badge>
                <Text
                  size="xs"
                  fw={600}
                  style={{ color: 'var(--mi-text)', lineHeight: 1.2, minWidth: 0 }}
                  lineClamp={1}
                >
                  {displayDesc}
                </Text>
              </Group>

              <Group gap={3} style={{ flexShrink: 0 }} wrap="nowrap">
                <SourceBadge description={diagnosis.description} />
                <NegationBadge status={diagnosis.negation_status} size="xs" />
                {/* Inline review actions */}
                {diagnosis.id !== undefined && (
                  <>
                    <Tooltip label="Accept" withArrow>
                      <ActionIcon
                        size={18}
                        variant="light"
                        color="green"
                        loading={isReviewing}
                        onClick={() => onAccept(diagnosis.id!)}
                      >
                        <IconCheck size={11} stroke={2.5} />
                      </ActionIcon>
                    </Tooltip>
                    <Tooltip label="Reject" withArrow>
                      <ActionIcon
                        size={18}
                        variant="light"
                        color="red"
                        loading={isReviewing}
                        onClick={() => onReject(diagnosis.id!)}
                      >
                        <IconX size={11} stroke={2.5} />
                      </ActionIcon>
                    </Tooltip>
                    <Tooltip label="Delete" withArrow>
                      <ActionIcon
                        size={18}
                        variant="light"
                        color="gray"
                        loading={isReviewing}
                        onClick={() => onDelete(diagnosis.id!)}
                      >
                        <IconTrash size={11} stroke={2} />
                      </ActionIcon>
                    </Tooltip>
                  </>
                )}
              </Group>
            </Group>

            {/* Row 2: Compact metadata line */}
            <Group gap={6} mt={4} wrap="wrap">
              {diagnosis.source_section && (
                <Badge size="xs" variant="outline" color="gray" styles={{ root: { textTransform: 'none', fontSize: 9, height: 16, padding: '0 4px' } }}>
                  {diagnosis.source_section}
                </Badge>
              )}
              {diagnosis.date_of_service && (
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>
                  DOS: {formatDate(diagnosis.date_of_service)}
                </Text>
              )}
              {diagnosis.provider && (
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>
                  {diagnosis.provider}
                </Text>
              )}
              {diagnosis.negation_trigger && (
                <Badge size="xs" variant="light" color="orange" styles={{ root: { textTransform: 'none', fontSize: 9, height: 16, padding: '0 4px' } }}>
                  {diagnosis.negation_trigger}
                </Badge>
              )}
              {/* Evidence inline — clickable to navigate in PDF */}
              {diagnosis.supporting_text && (
                <Box
                  style={{
                    borderLeft: '3px solid color-mix(in srgb, var(--mi-primary) 25%, transparent)',
                    paddingLeft: 12,
                    marginLeft: 4,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                    minWidth: 0,
                    flex: 1,
                  }}
                >
                  <IconQuote size={10} stroke={1.5} color="var(--mi-primary)" style={{ flexShrink: 0, opacity: 0.6 }} />
                  <Text
                    size="xs"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigateToText(diagnosis.supporting_text!, 'diagnosis', diagnosis.icd10_code, {
                        code: diagnosis.icd10_code,
                        description: diagnosis.description,
                        sourceSection: diagnosis.source_section ?? undefined,
                        provider: diagnosis.provider ?? undefined,
                        dateOfService: diagnosis.date_of_service ?? undefined,
                      });
                    }}
                    style={{
                      color: 'var(--mi-primary)',
                      fontStyle: 'italic',
                      fontSize: 10,
                      minWidth: 0,
                      flex: 1,
                      cursor: 'pointer',
                      textDecoration: 'underline',
                      textDecorationColor: 'color-mix(in srgb, var(--mi-primary) 30%, transparent)',
                      textUnderlineOffset: 2,
                    }}
                    lineClamp={1}
                  >
                    &ldquo;{diagnosis.supporting_text.slice(0, 120)}&rdquo;
                  </Text>
                </Box>
              )}
            </Group>
          </Box>
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
            {/* ICD Code header */}
            <Group gap={8} align="center">
              <Badge
                size="md"
                variant="filled"
                color="violet"
                radius="md"
                styles={{ root: { fontFamily: '"JetBrains Mono", "Fira Code", monospace', fontWeight: 700, textTransform: 'none' } }}
              >
                {diagnosis.icd10_code}
              </Badge>
              <NegationBadge status={diagnosis.negation_status} size="sm" />
            </Group>

            {/* Full description */}
            <Text size="sm" fw={600} style={{ color: 'var(--mi-text)', lineHeight: 1.4 }}>
              {displayDesc}
            </Text>

            {/* Negation explanation */}
            <Box
              style={{
                padding: '6px 10px',
                borderRadius: 'var(--mi-radius-sm)',
                backgroundColor: `color-mix(in srgb, ${NEGATION_BORDER_CSS[diagnosis.negation_status] ?? 'var(--mi-border)'} 8%, var(--mi-surface))`,
                border: `1px solid color-mix(in srgb, ${NEGATION_BORDER_CSS[diagnosis.negation_status] ?? 'var(--mi-border)'} 20%, transparent)`,
              }}
            >
              <Text size="xs" fw={600} style={{ color: 'var(--mi-text)', marginBottom: 2 }}>
                {getNegationLabel(diagnosis.negation_status)}
              </Text>
              <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                {NEGATION_EXPLANATIONS[diagnosis.negation_status] ?? ''}
              </Text>
            </Box>

            {/* Metadata */}
            <Group gap={12}>
              {diagnosis.date_of_service && (
                <Box>
                  <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 9 }}>DOS</Text>
                  <Text size="xs" fw={600} style={{ color: 'var(--mi-text)' }}>{formatDate(diagnosis.date_of_service)}</Text>
                </Box>
              )}
              {diagnosis.provider && (
                <Box>
                  <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 9 }}>Provider</Text>
                  <Text size="xs" fw={600} style={{ color: 'var(--mi-text)' }}>{diagnosis.provider}</Text>
                </Box>
              )}
              {diagnosis.source_section && (
                <Box>
                  <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 9 }}>Section</Text>
                  <Text size="xs" fw={600} style={{ color: 'var(--mi-text)' }}>{diagnosis.source_section}</Text>
                </Box>
              )}
            </Group>

            {/* Confidence bar */}
            {confidence !== undefined && confidence !== null && (
              <Box>
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 9, marginBottom: 4 }}>Confidence</Text>
                <ConfidenceBar confidence={confidence} size="sm" />
              </Box>
            )}

            {/* Supporting text quote */}
            {diagnosis.supporting_text && (
              <Box
                style={{
                  padding: '8px 10px',
                  borderRadius: 'var(--mi-radius-sm)',
                  backgroundColor: 'color-mix(in srgb, var(--mi-primary) 4%, var(--mi-surface))',
                  borderLeft: '3px solid color-mix(in srgb, var(--mi-primary) 30%, transparent)',
                }}
              >
                <Group gap={4} mb={4}>
                  <IconQuote size={10} stroke={1.5} color="var(--mi-primary)" />
                  <Text size="xs" fw={600} style={{ color: 'var(--mi-text-muted)', fontSize: 9 }}>Supporting Evidence</Text>
                </Group>
                <Text size="xs" style={{ color: 'var(--mi-text-secondary)', fontStyle: 'italic', lineHeight: 1.5 }}>
                  &ldquo;{diagnosis.supporting_text.slice(0, 300)}{diagnosis.supporting_text.length > 300 ? '...' : ''}&rdquo;
                </Text>
              </Box>
            )}
          </Stack>
        </HoverCard.Dropdown>
      </HoverCard>
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */
/* Main Diagnoses Panel                                                        */
/* -------------------------------------------------------------------------- */
export function DiagnosesPanel() {
  const activeChartId = useChartStore((s) => s.activeChartId);
  const { data: diagnoses, isLoading, isError, refetch } = useDiagnoses(activeChartId);
  const acceptMutation = useAcceptDiagnosis();
  const rejectMutation = useRejectDiagnosis2();
  const deleteMutation = useDeleteDiagnosis();
  const addMutation = useAddDiagnosis();
  const saveMutation = useSaveDocument();

  /* Modal state */
  const [reviewModal, setReviewModal] = useState<{
    open: boolean;
    action: 'accept' | 'reject';
    id: number | string;
    label: string;
  }>({ open: false, action: 'accept', id: 0, label: '' });
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [codingHelperOpen, setCodingHelperOpen] = useState(false);
  const [selectedCode, setSelectedCode] = useState<CodingHelperResult | null>(null);

  /* Filters */
  const [search, setSearch] = useState('');
  const [negationFilter, setNegationFilter] = useState<string[]>([]);
  const [sortField, setSortField] = useState<SortField>('icd');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [sourceFilter, setSourceFilter] = useState<'all' | 'ai' | 'manual'>('all');

  const hasFilters = search.trim() !== '' || negationFilter.length > 0 || sourceFilter !== 'all';
  const isAnyMutating = acceptMutation.isPending || rejectMutation.isPending || deleteMutation.isPending;

  /* Filter + sort diagnoses */
  const filteredDiagnoses = useMemo<Diagnosis[]>(() => {
    if (!diagnoses) return [];
    let result = [...diagnoses];
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(
        (d) =>
          (d.icd10_code ?? '').toLowerCase().includes(q) ||
          (d.description ?? '').toLowerCase().includes(q) ||
          (d.supporting_text?.toLowerCase().includes(q) ?? false) ||
          (d.source_section?.toLowerCase().includes(q) ?? false) ||
          (d.provider?.toLowerCase().includes(q) ?? false),
      );
    }
    if (negationFilter.length > 0) {
      result = result.filter((d) => negationFilter.includes(d.negation_status));
    }
    if (sourceFilter === 'manual') {
      result = result.filter((d) => d.description?.startsWith('[Coder-added]'));
    } else if (sourceFilter === 'ai') {
      result = result.filter((d) => !d.description?.startsWith('[Coder-added]'));
    }
    result.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'icd':
          cmp = (a.icd10_code ?? '').localeCompare(b.icd10_code ?? '');
          break;
        case 'description':
          cmp = (a.description ?? '').localeCompare(b.description ?? '');
          break;
        case 'date':
          cmp = (a.date_of_service ?? '').localeCompare(b.date_of_service ?? '');
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return result;
  }, [diagnoses, search, negationFilter, sortField, sortDir, sourceFilter]);

  /* Handlers */
  const handleAcceptClick = useCallback((id: number | string) => {
    const diag = diagnoses?.find((d) => d.id === id);
    setReviewModal({ open: true, action: 'accept', id, label: `${diag?.icd10_code ?? ''} - ${diag?.description ?? ''}` });
  }, [diagnoses]);

  const handleRejectClick = useCallback((id: number | string) => {
    const diag = diagnoses?.find((d) => d.id === id);
    setReviewModal({ open: true, action: 'reject', id, label: `${diag?.icd10_code ?? ''} - ${diag?.description ?? ''}` });
  }, [diagnoses]);

  const handleReviewConfirm = useCallback((notes: string) => {
    const { action, id } = reviewModal;
    if (action === 'accept') {
      acceptMutation.mutate({ id, payload: { reviewer: 'RiskQ360', notes: notes || null } });
    } else {
      rejectMutation.mutate({ id, payload: { reviewer: 'RiskQ360', notes: notes || null } });
    }
    setReviewModal((m) => ({ ...m, open: false }));
  }, [reviewModal, acceptMutation, rejectMutation]);

  const handleDelete = useCallback((id: number | string) => {
    deleteMutation.mutate({ id, reviewer: 'RiskQ360' });
  }, [deleteMutation]);

  const handleAddSubmit = useCallback(
    (data: {
      icd10_code: string;
      description: string;
      date_of_service?: string;
      notes?: string;
      page_number?: number;
      exact_quote?: string;
      hcc_code?: string;
      status: string;
    }) => {
      if (!activeChartId) return;
      addMutation.mutate({
        chart_id: parseInt(activeChartId, 10),
        icd10_code: data.icd10_code,
        description: data.description,
        reviewer: 'RiskQ360',
        notes: data.notes,
        date_of_service: data.date_of_service,
        page_number: data.page_number,
        exact_quote: data.exact_quote,
        hcc_code: data.hcc_code,
        status: data.status,
      });
      setAddModalOpen(false);
      setSelectedCode(null);
    },
    [activeChartId, addMutation],
  );

  const handleCodeSelect = useCallback((result: CodingHelperResult) => {
    setSelectedCode(result);
    setCodingHelperOpen(false);
    setAddModalOpen(true);
  }, []);

  const handleSaveDocument = useCallback(() => {
    if (!activeChartId) return;
    saveMutation.mutate({
      chartId: activeChartId,
      payload: { reviewer: 'RiskQ360', comments: 'Saved from Diagnoses panel' },
    });
  }, [activeChartId, saveMutation]);

  const toggleSortDir = useCallback(() => {
    setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
  }, []);

  if (isLoading) return <DiagnosesSkeleton />;

  if (isError) {
    return (
      <Box p={16}>
        <Alert
          icon={<IconAlertCircle size={18} />}
          title="Failed to load diagnoses"
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
            There was an error loading diagnosis data. The chart may still be processing.
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

  return (
    <Box style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Filter Bar */}
      <Box
        style={{
          padding: '8px 12px',
          borderBottom: '1px solid var(--mi-border)',
          backgroundColor: 'var(--mi-surface)',
          flexShrink: 0,
        }}
      >
        <Group gap={8} wrap="wrap">
          <TextInput
            placeholder="Search diagnoses..."
            leftSection={<IconSearch size={14} stroke={1.5} />}
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
            size="xs"
            style={{ flex: 1, minWidth: 160 }}
            styles={{
              input: { backgroundColor: 'var(--mi-surface)', borderColor: 'var(--mi-border)', color: 'var(--mi-text)', fontSize: 12 },
            }}
          />
          <MultiSelect
            placeholder="Negation..."
            leftSection={<IconFilter size={14} stroke={1.5} />}
            data={NEGATION_SELECT_DATA}
            value={negationFilter}
            onChange={setNegationFilter}
            size="xs"
            clearable
            searchable
            maxDropdownHeight={240}
            style={{ minWidth: 140 }}
            styles={{
              input: { backgroundColor: 'var(--mi-surface)', borderColor: 'var(--mi-border)', color: 'var(--mi-text)', fontSize: 12, minHeight: 30 },
              pill: { fontSize: 10 },
            }}
            renderOption={({ option }) => {
              const status = option.value as NegationStatus;
              return (
                <Group gap={8}>
                  <Box style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: `var(--mantine-color-${getNegationColor(status)}-5)` }} />
                  <Text size="xs">{option.label}</Text>
                </Group>
              );
            }}
          />
          <Select
            data={SORT_OPTIONS}
            value={sortField}
            onChange={(v) => { if (v) setSortField(v as SortField); }}
            size="xs"
            style={{ width: 130 }}
            styles={{
              input: { backgroundColor: 'var(--mi-surface)', borderColor: 'var(--mi-border)', color: 'var(--mi-text)', fontSize: 12 },
            }}
          />
          <Tooltip label={sortDir === 'asc' ? 'Sort ascending' : 'Sort descending'} withArrow>
            <ActionIcon size="sm" variant="subtle" onClick={toggleSortDir} style={{ color: 'var(--mi-text-muted)' }}>
              {sortDir === 'asc' ? <IconSortAscending size={16} stroke={1.5} /> : <IconSortDescending size={16} stroke={1.5} />}
            </ActionIcon>
          </Tooltip>
        </Group>

        {/* Action buttons + count */}
        <Group justify="space-between" mt={8}>
          <Group gap={8}>
            {/* Source filter tabs */}
            <Group
              gap={0}
              style={{
                borderRadius: 6,
                border: '1px solid var(--mi-border)',
                overflow: 'hidden',
              }}
            >
              {([['all', 'All'], ['ai', 'AI'], ['manual', 'Manual']] as const).map(([val, label]) => {
                const isActive = sourceFilter === val;
                const count = val === 'all'
                  ? (diagnoses?.length ?? 0)
                  : val === 'manual'
                    ? (diagnoses?.filter((d) => d.description?.startsWith('[Coder-added]')).length ?? 0)
                    : (diagnoses?.filter((d) => !d.description?.startsWith('[Coder-added]')).length ?? 0);
                return (
                  <Box
                    key={val}
                    onClick={() => setSourceFilter(val)}
                    style={{
                      padding: '2px 8px',
                      fontSize: 10,
                      fontWeight: isActive ? 700 : 500,
                      cursor: 'pointer',
                      backgroundColor: isActive ? 'var(--mi-primary)' : 'transparent',
                      color: isActive ? '#fff' : 'var(--mi-text-muted)',
                      transition: 'all 0.15s ease',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 3,
                    }}
                  >
                    {val === 'ai' && <IconRobot size={9} />}
                    {val === 'manual' && <IconUser size={9} />}
                    {label} {count > 0 && <span style={{ opacity: 0.7 }}>({count})</span>}
                  </Box>
                );
              })}
            </Group>
            <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>
              {filteredDiagnoses.length} shown
            </Text>
            {hasFilters && (
              <Button
                size="compact-xs"
                variant="subtle"
                color="gray"
                onClick={() => { setSearch(''); setNegationFilter([]); setSourceFilter('all'); }}
                styles={{ root: { fontSize: 10, fontWeight: 500, padding: '2px 6px', height: 'auto' } }}
              >
                Clear filters
              </Button>
            )}
          </Group>

          <Group gap={6}>
            {/* Add Diagnosis */}
            <Tooltip label="Add new diagnosis code" withArrow>
              <Button
                size="compact-xs"
                variant="light"
                color="blue"
                leftSection={<IconPlus size={12} />}
                onClick={() => setAddModalOpen(true)}
                styles={{ root: { fontSize: 10, fontWeight: 600 } }}
              >
                Add
              </Button>
            </Tooltip>

            {/* Coding Helper */}
            <Tooltip label="Search ICD-10 codes" withArrow>
              <Button
                size="compact-xs"
                variant="light"
                color="violet"
                leftSection={<IconSearch size={12} />}
                onClick={() => setCodingHelperOpen(true)}
                styles={{ root: { fontSize: 10, fontWeight: 600 } }}
              >
                Code Helper
              </Button>
            </Tooltip>

            {/* Save Document */}
            <Tooltip label="Save all reviewed data" withArrow>
              <Button
                size="compact-xs"
                variant="light"
                color="green"
                leftSection={<IconDeviceFloppy size={12} />}
                onClick={handleSaveDocument}
                loading={saveMutation.isPending}
                styles={{ root: { fontSize: 10, fontWeight: 600 } }}
              >
                Save
              </Button>
            </Tooltip>

            {/* Status summary badges */}
            {diagnoses && diagnoses.length > 0 && (
              <Group gap={4}>
                {ALL_NEGATION_STATUSES.map((status) => {
                  const count = diagnoses.filter((d) => d.negation_status === status).length;
                  if (count === 0) return null;
                  return (
                    <Tooltip key={status} label={`${getNegationLabel(status)}: ${count}`} withArrow>
                      <Badge
                        size="xs"
                        color={getNegationColor(status)}
                        variant={negationFilter.includes(status) ? 'filled' : 'light'}
                        radius="sm"
                        style={{ cursor: 'pointer', transition: 'all var(--mi-transition-fast)' }}
                        onClick={() => {
                          setNegationFilter((prev) =>
                            prev.includes(status) ? prev.filter((s) => s !== status) : [...prev, status],
                          );
                        }}
                      >
                        {count}
                      </Badge>
                    </Tooltip>
                  );
                })}
              </Group>
            )}
          </Group>
        </Group>
      </Box>

      {/* Diagnosis List */}
      <Box style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {filteredDiagnoses.length === 0 ? (
          <EmptyState hasFilters={hasFilters} />
        ) : (
          <Stack gap={8}>
            <AnimatePresence mode="popLayout">
              {filteredDiagnoses.map((diagnosis, index) => (
                <DiagnosisCard
                  key={`${diagnosis.icd10_code}-${diagnosis.id ?? index}`}
                  diagnosis={diagnosis}
                  index={index}
                  onAccept={handleAcceptClick}
                  onReject={handleRejectClick}
                  onDelete={handleDelete}
                  isReviewing={isAnyMutating}
                />
              ))}
            </AnimatePresence>
          </Stack>
        )}
      </Box>

      {/* Review Modal (Accept/Reject with comments) */}
      <ReviewModal
        opened={reviewModal.open}
        onClose={() => setReviewModal((m) => ({ ...m, open: false }))}
        onConfirm={handleReviewConfirm}
        action={reviewModal.action}
        itemType="Diagnosis"
        itemLabel={reviewModal.label}
        isPending={acceptMutation.isPending || rejectMutation.isPending}
      />

      {/* Add Diagnosis Modal */}
      <AddDiagnosisModal
        opened={addModalOpen}
        onClose={() => { setAddModalOpen(false); setSelectedCode(null); }}
        onSubmit={handleAddSubmit}
        onOpenCodingHelper={() => { setAddModalOpen(false); setCodingHelperOpen(true); }}
        prefilledCode={selectedCode}
        isPending={addMutation.isPending}
      />

      {/* Coding Helper Modal */}
      <CodingHelperModal
        opened={codingHelperOpen}
        onClose={() => setCodingHelperOpen(false)}
        onSelect={handleCodeSelect}
      />
    </Box>
  );
}
