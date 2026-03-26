import { useState, useMemo } from 'react';
import {
  Box,
  Text,
  Tabs,
  Stack,
  Group,
  Badge,
  Skeleton,
  Alert,
  Button,
  TextInput,
  Table,
  Tooltip,
  Collapse,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconHeartbeat,
  IconTestPipe,
  IconPill,
  IconCalendarEvent,
  IconMessageCircle,
  IconAlertCircle,
  IconRefresh,
  IconSearch,
  IconCheck,
  IconX,
  IconChevronDown,
  IconChevronUp,
  IconStethoscope,
  IconUser,
  IconBuilding,
  IconClock,
} from '@tabler/icons-react';
import { motion } from 'framer-motion';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { useChartStore } from '../../stores/chartStore';
import { useVitals, useLabs, useMedications, useEncounters, useSentences } from '../../hooks/useChart';
import type { Vital, LabResult, Medication, Encounter, ClinicalSentence } from '../../types/clinical';
import { formatDate, formatDateTime, formatCategory } from '../../utils/formatters';
import { NegationBadge } from '../shared/NegationBadge';
import { EvidenceSnippet } from '../shared/EvidenceSnippet';

/* -------------------------------------------------------------------------- */
/* Sub-tab definitions                                                         */
/* -------------------------------------------------------------------------- */
interface SubTabDef {
  value: string;
  label: string;
  icon: typeof IconHeartbeat;
}

const SUB_TABS: SubTabDef[] = [
  { value: 'vitals', label: 'Vitals', icon: IconHeartbeat },
  { value: 'labs', label: 'Labs', icon: IconTestPipe },
  { value: 'medications', label: 'Meds', icon: IconPill },
  { value: 'encounters', label: 'Encounters', icon: IconCalendarEvent },
  { value: 'sentences', label: 'Findings', icon: IconMessageCircle },
];

/* -------------------------------------------------------------------------- */
/* Generic loading skeleton                                                    */
/* -------------------------------------------------------------------------- */
function SubTabSkeleton() {
  return (
    <Stack gap={12} p={16}>
      <Skeleton height={24} width={160} radius="md" />
      <Skeleton height={180} radius="md" />
      <Skeleton height={100} radius="md" />
    </Stack>
  );
}

/* -------------------------------------------------------------------------- */
/* Generic empty state                                                         */
/* -------------------------------------------------------------------------- */
function SubTabEmpty({ label, icon: Icon }: { label: string; icon: typeof IconHeartbeat }) {
  return (
    <Box
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 40,
        gap: 12,
      }}
    >
      <Box
        style={{
          width: 48,
          height: 48,
          borderRadius: 'var(--mi-radius-lg)',
          background: 'color-mix(in srgb, var(--mi-primary) 8%, var(--mi-surface))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Icon size={24} stroke={1.2} color="var(--mi-text-muted)" />
      </Box>
      <Text size="sm" fw={600} style={{ color: 'var(--mi-text)' }}>
        No {label} Data
      </Text>
      <Text size="xs" c="dimmed" ta="center" maw={250}>
        {label} data will appear here once the chart has been processed.
      </Text>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Generic error state                                                         */
/* -------------------------------------------------------------------------- */
function SubTabError({ label, refetch }: { label: string; refetch: () => void }) {
  return (
    <Box p={16}>
      <Alert
        icon={<IconAlertCircle size={16} />}
        title={`Failed to load ${label}`}
        color="red"
        radius="md"
        styles={{
          root: {
            backgroundColor: 'color-mix(in srgb, var(--mi-error) 6%, var(--mi-surface))',
            borderColor: 'color-mix(in srgb, var(--mi-error) 20%, transparent)',
          },
        }}
      >
        <Button
          size="xs"
          variant="light"
          color="red"
          mt={6}
          leftSection={<IconRefresh size={14} />}
          onClick={refetch}
        >
          Retry
        </Button>
      </Alert>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Recharts custom tooltip                                                     */
/* -------------------------------------------------------------------------- */
interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}

function ChartTooltipContent({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <Box
      className="glass"
      style={{
        padding: '8px 12px',
        borderRadius: 'var(--mi-radius-md)',
        boxShadow: 'var(--mi-shadow-md)',
      }}
    >
      <Text size="xs" fw={600} style={{ color: 'var(--mi-text)' }} mb={4}>
        {label}
      </Text>
      {payload.map((entry, idx) => (
        <Group key={idx} gap={6}>
          <Box
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: entry.color,
            }}
          />
          <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
            {entry.name}: {entry.value}
          </Text>
        </Group>
      ))}
    </Box>
  );
}

/* ========================================================================= */
/* VITALS SUB-TAB                                                             */
/* ========================================================================= */
function VitalsSubTab() {
  const activeChartId = useChartStore((s) => s.activeChartId);
  const { data: vitals, isLoading, isError, refetch } = useVitals(activeChartId);

  if (isLoading) return <SubTabSkeleton />;
  if (isError) return <SubTabError label="vitals" refetch={refetch} />;
  if (!vitals || vitals.length === 0) return <SubTabEmpty label="Vitals" icon={IconHeartbeat} />;

  // Prepare BP chart data
  const bpData = vitals
    .filter((v: Vital) => v.bp_systolic || v.bp_diastolic || v.blood_pressure)
    .map((v: Vital) => {
      let systolic = v.bp_systolic ?? null;
      let diastolic = v.bp_diastolic ?? null;

      // Parse from blood_pressure string if individual values not available
      if ((systolic === null || diastolic === null) && v.blood_pressure) {
        const parts = v.blood_pressure.split('/');
        if (parts.length === 2) {
          systolic = systolic ?? (parseInt(parts[0], 10) || null);
          diastolic = diastolic ?? (parseInt(parts[1], 10) || null);
        }
      }

      return {
        date: formatDate(v.date),
        systolic,
        diastolic,
      };
    })
    .filter((d) => d.systolic !== null && d.diastolic !== null);

  return (
    <Stack gap={16} p={16}>
      {/* BP Chart */}
      {bpData.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
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
              <IconHeartbeat size={14} stroke={2} color="var(--mi-error)" />
              <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
                Blood Pressure Trend
              </Text>
              <Badge size="xs" variant="light" color="red" radius="sm">
                {bpData.length} readings
              </Badge>
            </Group>
            <Box style={{ width: '100%', minHeight: 200 }}>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={bpData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--mi-border)" opacity={0.5} />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: 'var(--mi-text-muted)', fontSize: 10 }}
                    stroke="var(--mi-border)"
                  />
                  <YAxis
                    domain={[40, 200]}
                    tick={{ fill: 'var(--mi-text-muted)', fontSize: 10 }}
                    stroke="var(--mi-border)"
                  />
                  <RechartsTooltip content={<ChartTooltipContent />} />
                  <ReferenceLine y={140} stroke="var(--mi-warning)" strokeDasharray="5 5" label="" />
                  <ReferenceLine y={90} stroke="var(--mi-warning)" strokeDasharray="5 5" label="" />
                  <Line
                    type="monotone"
                    dataKey="systolic"
                    stroke="#EF4444"
                    strokeWidth={2}
                    dot={{ r: 3, fill: '#EF4444' }}
                    activeDot={{ r: 5 }}
                    name="Systolic"
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="diastolic"
                    stroke="#3B82F6"
                    strokeWidth={2}
                    dot={{ r: 3, fill: '#3B82F6' }}
                    activeDot={{ r: 5 }}
                    name="Diastolic"
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </Box>
        </motion.div>
      )}

      {/* Vitals cards */}
      <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
        All Readings
      </Text>
      <Stack gap={8}>
        {vitals.map((vital: Vital, idx: number) => (
          <motion.div
            key={`${vital.date}-${idx}`}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(idx * 0.03, 0.3), duration: 0.2 }}
          >
            <Box
              style={{
                padding: '12px 14px',
                borderRadius: 'var(--mi-radius-lg)',
                backgroundColor: 'var(--mi-surface)',
                border: '1px solid var(--mi-border)',
              }}
            >
              <Group justify="space-between" mb={6}>
                <Text size="xs" fw={600} style={{ color: 'var(--mi-text)' }}>
                  {formatDate(vital.date)}
                </Text>
              </Group>
              <Group gap={12} wrap="wrap">
                {(vital.blood_pressure || vital.bp_systolic) && (
                  <Group gap={4}>
                    <IconHeartbeat size={12} stroke={1.5} color="var(--mi-error)" />
                    <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                      BP: {vital.blood_pressure ?? `${vital.bp_systolic}/${vital.bp_diastolic}`}
                    </Text>
                  </Group>
                )}
                {vital.weight && (
                  <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                    Weight: {vital.weight}
                  </Text>
                )}
                {vital.height && (
                  <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                    Height: {vital.height}
                  </Text>
                )}
                {vital.bmi && (
                  <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                    BMI: {vital.bmi}
                  </Text>
                )}
                {vital.pulse && (
                  <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                    Pulse: {vital.pulse}
                  </Text>
                )}
                {vital.temperature && (
                  <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                    Temp: {vital.temperature}
                  </Text>
                )}
                {vital.oxygen_saturation && (
                  <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                    SpO2: {vital.oxygen_saturation}
                  </Text>
                )}
              </Group>
              {vital.exact_quote && (
                <Box mt={8}>
                  <EvidenceSnippet
                    text={vital.exact_quote}
                    type="hedis"
                    label="Vital evidence"
                    maxLength={220}
                    meta={{
                      pageHint: Number(vital.page_number ?? 0) || undefined,
                      exactQuote: vital.exact_quote || undefined,
                    }}
                  />
                </Box>
              )}
            </Box>
          </motion.div>
        ))}
      </Stack>
    </Stack>
  );
}

/* ========================================================================= */
/* LABS SUB-TAB                                                               */
/* ========================================================================= */
function LabsSubTab() {
  const activeChartId = useChartStore((s) => s.activeChartId);
  const { data: labs, isLoading, isError, refetch } = useLabs(activeChartId);

  // Group by test_name for trend charts — must be before early returns (Rules of Hooks)
  const labsByTest = useMemo(() => {
    if (!labs || labs.length === 0) return {};
    const grouped: Record<string, LabResult[]> = {};
    labs.forEach((lab: LabResult) => {
      const key = lab.test_name;
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(lab);
    });
    return grouped;
  }, [labs]);

  const a1cChartData = useMemo(() => {
    const a1cKey = Object.keys(labsByTest).find((k) => k.toLowerCase().includes('a1c') || k.toLowerCase().includes('hba1c'));
    const a1cData = a1cKey ? labsByTest[a1cKey] : [];
    return a1cData
      .filter((l) => l.result_date && !isNaN(parseFloat(l.result_value)))
      .map((l) => ({
        date: formatDate(l.result_date),
        value: parseFloat(l.result_value),
      }));
  }, [labsByTest]);

  if (isLoading) return <SubTabSkeleton />;
  if (isError) return <SubTabError label="labs" refetch={refetch} />;
  if (!labs || labs.length === 0) return <SubTabEmpty label="Lab Results" icon={IconTestPipe} />;

  return (
    <Stack gap={16} p={16}>
      {/* A1C Trend Chart */}
      {a1cChartData.length > 1 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
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
              <IconTestPipe size={14} stroke={2} color="var(--mi-primary)" />
              <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
                A1C Trend
              </Text>
            </Group>
            <Box style={{ width: '100%', minHeight: 180 }}>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={a1cChartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--mi-border)" opacity={0.5} />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: 'var(--mi-text-muted)', fontSize: 10 }}
                    stroke="var(--mi-border)"
                  />
                  <YAxis
                    tick={{ fill: 'var(--mi-text-muted)', fontSize: 10 }}
                    stroke="var(--mi-border)"
                    domain={['auto', 'auto']}
                  />
                  <RechartsTooltip content={<ChartTooltipContent />} />
                  <ReferenceLine y={7} stroke="var(--mi-warning)" strokeDasharray="5 5" />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="var(--mi-primary)"
                    strokeWidth={2}
                    dot={{ r: 4, fill: 'var(--mi-primary)' }}
                    activeDot={{ r: 6 }}
                    name="A1C"
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </Box>
        </motion.div>
      )}

      {/* Lab Results - Card Layout */}
      <Group gap={8} mb={4}>
        <IconTestPipe size={14} stroke={2} color="var(--mi-primary)" />
        <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
          Lab Results
        </Text>
        <Badge size="xs" variant="light" color="gray" radius="xl" styles={{ root: { fontWeight: 600 } }}>
          {labs.length}
        </Badge>
      </Group>

      {Object.entries(labsByTest).map(([testName, results], groupIdx) => {
        const latest = results[0];
        const isInRange = latest.within_target === true;
        const isOutOfRange = latest.within_target === false;
        const statusColor = isInRange ? 'var(--mi-success)' : isOutOfRange ? 'var(--mi-error)' : 'var(--mi-text-muted)';
        const statusBg = isInRange
          ? 'color-mix(in srgb, var(--mi-success) 8%, transparent)'
          : isOutOfRange
            ? 'color-mix(in srgb, var(--mi-error) 8%, transparent)'
            : 'transparent';

        return (
          <motion.div
            key={testName}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: groupIdx * 0.03 }}
          >
            <Box
              style={{
                borderRadius: 12,
                border: `1px solid ${isOutOfRange ? 'color-mix(in srgb, var(--mi-error) 25%, var(--mi-border))' : 'var(--mi-border)'}`,
                background: 'var(--mi-surface)',
                overflow: 'hidden',
                transition: 'all var(--mi-transition-fast)',
              }}
            >
              {/* Thin accent bar at top */}
              <Box
                style={{
                  height: 2,
                  background: isOutOfRange
                    ? 'linear-gradient(90deg, var(--mi-error), #F87171)'
                    : isInRange
                      ? 'linear-gradient(90deg, var(--mi-success), #34D399)'
                      : 'linear-gradient(90deg, var(--mi-border), var(--mi-border))',
                }}
              />

              <Box style={{ padding: '10px 14px' }}>
                {/* Header row: test name + value + status */}
                <Group justify="space-between" align="flex-start" wrap="nowrap" mb={6}>
                  <Box style={{ flex: 1, minWidth: 0 }}>
                    <Group gap={8} wrap="nowrap">
                      <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }} lineClamp={1}>
                        {testName}
                      </Text>
                      {latest.hedis_measure && (
                        <Badge
                          size="xs"
                          variant="light"
                          color="violet"
                          radius="sm"
                          styles={{ root: { textTransform: 'none', flexShrink: 0, fontWeight: 600 } }}
                        >
                          {latest.hedis_measure}
                        </Badge>
                      )}
                    </Group>
                  </Box>

                  {/* Large value display */}
                  <Box
                    style={{
                      padding: '3px 10px',
                      borderRadius: 8,
                      backgroundColor: statusBg,
                      border: `1px solid ${isOutOfRange ? 'color-mix(in srgb, var(--mi-error) 20%, transparent)' : isInRange ? 'color-mix(in srgb, var(--mi-success) 20%, transparent)' : 'var(--mi-border)'}`,
                      flexShrink: 0,
                    }}
                  >
                    <Text
                      size="sm"
                      fw={800}
                      style={{
                        fontFamily: '"JetBrains Mono", monospace',
                        fontVariantNumeric: 'tabular-nums',
                        color: statusColor,
                        fontSize: 13,
                      }}
                    >
                      {latest.result_value}
                    </Text>
                  </Box>
                </Group>

                {/* Meta row: reference range, date, status badge */}
                <Group gap={12} wrap="wrap">
                  {latest.reference_range && (
                    <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 11 }}>
                      Ref: <Text component="span" inherit fw={600} style={{ color: 'var(--mi-text-secondary)' }}>{latest.reference_range}</Text>
                    </Text>
                  )}
                  {latest.result_date && (
                    <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 11 }}>
                      <IconClock size={10} style={{ display: 'inline', verticalAlign: '-1px', marginRight: 3 }} />
                      {formatDate(latest.result_date)}
                    </Text>
                  )}
                  {latest.within_target !== null && latest.within_target !== undefined && (
                    <Badge
                      size="xs"
                      color={latest.within_target ? 'green' : 'red'}
                      variant="light"
                      radius="sm"
                      leftSection={
                        latest.within_target
                          ? <IconCheck size={9} stroke={3} />
                          : <IconX size={9} stroke={3} />
                      }
                      styles={{ root: { textTransform: 'none', fontWeight: 700, fontSize: 9 } }}
                    >
                      {latest.within_target ? 'In Range' : 'Out of Range'}
                    </Badge>
                  )}
                </Group>

                {/* Evidence snippet */}
                {latest.exact_quote && (
                  <Box mt={6}>
                    <EvidenceSnippet
                      text={latest.exact_quote}
                      type="hedis"
                      label={testName}
                      maxLength={120}
                      meta={{
                        pageHint: Number(latest.page_number ?? 0) || undefined,
                        exactQuote: latest.exact_quote || undefined,
                      }}
                    />
                  </Box>
                )}

                {/* Previous results (if multiple) */}
                {results.length > 1 && (
                  <Box
                    mt={8}
                    style={{
                      padding: '6px 10px',
                      borderRadius: 8,
                      backgroundColor: 'var(--mi-surface-hover)',
                      border: '1px solid var(--mi-border)',
                    }}
                  >
                    <Text size="xs" fw={600} style={{ color: 'var(--mi-text-muted)', fontSize: 10, marginBottom: 4 }}>
                      History ({results.length} results)
                    </Text>
                    <Group gap={8} wrap="wrap">
                      {results.slice(1, 5).map((r, i) => (
                        <Badge
                          key={i}
                          size="xs"
                          variant="outline"
                          color={r.within_target === true ? 'green' : r.within_target === false ? 'red' : 'gray'}
                          radius="sm"
                          styles={{
                            root: {
                              textTransform: 'none',
                              fontFamily: '"JetBrains Mono", monospace',
                              fontWeight: 600,
                              fontSize: 10,
                            },
                          }}
                        >
                          {r.result_value} {r.result_date ? `(${formatDate(r.result_date)})` : ''}
                        </Badge>
                      ))}
                      {results.length > 5 && (
                        <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 10 }}>
                          +{results.length - 5} more
                        </Text>
                      )}
                    </Group>
                  </Box>
                )}
              </Box>
            </Box>
          </motion.div>
        );
      })}
    </Stack>
  );
}

/* ========================================================================= */
/* MEDICATIONS SUB-TAB                                                        */
/* ========================================================================= */
function MedicationsSubTab() {
  const activeChartId = useChartStore((s) => s.activeChartId);
  const { data: medications, isLoading, isError, refetch } = useMedications(activeChartId);

  if (isLoading) return <SubTabSkeleton />;
  if (isError) return <SubTabError label="medications" refetch={refetch} />;
  if (!medications || medications.length === 0) return <SubTabEmpty label="Medications" icon={IconPill} />;

  return (
    <Stack gap={8} p={16}>
      <Group gap={8} mb={4}>
        <IconPill size={14} stroke={2} color="var(--mi-primary)" />
        <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
          Medications
        </Text>
        <Badge size="sm" variant="light" color="blue" radius="md">
          {medications.length}
        </Badge>
      </Group>

      {medications.map((med: Medication, idx: number) => (
        <motion.div
          key={`${med.name}-${idx}`}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: Math.min(idx * 0.03, 0.3), duration: 0.2 }}
        >
          <Box
            style={{
              padding: '12px 14px',
              borderRadius: 'var(--mi-radius-lg)',
              backgroundColor: 'var(--mi-surface)',
              border: '1px solid var(--mi-border)',
              transition: 'all var(--mi-transition-fast)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--mi-primary) 25%, transparent)';
              e.currentTarget.style.boxShadow = 'var(--mi-shadow-sm)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--mi-border)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            <Group justify="space-between" align="flex-start" wrap="nowrap" mb={4}>
              <Group gap={8} align="center" style={{ minWidth: 0 }}>
                <Box
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    backgroundColor: 'var(--mi-primary)',
                    flexShrink: 0,
                  }}
                />
                <Text
                  size="sm"
                  fw={600}
                  style={{
                    color: 'var(--mi-text)',
                    minWidth: 0,
                  }}
                  lineClamp={1}
                >
                  {med.name}
                </Text>
              </Group>
              {med.action && (
                <Badge
                  size="xs"
                  variant="light"
                  color="blue"
                  radius="sm"
                  styles={{ root: { textTransform: 'none', flexShrink: 0 } }}
                >
                  {med.action}
                </Badge>
              )}
            </Group>

            <Group gap={12} wrap="wrap">
              {med.dose_form && (
                <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                  {med.dose_form}
                </Text>
              )}
              {med.instructions && (
                <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>
                  {med.instructions}
                </Text>
              )}
              {med.indication && (
                <Badge
                  size="xs"
                  variant="outline"
                  color="gray"
                  radius="sm"
                  styles={{ root: { textTransform: 'none' } }}
                >
                  {med.indication}
                </Badge>
              )}
            </Group>
            {med.exact_quote && (
              <Box mt={8}>
                <EvidenceSnippet
                  text={med.exact_quote}
                  type="hedis"
                  label={med.name}
                  maxLength={220}
                  meta={{
                    pageHint: Number(med.page_number ?? 0) || undefined,
                    exactQuote: med.exact_quote || undefined,
                  }}
                />
              </Box>
            )}
          </Box>
        </motion.div>
      ))}
    </Stack>
  );
}

/* ========================================================================= */
/* ENCOUNTERS SUB-TAB                                                         */
/* ========================================================================= */
function EncountersSubTab() {
  const activeChartId = useChartStore((s) => s.activeChartId);
  const { data: encounters, isLoading, isError, refetch } = useEncounters(activeChartId);

  if (isLoading) return <SubTabSkeleton />;
  if (isError) return <SubTabError label="encounters" refetch={refetch} />;
  if (!encounters || encounters.length === 0) return <SubTabEmpty label="Encounters" icon={IconCalendarEvent} />;

  return (
    <Stack gap={0} p={16}>
      <Group gap={8} mb={12}>
        <IconCalendarEvent size={14} stroke={2} color="var(--mi-primary)" />
        <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>
          Encounter Timeline
        </Text>
        <Badge size="sm" variant="light" color="blue" radius="md">
          {encounters.length}
        </Badge>
      </Group>

      {/* Timeline */}
      <Box style={{ position: 'relative', paddingLeft: 24 }}>
        {/* Vertical line */}
        <Box
          style={{
            position: 'absolute',
            left: 7,
            top: 8,
            bottom: 8,
            width: 2,
            backgroundColor: 'var(--mi-border)',
            borderRadius: 1,
          }}
        />

        <Stack gap={12}>
          {encounters.map((enc: Encounter, idx: number) => (
            <EncounterTimelineItem key={`${enc.date}-${idx}`} encounter={enc} index={idx} />
          ))}
        </Stack>
      </Box>
    </Stack>
  );
}

function EncounterTimelineItem({ encounter, index }: { encounter: Encounter; index: number }) {
  const [opened, { toggle }] = useDisclosure(false);
  const evidenceItems = encounter.evidence_items ?? [];
  const primaryEvidence = encounter.evidence ?? evidenceItems[0]?.exact_quote ?? null;
  const pageHint =
    encounter.page_number ??
    evidenceItems.find((ev) => ev.page_number !== null && ev.page_number !== undefined)?.page_number ??
    null;
  const hasDetails =
    (encounter.procedures && encounter.procedures.length > 0) ||
    (encounter.diagnoses && encounter.diagnoses.length > 0) ||
    (encounter.medications && encounter.medications.length > 0) ||
    evidenceItems.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index * 0.04, 0.3), duration: 0.2 }}
      style={{ position: 'relative' }}
    >
      {/* Timeline dot */}
      <Box
        style={{
          position: 'absolute',
          left: -21,
          top: 10,
          width: 12,
          height: 12,
          borderRadius: '50%',
          backgroundColor: 'var(--mi-primary)',
          border: '3px solid var(--mi-surface)',
          boxShadow: '0 0 0 2px var(--mi-border)',
          zIndex: 2,
        }}
      />

      <Box
        onClick={hasDetails ? toggle : undefined}
        style={{
          padding: '12px 14px',
          borderRadius: 'var(--mi-radius-lg)',
          backgroundColor: 'var(--mi-surface)',
          border: '1px solid var(--mi-border)',
          cursor: hasDetails ? 'pointer' : 'default',
          transition: 'all var(--mi-transition-fast)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--mi-primary) 25%, transparent)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'var(--mi-border)';
        }}
      >
        {/* Date + Type */}
        <Group justify="space-between" mb={6} wrap="nowrap">
          <Group gap={8} align="center">
            <Text size="xs" fw={700} style={{ color: 'var(--mi-primary)' }}>
              {formatDate(encounter.date)}
            </Text>
            {encounter.type && (
              <Badge
                size="xs"
                variant="light"
                color="blue"
                radius="sm"
                styles={{ root: { textTransform: 'none' } }}
              >
                {encounter.type}
              </Badge>
            )}
          </Group>
          {hasDetails && (
            <Box style={{ color: 'var(--mi-text-muted)', flexShrink: 0 }}>
              {opened ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
            </Box>
          )}
        </Group>

        {/* Provider + Facility */}
        <Group gap={12} wrap="wrap" mb={encounter.chief_complaint ? 6 : 0}>
          {encounter.provider && (
            <Group gap={4}>
              <IconUser size={11} stroke={1.5} color="var(--mi-text-muted)" />
              <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                {encounter.provider}
              </Text>
            </Group>
          )}
          {encounter.facility && (
            <Group gap={4}>
              <IconBuilding size={11} stroke={1.5} color="var(--mi-text-muted)" />
              <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                {encounter.facility}
              </Text>
            </Group>
          )}
        </Group>

        {/* Chief Complaint */}
        {encounter.chief_complaint && (
          <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>
            CC: {encounter.chief_complaint}
          </Text>
        )}
        {(encounter.assertion_count || (encounter.categories && encounter.categories.length > 0)) && (
          <Group gap={6} mt={6} wrap="wrap">
            {encounter.assertion_count ? (
              <Badge size="xs" variant="light" color="gray" radius="sm" styles={{ root: { textTransform: 'none' } }}>
                {encounter.assertion_count} linked assertions
              </Badge>
            ) : null}
            {(encounter.categories ?? []).slice(0, 4).map((cat) => (
              <Badge key={cat} size="xs" variant="outline" color="gray" radius="sm" styles={{ root: { textTransform: 'none' } }}>
                {cat}
              </Badge>
            ))}
          </Group>
        )}
        {primaryEvidence && (
          <Box mt={8}>
            <EvidenceSnippet
              text={primaryEvidence}
              type="hedis"
              label={encounter.type ?? 'Encounter evidence'}
              maxLength={220}
              meta={{
                pageHint: Number(pageHint ?? 0) || undefined,
                exactQuote: primaryEvidence || undefined,
              }}
            />
          </Box>
        )}

        {/* Expanded details */}
        <Collapse in={opened}>
          <Stack gap={8} mt={10} style={{ borderTop: '1px solid var(--mi-border)', paddingTop: 10 }}>
            {evidenceItems.length > 1 && (
              <Box>
                <Text size="xs" fw={600} mb={4} style={{ color: 'var(--mi-text-muted)', textTransform: 'uppercase', fontSize: 10, letterSpacing: '0.04em' }}>
                  Evidence ({evidenceItems.length})
                </Text>
                <Stack gap={6}>
                  {evidenceItems.slice(0, 5).map((ev, i) => (
                    <EvidenceSnippet
                      key={`${ev.page_number ?? 'p'}-${i}`}
                      text={ev.exact_quote ?? ''}
                      type="hedis"
                      label={ev.category ?? 'evidence'}
                      maxLength={220}
                      meta={{
                        pageHint: Number(ev.page_number ?? 0) || undefined,
                        exactQuote: ev.exact_quote || undefined,
                      }}
                    />
                  ))}
                </Stack>
              </Box>
            )}
            {/* Procedures */}
            {encounter.procedures && encounter.procedures.length > 0 && (
              <Box>
                <Text size="xs" fw={600} mb={4} style={{ color: 'var(--mi-text-muted)', textTransform: 'uppercase', fontSize: 10, letterSpacing: '0.04em' }}>
                  Procedures ({encounter.procedures.length})
                </Text>
                <Stack gap={4}>
                  {encounter.procedures.map((proc, i) => (
                    <Group key={i} gap={8}>
                      <Badge
                        size="xs"
                        variant="outline"
                        color="violet"
                        radius="sm"
                        styles={{ root: { fontFamily: 'monospace', textTransform: 'none', fontWeight: 600 } }}
                      >
                        {proc.cpt_code}
                      </Badge>
                      <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                        {proc.name}
                      </Text>
                      {proc.status && (
                        <Badge size="xs" variant="light" color="green" radius="sm" styles={{ root: { textTransform: 'none' } }}>
                          {proc.status}
                        </Badge>
                      )}
                    </Group>
                  ))}
                </Stack>
              </Box>
            )}

            {/* Diagnoses */}
            {encounter.diagnoses && encounter.diagnoses.length > 0 && (
              <Box>
                <Text size="xs" fw={600} mb={4} style={{ color: 'var(--mi-text-muted)', textTransform: 'uppercase', fontSize: 10, letterSpacing: '0.04em' }}>
                  Diagnoses ({encounter.diagnoses.length})
                </Text>
                <Stack gap={4}>
                  {encounter.diagnoses.map((dx, i) => (
                    <Group key={i} gap={8}>
                      <Badge
                        size="xs"
                        variant="filled"
                        color="violet"
                        radius="sm"
                        styles={{ root: { fontFamily: 'monospace', textTransform: 'none', fontWeight: 600 } }}
                      >
                        {dx.icd10_code}
                      </Badge>
                      <Text size="xs" style={{ color: 'var(--mi-text-secondary)', flex: 1, minWidth: 0 }} lineClamp={1}>
                        {dx.description}
                      </Text>
                      <NegationBadge status={dx.negation_status} size="xs" />
                    </Group>
                  ))}
                </Stack>
              </Box>
            )}
          </Stack>
        </Collapse>
      </Box>
    </motion.div>
  );
}

/* ========================================================================= */
/* SENTENCES SUB-TAB                                                          */
/* ========================================================================= */
function SentencesSubTab() {
  const activeChartId = useChartStore((s) => s.activeChartId);
  const { data: sentences, isLoading, isError, refetch } = useSentences(activeChartId);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const categories = useMemo(() => {
    if (!sentences) return [];
    const cats = new Set(sentences.map((s: ClinicalSentence) => s.category));
    return Array.from(cats).sort();
  }, [sentences]);

  const filtered = useMemo(() => {
    if (!sentences) return [];
    let result = [...sentences];

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(
        (s: ClinicalSentence) =>
          (s.text ?? '').toLowerCase().includes(q) ||
          (s.category ?? '').toLowerCase().includes(q) ||
          (s.negated_item?.toLowerCase().includes(q) ?? false),
      );
    }

    if (categoryFilter) {
      result = result.filter((s: ClinicalSentence) => s.category === categoryFilter);
    }

    return result;
  }, [sentences, search, categoryFilter]);

  if (isLoading) return <SubTabSkeleton />;
  if (isError) return <SubTabError label="sentences" refetch={refetch} />;
  if (!sentences || sentences.length === 0) return <SubTabEmpty label="Sentences" icon={IconMessageCircle} />;

  return (
    <Box style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Filter Bar */}
      <Box
        style={{
          padding: '10px 16px',
          borderBottom: '1px solid var(--mi-border)',
          flexShrink: 0,
        }}
      >
        <Group gap={8} wrap="wrap">
          <TextInput
            placeholder="Search sentences..."
            leftSection={<IconSearch size={14} stroke={1.5} />}
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
            size="xs"
            style={{ flex: 1, minWidth: 150 }}
            styles={{
              input: {
                backgroundColor: 'var(--mi-surface)',
                borderColor: 'var(--mi-border)',
                color: 'var(--mi-text)',
                fontSize: 12,
              },
            }}
          />
        </Group>

        {/* Category chips */}
        <Group gap={4} mt={8} wrap="wrap">
          <Badge
            size="xs"
            variant={categoryFilter === null ? 'filled' : 'light'}
            color="blue"
            radius="sm"
            style={{ cursor: 'pointer', transition: 'all var(--mi-transition-fast)' }}
            onClick={() => setCategoryFilter(null)}
          >
            All ({sentences.length})
          </Badge>
          {categories.map((cat) => {
            const count = sentences.filter((s: ClinicalSentence) => s.category === cat).length;
            return (
              <Badge
                key={cat}
                size="xs"
                variant={categoryFilter === cat ? 'filled' : 'light'}
                color="gray"
                radius="sm"
                style={{ cursor: 'pointer', textTransform: 'none', transition: 'all var(--mi-transition-fast)' }}
                onClick={() => setCategoryFilter(categoryFilter === cat ? null : cat)}
              >
                {formatCategory(cat)} ({count})
              </Badge>
            );
          })}
        </Group>

        <Text size="xs" mt={6} style={{ color: 'var(--mi-text-muted)' }}>
          {filtered.length} of {sentences.length} findings
        </Text>
      </Box>

      {/* Sentence List */}
      <Box style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        <Stack gap={6}>
          {filtered.map((sentence: ClinicalSentence, idx: number) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(idx * 0.02, 0.2), duration: 0.15 }}
            >
              <Box
                style={{
                  padding: '10px 12px',
                  borderRadius: 'var(--mi-radius-md)',
                  backgroundColor: 'var(--mi-surface)',
                  border: '1px solid var(--mi-border)',
                  transition: 'all var(--mi-transition-fast)',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--mi-primary) 20%, transparent)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--mi-border)';
                }}
              >
                <Group gap={6} mb={4} wrap="wrap">
                  <Badge
                    size="xs"
                    variant="light"
                    color="blue"
                    radius="sm"
                    styles={{ root: { textTransform: 'none' } }}
                  >
                    {formatCategory(sentence.category)}
                  </Badge>
                  {sentence.is_negated && (
                    <Badge
                      size="xs"
                      variant="light"
                      color="red"
                      radius="sm"
                      leftSection={<IconX size={8} stroke={2.5} />}
                      styles={{ root: { textTransform: 'none' } }}
                    >
                      Negated
                    </Badge>
                  )}
                  {sentence.negation_trigger && (
                    <Badge
                      size="xs"
                      variant="outline"
                      color="orange"
                      radius="sm"
                      styles={{ root: { textTransform: 'none' } }}
                    >
                      {sentence.negation_trigger}
                    </Badge>
                  )}
                </Group>
                <EvidenceSnippet
                  text={sentence.text}
                  type={sentence.is_negated ? 'negated' : 'diagnosis'}
                  label={sentence.category}
                  maxLength={300}
                />
              </Box>
            </motion.div>
          ))}
          {filtered.length === 0 && (
            <Text size="sm" c="dimmed" ta="center" py={20}>
              No sentences matching your filters.
            </Text>
          )}
        </Stack>
      </Box>
    </Box>
  );
}

/* ========================================================================= */
/* MAIN CLINICAL PANEL                                                        */
/* ========================================================================= */
export function ClinicalPanel() {
  const [activeSubTab, setActiveSubTab] = useState('vitals');

  return (
    <Box
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <Tabs
        value={activeSubTab}
        onChange={(val) => { if (val) setActiveSubTab(val); }}
        variant="default"
        keepMounted={false}
        style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
        styles={{
          root: { height: '100%', display: 'flex', flexDirection: 'column' },
          panel: { flex: 1, overflow: 'auto', padding: 0 },
        }}
      >
        <Tabs.List
          style={{
            padding: '4px 12px 0',
            borderBottom: '1px solid var(--mi-border)',
            backgroundColor: 'var(--mi-surface-hover)',
            flexShrink: 0,
            gap: 0,
            flexWrap: 'nowrap',
            overflowX: 'auto',
            scrollbarWidth: 'none',
          }}
        >
          {SUB_TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeSubTab === tab.value;
            return (
              <Tabs.Tab
                key={tab.value}
                value={tab.value}
                leftSection={
                  <Icon
                    size={13}
                    stroke={isActive ? 2 : 1.5}
                    style={{
                      color: isActive ? 'var(--mi-primary)' : 'var(--mi-text-muted)',
                      transition: 'color var(--mi-transition-fast)',
                    }}
                  />
                }
                style={{
                  fontSize: 11,
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? 'var(--mi-text)' : 'var(--mi-text-muted)',
                  borderBottom: isActive ? '2px solid var(--mi-primary)' : '2px solid transparent',
                  padding: '6px 8px',
                  transition: 'all var(--mi-transition-fast)',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}
              >
                {tab.label}
              </Tabs.Tab>
            );
          })}
        </Tabs.List>

        <Tabs.Panel value="vitals">
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.15 }}
            style={{ height: '100%' }}
          >
            <VitalsSubTab />
          </motion.div>
        </Tabs.Panel>

        <Tabs.Panel value="labs">
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.15 }}
            style={{ height: '100%' }}
          >
            <LabsSubTab />
          </motion.div>
        </Tabs.Panel>

        <Tabs.Panel value="medications">
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.15 }}
            style={{ height: '100%' }}
          >
            <MedicationsSubTab />
          </motion.div>
        </Tabs.Panel>

        <Tabs.Panel value="encounters">
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.15 }}
            style={{ height: '100%' }}
          >
            <EncountersSubTab />
          </motion.div>
        </Tabs.Panel>

        <Tabs.Panel value="sentences">
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.15 }}
            style={{ height: '100%' }}
          >
            <SentencesSubTab />
          </motion.div>
        </Tabs.Panel>
      </Tabs>
    </Box>
  );
}
