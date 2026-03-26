import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  Text,
  Stack,
  Group,
  Badge,
  Skeleton,
  Alert,
  Button,
  TextInput,
  NumberInput,
  Slider,
  Switch,
  Select,
  Textarea,
  SimpleGrid,
  Tooltip,
  Loader,
  Tabs,
  ThemeIcon,
  ScrollArea,
  Divider,
  Progress,
} from '@mantine/core';
import {
  IconSettings,
  IconAlertCircle,
  IconRefresh,
  IconDeviceFloppy,
  IconArrowBackUp,
  IconBrain,
  IconAdjustments,
  IconToggleLeft,
  IconCode,
  IconRobot,
  IconCheck,
  IconShieldCheck,
  IconDatabase,
  IconHeartRateMonitor,
  IconInfoCircle,
  IconSearch,
  IconTrash,
  IconSparkles,
  IconCpu,
  IconCloudComputing,
  IconBrandOpenai,
  IconTemperature,
  IconMaximize,
  IconStack2,
  IconArrowsShuffle,
  IconGauge,
  IconCalendar,
  IconPercentage,
  IconTargetArrow,
} from '@tabler/icons-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  useConfig,
  useUpdateConfig,
  usePrompts,
  useFeatureFlags,
  useUpdateFeatureFlags,
  useHedisMeasureCatalog,
  useUpdateHedisMeasureProfile,
  useHedisMeasureDefinition,
  useSaveHedisMeasureDefinition,
  useDeleteHedisMeasureDefinition,
} from '../../hooks/useChart';
import type { SystemConfig, FeatureFlags, PromptTemplates } from '../../types/api';

/* -------------------------------------------------------------------------- */
/* Constants                                                                   */
/* -------------------------------------------------------------------------- */
const TAB_ID = {
  AI: 'ai-engine',
  PIPELINE: 'pipeline',
  ML: 'ml-risk',
  FLAGS: 'feature-flags',
  HEDIS: 'quality-hedis',
  PROMPTS: 'prompts',
} as const;

const PROVIDER_OPTIONS = [
  { value: 'openai', label: 'OpenAI', icon: IconBrandOpenai, color: '#10A37F', desc: 'GPT-4o, GPT-4o-mini' },
  { value: 'azure', label: 'Azure OpenAI', icon: IconCloudComputing, color: '#0078D4', desc: 'Enterprise deployments' },
  { value: 'gemini', label: 'Google Gemini', icon: IconSparkles, color: '#4285F4', desc: 'Gemini Pro, Ultra' },
  { value: 'anthropic', label: 'Anthropic', icon: IconCpu, color: '#D97706', desc: 'Claude Opus, Sonnet' },
];

const FLAG_DESCRIPTIONS: Record<string, string> = {
  enable_risk_adjustment: 'Run HCC/RAF risk adjustment pipeline on chart processing',
  enable_hedis: 'Run HEDIS quality measure evaluation pipeline',
  enable_ml_predictions: 'Use BioClinicalBERT for ML-based HCC predictions',
  enable_llm_verification: 'Verify ICD codes with LLM + MEAT validation',
  enable_ocr_fallback: 'Use GPT-4o Vision OCR for low-quality pages',
  enable_parallel_pipelines: 'Process extraction pipelines in parallel',
  enable_negation_detection: 'Apply ConText/NegEx negation gating',
  enable_tfidf_retrieval: 'Use TF-IDF for ICD-10 code retrieval',
  enable_audit_scoring: 'Compute per-diagnosis audit risk scores',
  enable_hierarchy_suppression: 'Apply V28 HCC hierarchy suppression rules',
};

const FLAG_CATEGORIES: Record<string, string[]> = {
  'Risk Adjustment': ['enable_risk_adjustment', 'enable_ml_predictions', 'enable_tfidf_retrieval', 'enable_negation_detection', 'enable_hierarchy_suppression', 'enable_audit_scoring'],
  'Quality': ['enable_hedis'],
  'Processing': ['enable_llm_verification', 'enable_ocr_fallback', 'enable_parallel_pipelines'],
};

/* -------------------------------------------------------------------------- */
/* Shared Styles                                                               */
/* -------------------------------------------------------------------------- */
const inputStyles = {
  input: {
    backgroundColor: 'var(--mi-surface)',
    borderColor: 'var(--mi-border)',
    color: 'var(--mi-text)',
    fontSize: 13,
    borderRadius: 'var(--mi-radius-md)',
  },
  label: {
    color: 'var(--mi-text)',
    fontSize: 12,
    fontWeight: 600,
    marginBottom: 4,
  },
  description: {
    color: 'var(--mi-text-muted)',
    fontSize: 11,
  },
};

/* -------------------------------------------------------------------------- */
/* Setting Row                                                                 */
/* -------------------------------------------------------------------------- */
interface SettingRowProps {
  label: string;
  description?: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  span?: boolean;
}

function SettingRow({ label, description, icon, children, span }: SettingRowProps) {
  return (
    <Box
      style={{
        padding: '16px 20px',
        borderRadius: 'var(--mi-radius-lg)',
        backgroundColor: 'var(--mi-surface)',
        border: '1px solid var(--mi-border)',
        gridColumn: span ? '1 / -1' : undefined,
      }}
    >
      <Group justify="space-between" align="flex-start" wrap="nowrap" gap={24}>
        <Box style={{ flex: 1, minWidth: 0 }}>
          <Group gap={8} mb={description ? 4 : 0}>
            {icon}
            <Text size="sm" fw={600} style={{ color: 'var(--mi-text)' }}>
              {label}
            </Text>
          </Group>
          {description && (
            <Text size="xs" style={{ color: 'var(--mi-text-muted)', lineHeight: 1.5, marginLeft: icon ? 24 : 0 }}>
              {description}
            </Text>
          )}
        </Box>
        <Box style={{ flexShrink: 0, minWidth: 200, maxWidth: 320 }}>
          {children}
        </Box>
      </Group>
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* Skeleton                                                                    */
/* -------------------------------------------------------------------------- */
function ConfigSkeleton() {
  return (
    <Stack gap={24} p={24}>
      <Skeleton height={28} width={200} radius="md" />
      <Skeleton height={44} radius="md" />
      <SimpleGrid cols={2} spacing={16}>
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Skeleton key={i} height={80} radius="lg" />
        ))}
      </SimpleGrid>
    </Stack>
  );
}

/* -------------------------------------------------------------------------- */
/* Main Config Panel                                                           */
/* -------------------------------------------------------------------------- */
export function ConfigPanel() {
  const { data: config, isLoading: configLoading, isError: configError, refetch: refetchConfig } = useConfig();
  const { data: promptData, isLoading: promptsLoading } = usePrompts();
  const { data: featureFlagsData, isLoading: flagsLoading } = useFeatureFlags();
  const { data: hedisCatalog, isLoading: hedisCatalogLoading } = useHedisMeasureCatalog();
  const updateConfigMutation = useUpdateConfig();
  const updateFlagsMutation = useUpdateFeatureFlags();
  const updateHedisProfileMutation = useUpdateHedisMeasureProfile();
  const saveMeasureDefMutation = useSaveHedisMeasureDefinition();
  const deleteMeasureDefMutation = useDeleteHedisMeasureDefinition();

  const [activeTab, setActiveTab] = useState<string>(TAB_ID.AI);

  /* Local form state */
  const [llmProvider, setLlmProvider] = useState('');
  const [llmModel, setLlmModel] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(4096);

  const [chunkSize, setChunkSize] = useState(1000);
  const [chunkOverlap, setChunkOverlap] = useState(200);
  const [qualityThreshold, setQualityThreshold] = useState(0.5);
  const [measurementYear, setMeasurementYear] = useState(2024);

  const [mlConfidence, setMlConfidence] = useState(0.5);
  const [tfidfSimilarity, setTfidfSimilarity] = useState(0.3);

  const [localFlags, setLocalFlags] = useState<FeatureFlags>({});

  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);
  const [promptText, setPromptText] = useState('');
  const [measureSearch, setMeasureSearch] = useState('');
  const [activeMeasureIds, setActiveMeasureIds] = useState<string[]>([]);
  const [selectedMeasureId, setSelectedMeasureId] = useState<string | null>(null);
  const [measureDefinitionText, setMeasureDefinitionText] = useState('');
  const { data: measureDefinitionData } = useHedisMeasureDefinition(selectedMeasureId);

  const [hasChanges, setHasChanges] = useState(false);

  /* Populate form from config data */
  useEffect(() => {
    if (config) {
      setLlmProvider(config.llm?.provider ?? '');
      setLlmModel(config.llm?.model ?? '');
      setTemperature(config.llm?.temperature ?? 0.7);
      setMaxTokens(config.llm?.max_tokens ?? 4096);
      setChunkSize(config.pipeline?.chunk_size ?? 1000);
      setChunkOverlap(config.pipeline?.chunk_overlap ?? 200);
      setQualityThreshold(config.pipeline?.quality_threshold ?? 0.5);
      setMeasurementYear(config.pipeline?.measurement_year ?? 2024);
      setMlConfidence(config.ml?.ml_confidence_threshold ?? 0.5);
      setTfidfSimilarity(config.ml?.tfidf_similarity_threshold ?? 0.3);
    }
  }, [config]);

  useEffect(() => {
    if (featureFlagsData) setLocalFlags(featureFlagsData);
  }, [featureFlagsData]);

  useEffect(() => {
    if (hedisCatalog?.profile?.active_measure_ids) {
      setActiveMeasureIds(hedisCatalog.profile.active_measure_ids);
    }
    if (!selectedMeasureId && (hedisCatalog?.measures?.length ?? 0) > 0) {
      setSelectedMeasureId(hedisCatalog!.measures[0].measure_id);
    }
  }, [hedisCatalog]);

  useEffect(() => {
    if (measureDefinitionData?.definition) {
      setMeasureDefinitionText(JSON.stringify(measureDefinitionData.definition, null, 2));
    }
  }, [measureDefinitionData]);

  useEffect(() => {
    if (promptData) {
      const allPrompts = { ...promptData.db_prompts, ...promptData.file_prompts };
      const keys = Object.keys(allPrompts);
      if (keys.length > 0 && !selectedPrompt) {
        setSelectedPrompt(keys[0]);
        const val = allPrompts[keys[0]];
        setPromptText(typeof val === 'string' ? val : JSON.stringify(val, null, 2));
      }
    }
  }, [promptData, selectedPrompt]);

  const markChanged = useCallback(() => setHasChanges(true), []);

  /* Save config */
  const handleSave = useCallback(() => {
    const configPayload: Partial<SystemConfig> = {
      llm: { provider: llmProvider, model: llmModel, temperature, max_tokens: maxTokens },
      pipeline: { chunk_size: chunkSize, chunk_overlap: chunkOverlap, quality_threshold: qualityThreshold, measurement_year: measurementYear },
      ml: { ml_confidence_threshold: mlConfidence, tfidf_similarity_threshold: tfidfSimilarity },
    };
    updateConfigMutation.mutate(configPayload, { onSuccess: () => setHasChanges(false) });
  }, [llmProvider, llmModel, temperature, maxTokens, chunkSize, chunkOverlap, qualityThreshold, measurementYear, mlConfidence, tfidfSimilarity, updateConfigMutation]);

  const handleSaveFlags = useCallback(() => {
    updateFlagsMutation.mutate(localFlags);
  }, [localFlags, updateFlagsMutation]);

  const handleReset = useCallback(() => {
    if (config) {
      setLlmProvider(config.llm?.provider ?? '');
      setLlmModel(config.llm?.model ?? '');
      setTemperature(config.llm?.temperature ?? 0.7);
      setMaxTokens(config.llm?.max_tokens ?? 4096);
      setChunkSize(config.pipeline?.chunk_size ?? 1000);
      setChunkOverlap(config.pipeline?.chunk_overlap ?? 200);
      setQualityThreshold(config.pipeline?.quality_threshold ?? 0.5);
      setMeasurementYear(config.pipeline?.measurement_year ?? 2024);
      setMlConfidence(config.ml?.ml_confidence_threshold ?? 0.5);
      setTfidfSimilarity(config.ml?.tfidf_similarity_threshold ?? 0.3);
      setHasChanges(false);
    }
  }, [config]);

  const toggleFlag = useCallback((key: string) => {
    setLocalFlags((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const handlePromptSelect = useCallback((value: string | null) => {
    if (!value || !promptData) return;
    setSelectedPrompt(value);
    const allPrompts = { ...promptData.db_prompts, ...promptData.file_prompts };
    const val = allPrompts[value];
    setPromptText(typeof val === 'string' ? val : JSON.stringify(val, null, 2));
  }, [promptData]);

  const toggleHedisMeasure = useCallback((measureId: string) => {
    setActiveMeasureIds((prev) =>
      prev.includes(measureId) ? prev.filter((m) => m !== measureId) : [...prev, measureId],
    );
  }, []);

  const saveHedisProfile = useCallback(() => {
    updateHedisProfileMutation.mutate(activeMeasureIds);
  }, [activeMeasureIds, updateHedisProfileMutation]);

  const saveMeasureDefinition = useCallback(() => {
    if (!selectedMeasureId) return;
    let parsed: Record<string, unknown>;
    try { parsed = JSON.parse(measureDefinitionText); } catch { return; }
    saveMeasureDefMutation.mutate({ measureId: selectedMeasureId, definition: parsed });
  }, [measureDefinitionText, saveMeasureDefMutation, selectedMeasureId]);

  const promptOptions = useMemo(() => {
    if (!promptData) return [];
    const allPrompts = { ...promptData.db_prompts, ...promptData.file_prompts };
    return Object.keys(allPrompts).map((key) => ({
      value: key,
      label: key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
    }));
  }, [promptData]);

  const filteredMeasures = useMemo(() => {
    return (hedisCatalog?.measures ?? []).filter((m) => {
      const q = measureSearch.trim().toLowerCase();
      if (!q) return true;
      return m.measure_id.toLowerCase().includes(q) || m.name.toLowerCase().includes(q) ||
        (m.description ?? '').toLowerCase().includes(q) || (m.domain ?? '').toLowerCase().includes(q);
    });
  }, [hedisCatalog, measureSearch]);

  if (configLoading) return <ConfigSkeleton />;

  if (configError) {
    return (
      <Box p={24}>
        <Alert icon={<IconAlertCircle size={18} />} title="Failed to load configuration" color="red" radius="lg"
          styles={{ root: { backgroundColor: 'color-mix(in srgb, var(--mi-error) 6%, var(--mi-surface))', borderColor: 'color-mix(in srgb, var(--mi-error) 20%, transparent)' } }}>
          <Text size="sm" style={{ color: 'var(--mi-text-secondary)' }}>Could not load system configuration.</Text>
          <Button size="xs" variant="light" color="red" mt={8} leftSection={<IconRefresh size={14} />} onClick={() => refetchConfig()}>Retry</Button>
        </Alert>
      </Box>
    );
  }

  /* Categorize flags */
  const categorizedFlags = Object.entries(localFlags).reduce<Record<string, [string, boolean][]>>((acc, [key, val]) => {
    let found = false;
    for (const [cat, keys] of Object.entries(FLAG_CATEGORIES)) {
      if (keys.includes(key)) { (acc[cat] ??= []).push([key, val]); found = true; break; }
    }
    if (!found) (acc['Other'] ??= []).push([key, val]);
    return acc;
  }, {});

  return (
    <Box style={{ padding: 24, maxWidth: 1200, margin: '0 auto', width: '100%' }}>
      <Stack gap={20}>
        {/* Page header */}
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <Group justify="space-between" align="center">
            <Group gap={12}>
              <ThemeIcon size={40} radius="xl" variant="light" color="blue">
                <IconSettings size={22} stroke={1.8} />
              </ThemeIcon>
              <Box>
                <Text fw={800} style={{ fontSize: 26, color: 'var(--mi-text)', lineHeight: 1.2 }}>
                  Settings
                </Text>
                <Text size="sm" style={{ color: 'var(--mi-text-muted)', marginTop: 2 }}>
                  Configure AI engine, pipeline, models, and system behavior
                </Text>
              </Box>
            </Group>
            <Group gap={8}>
              <Button variant="subtle" size="xs" leftSection={<IconArrowBackUp size={14} />} onClick={handleReset} disabled={!hasChanges}
                style={{ borderRadius: 'var(--mi-radius-full)' }}>
                Reset
              </Button>
              <Button variant="filled" size="sm"
                leftSection={updateConfigMutation.isPending ? <Loader size={14} color="white" /> : <IconDeviceFloppy size={14} />}
                onClick={handleSave} disabled={updateConfigMutation.isPending}
                style={{ borderRadius: 'var(--mi-radius-full)', backgroundColor: 'var(--mi-primary)' }}>
                Save All Changes
              </Button>
            </Group>
          </Group>
        </motion.div>

        {/* Tabs */}
        <Tabs
          value={activeTab}
          onChange={(val) => setActiveTab(val ?? TAB_ID.AI)}
          variant="pills"
          radius="xl"
          styles={{
            root: { overflow: 'visible' },
            list: {
              backgroundColor: 'var(--mi-surface)',
              border: '1px solid var(--mi-border)',
              borderRadius: 'var(--mi-radius-xl)',
              padding: 4,
              gap: 2,
              flexWrap: 'wrap',
            },
            tab: {
              fontWeight: 600,
              fontSize: 13,
              color: 'var(--mi-text-secondary)',
              padding: '8px 16px',
              borderRadius: 'var(--mi-radius-full)',
              transition: 'all 0.15s ease',
            },
          }}
        >
          <Tabs.List>
            <Tabs.Tab value={TAB_ID.AI} leftSection={<IconRobot size={15} />}>AI Engine</Tabs.Tab>
            <Tabs.Tab value={TAB_ID.PIPELINE} leftSection={<IconAdjustments size={15} />}>Pipeline</Tabs.Tab>
            <Tabs.Tab value={TAB_ID.ML} leftSection={<IconBrain size={15} />}>ML &amp; Risk</Tabs.Tab>
            <Tabs.Tab value={TAB_ID.FLAGS} leftSection={<IconToggleLeft size={15} />}>Feature Flags</Tabs.Tab>
            <Tabs.Tab value={TAB_ID.HEDIS} leftSection={<IconHeartRateMonitor size={15} />}>Quality / HEDIS</Tabs.Tab>
            <Tabs.Tab value={TAB_ID.PROMPTS} leftSection={<IconCode size={15} />}>Prompts</Tabs.Tab>
          </Tabs.List>

          {/* ================================================================ */}
          {/* AI ENGINE TAB                                                     */}
          {/* ================================================================ */}
          <Tabs.Panel value={TAB_ID.AI} pt={20}>
            <AnimatePresence mode="wait">
              <motion.div key="ai" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
                <Stack gap={16}>
                  {/* Provider Cards */}
                  <Box>
                    <Text size="sm" fw={700} mb={12} style={{ color: 'var(--mi-text)' }}>
                      LLM Provider
                    </Text>
                    <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing={12}>
                      {PROVIDER_OPTIONS.map((p) => {
                        const Icon = p.icon;
                        const isActive = llmProvider === p.value;
                        return (
                          <Box
                            key={p.value}
                            onClick={() => { setLlmProvider(p.value); markChanged(); }}
                            style={{
                              padding: 16,
                              borderRadius: 'var(--mi-radius-lg)',
                              border: `2px solid ${isActive ? p.color : 'var(--mi-border)'}`,
                              backgroundColor: isActive ? `${p.color}10` : 'var(--mi-surface)',
                              cursor: 'pointer',
                              transition: 'all 0.15s ease',
                              position: 'relative',
                            }}
                          >
                            {isActive && (
                              <Box style={{ position: 'absolute', top: 8, right: 8, width: 20, height: 20, borderRadius: '50%', backgroundColor: p.color, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <IconCheck size={12} color="#fff" stroke={3} />
                              </Box>
                            )}
                            <Icon size={24} color={isActive ? p.color : 'var(--mi-text-muted)'} stroke={1.5} />
                            <Text size="sm" fw={700} mt={8} style={{ color: 'var(--mi-text)' }}>{p.label}</Text>
                            <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>{p.desc}</Text>
                          </Box>
                        );
                      })}
                    </SimpleGrid>
                  </Box>

                  {/* Model & Parameters */}
                  <SimpleGrid cols={{ base: 1, md: 2 }} spacing={12}>
                    <SettingRow label="Model" description="Specific model identifier (e.g. gpt-4o, claude-opus-4-6)" icon={<IconCpu size={16} color="var(--mi-primary)" />}>
                      <TextInput
                        value={llmModel} onChange={(e) => { setLlmModel(e.currentTarget.value); markChanged(); }}
                        size="sm" placeholder="gpt-4o" styles={inputStyles}
                      />
                    </SettingRow>

                    <SettingRow label="Max Tokens" description="Maximum output tokens per LLM request" icon={<IconMaximize size={16} color="var(--mi-primary)" />}>
                      <NumberInput
                        value={maxTokens} onChange={(val) => { setMaxTokens(typeof val === 'number' ? val : 4096); markChanged(); }}
                        min={256} max={32768} step={256} size="sm" styles={inputStyles}
                      />
                    </SettingRow>
                  </SimpleGrid>

                  <SettingRow
                    label="Temperature"
                    description={`Controls randomness in LLM outputs. Lower = more deterministic. Current: ${temperature.toFixed(2)}`}
                    icon={<IconTemperature size={16} color="#F59E0B" />}
                    span
                  >
                    <Box style={{ width: '100%', minWidth: 200 }}>
                      <Slider
                        value={temperature}
                        onChange={(val) => { setTemperature(val); markChanged(); }}
                        min={0} max={2} step={0.05}
                        marks={[{ value: 0, label: '0' }, { value: 0.5, label: '0.5' }, { value: 1, label: '1' }, { value: 1.5, label: '1.5' }, { value: 2, label: '2' }]}
                        styles={{ markLabel: { fontSize: 10, color: 'var(--mi-text-muted)' }, track: { backgroundColor: 'var(--mi-border)' } }}
                        color="orange"
                      />
                    </Box>
                  </SettingRow>

                  {/* Summary */}
                  <Box style={{ padding: 16, borderRadius: 'var(--mi-radius-lg)', backgroundColor: 'color-mix(in srgb, var(--mi-primary) 6%, var(--mi-surface))', border: '1px solid color-mix(in srgb, var(--mi-primary) 15%, transparent)' }}>
                    <Group gap={8}>
                      <IconInfoCircle size={14} color="var(--mi-primary)" />
                      <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                        Active: <Text span fw={700} style={{ color: 'var(--mi-text)' }}>{llmProvider || 'None'}</Text> / <Text span fw={700} style={{ color: 'var(--mi-text)' }}>{llmModel || 'Not set'}</Text> with temperature {temperature.toFixed(2)} and {maxTokens.toLocaleString()} max tokens
                      </Text>
                    </Group>
                  </Box>
                </Stack>
              </motion.div>
            </AnimatePresence>
          </Tabs.Panel>

          {/* ================================================================ */}
          {/* PIPELINE TAB                                                      */}
          {/* ================================================================ */}
          <Tabs.Panel value={TAB_ID.PIPELINE} pt={20}>
            <AnimatePresence mode="wait">
              <motion.div key="pipeline" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
                <Stack gap={16}>
                  <SimpleGrid cols={{ base: 1, md: 2 }} spacing={12}>
                    <SettingRow label="Chunk Size" description="Characters per text chunk for LLM processing" icon={<IconStack2 size={16} color="#3B82F6" />}>
                      <NumberInput
                        value={chunkSize} onChange={(val) => { setChunkSize(typeof val === 'number' ? val : 1000); markChanged(); }}
                        min={200} max={50000} step={500} size="sm" styles={inputStyles}
                      />
                    </SettingRow>

                    <SettingRow label="Chunk Overlap" description="Character overlap between adjacent chunks" icon={<IconArrowsShuffle size={16} color="#8B5CF6" />}>
                      <NumberInput
                        value={chunkOverlap} onChange={(val) => { setChunkOverlap(typeof val === 'number' ? val : 200); markChanged(); }}
                        min={0} max={5000} step={50} size="sm" styles={inputStyles}
                      />
                    </SettingRow>

                    <SettingRow label="Measurement Year" description="HEDIS/RAF measurement year for compliance evaluation" icon={<IconCalendar size={16} color="#10B981" />}>
                      <NumberInput
                        value={measurementYear} onChange={(val) => { setMeasurementYear(typeof val === 'number' ? val : 2024); markChanged(); }}
                        min={2020} max={2030} step={1} size="sm" styles={inputStyles}
                      />
                    </SettingRow>
                  </SimpleGrid>

                  <SettingRow
                    label="OCR Quality Threshold"
                    description={`Pages below this score trigger GPT-4o Vision OCR fallback. Current: ${(qualityThreshold * 100).toFixed(0)}%`}
                    icon={<IconGauge size={16} color="#EC4899" />}
                    span
                  >
                    <Box style={{ width: '100%', minWidth: 200 }}>
                      <Group justify="space-between" mb={4}>
                        <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>Low quality</Text>
                        <Text size="xs" fw={700} style={{ color: 'var(--mi-text)' }}>{(qualityThreshold * 100).toFixed(0)}%</Text>
                        <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>High quality</Text>
                      </Group>
                      <Slider
                        value={qualityThreshold}
                        onChange={(val) => { setQualityThreshold(val); markChanged(); }}
                        min={0} max={1} step={0.05}
                        styles={{ markLabel: { fontSize: 10, color: 'var(--mi-text-muted)' }, track: { backgroundColor: 'var(--mi-border)' } }}
                        color="pink"
                      />
                    </Box>
                  </SettingRow>

                  {/* Visual chunk preview */}
                  <Box style={{ padding: 16, borderRadius: 'var(--mi-radius-lg)', backgroundColor: 'var(--mi-surface)', border: '1px solid var(--mi-border)' }}>
                    <Text size="xs" fw={600} mb={8} style={{ color: 'var(--mi-text)' }}>Chunking Preview</Text>
                    <Group gap={4} style={{ overflow: 'hidden' }}>
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Tooltip key={i} label={`Chunk ${i + 1}: ${chunkSize} chars${i > 0 ? ` (${chunkOverlap} overlap)` : ''}`}>
                          <Box style={{
                            flex: 1, height: 24, borderRadius: 4, position: 'relative', overflow: 'hidden',
                            backgroundColor: `hsl(${210 + i * 30}, 70%, ${55 - i * 4}%)`,
                          }}>
                            {i > 0 && (
                              <Box style={{
                                position: 'absolute', left: 0, top: 0, bottom: 0,
                                width: `${Math.min((chunkOverlap / chunkSize) * 100, 40)}%`,
                                backgroundColor: 'rgba(255,255,255,0.25)',
                              }} />
                            )}
                            <Text size="xs" fw={700} ta="center" style={{ lineHeight: '24px', color: '#fff' }}>
                              {i + 1}
                            </Text>
                          </Box>
                        </Tooltip>
                      ))}
                    </Group>
                    <Text size="xs" mt={6} style={{ color: 'var(--mi-text-muted)' }}>
                      Overlap ratio: {chunkSize > 0 ? ((chunkOverlap / chunkSize) * 100).toFixed(1) : 0}%
                    </Text>
                  </Box>
                </Stack>
              </motion.div>
            </AnimatePresence>
          </Tabs.Panel>

          {/* ================================================================ */}
          {/* ML & RISK TAB                                                     */}
          {/* ================================================================ */}
          <Tabs.Panel value={TAB_ID.ML} pt={20}>
            <AnimatePresence mode="wait">
              <motion.div key="ml" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
                <Stack gap={16}>
                  <SettingRow
                    label="ML Confidence Threshold"
                    description={`BioClinicalBERT predictions below this confidence are discarded. Current: ${(mlConfidence * 100).toFixed(0)}%`}
                    icon={<IconBrain size={16} color="#EC4899" />}
                    span
                  >
                    <Box style={{ width: '100%', minWidth: 200 }}>
                      <Slider
                        value={mlConfidence}
                        onChange={(val) => { setMlConfidence(val); markChanged(); }}
                        min={0} max={1} step={0.05}
                        marks={[{ value: 0, label: '0%' }, { value: 0.3, label: '30%' }, { value: 0.5, label: '50%' }, { value: 0.7, label: '70%' }, { value: 1, label: '100%' }]}
                        styles={{ markLabel: { fontSize: 10, color: 'var(--mi-text-muted)' }, track: { backgroundColor: 'var(--mi-border)' } }}
                        color="pink"
                      />
                    </Box>
                  </SettingRow>

                  <SettingRow
                    label="TF-IDF Similarity Threshold"
                    description={`Minimum cosine similarity for ICD-10 code retrieval. Current: ${(tfidfSimilarity * 100).toFixed(0)}%`}
                    icon={<IconTargetArrow size={16} color="#8B5CF6" />}
                    span
                  >
                    <Box style={{ width: '100%', minWidth: 200 }}>
                      <Slider
                        value={tfidfSimilarity}
                        onChange={(val) => { setTfidfSimilarity(val); markChanged(); }}
                        min={0} max={1} step={0.05}
                        marks={[{ value: 0, label: '0%' }, { value: 0.25, label: '25%' }, { value: 0.5, label: '50%' }, { value: 0.75, label: '75%' }, { value: 1, label: '100%' }]}
                        styles={{ markLabel: { fontSize: 10, color: 'var(--mi-text-muted)' }, track: { backgroundColor: 'var(--mi-border)' } }}
                        color="violet"
                      />
                    </Box>
                  </SettingRow>

                  {/* Threshold impact indicators */}
                  <SimpleGrid cols={{ base: 1, md: 2 }} spacing={12}>
                    <Box style={{ padding: 16, borderRadius: 'var(--mi-radius-lg)', backgroundColor: 'var(--mi-surface)', border: '1px solid var(--mi-border)' }}>
                      <Group gap={8} mb={8}>
                        <IconBrain size={14} color="#EC4899" />
                        <Text size="xs" fw={700} style={{ color: 'var(--mi-text)' }}>ML Confidence Impact</Text>
                      </Group>
                      <Stack gap={6}>
                        <Group justify="space-between">
                          <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>Precision</Text>
                          <Text size="xs" fw={600} style={{ color: mlConfidence >= 0.7 ? '#10B981' : mlConfidence >= 0.4 ? '#F59E0B' : '#EF4444' }}>
                            {mlConfidence >= 0.7 ? 'High' : mlConfidence >= 0.4 ? 'Medium' : 'Low'}
                          </Text>
                        </Group>
                        <Progress value={mlConfidence * 100} size="xs" color="pink" radius="xl" />
                        <Group justify="space-between">
                          <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>Recall</Text>
                          <Text size="xs" fw={600} style={{ color: mlConfidence <= 0.3 ? '#10B981' : mlConfidence <= 0.6 ? '#F59E0B' : '#EF4444' }}>
                            {mlConfidence <= 0.3 ? 'High' : mlConfidence <= 0.6 ? 'Medium' : 'Low'}
                          </Text>
                        </Group>
                        <Progress value={(1 - mlConfidence) * 100} size="xs" color="teal" radius="xl" />
                      </Stack>
                    </Box>

                    <Box style={{ padding: 16, borderRadius: 'var(--mi-radius-lg)', backgroundColor: 'var(--mi-surface)', border: '1px solid var(--mi-border)' }}>
                      <Group gap={8} mb={8}>
                        <IconTargetArrow size={14} color="#8B5CF6" />
                        <Text size="xs" fw={700} style={{ color: 'var(--mi-text)' }}>TF-IDF Retrieval Impact</Text>
                      </Group>
                      <Stack gap={6}>
                        <Group justify="space-between">
                          <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>Code Specificity</Text>
                          <Text size="xs" fw={600} style={{ color: tfidfSimilarity >= 0.5 ? '#10B981' : '#F59E0B' }}>
                            {tfidfSimilarity >= 0.5 ? 'High' : 'Broad'}
                          </Text>
                        </Group>
                        <Progress value={tfidfSimilarity * 100} size="xs" color="violet" radius="xl" />
                        <Group justify="space-between">
                          <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>Coverage</Text>
                          <Text size="xs" fw={600} style={{ color: tfidfSimilarity <= 0.3 ? '#10B981' : tfidfSimilarity <= 0.5 ? '#F59E0B' : '#EF4444' }}>
                            {tfidfSimilarity <= 0.3 ? 'Broad' : tfidfSimilarity <= 0.5 ? 'Moderate' : 'Narrow'}
                          </Text>
                        </Group>
                        <Progress value={(1 - tfidfSimilarity) * 100} size="xs" color="teal" radius="xl" />
                      </Stack>
                    </Box>
                  </SimpleGrid>
                </Stack>
              </motion.div>
            </AnimatePresence>
          </Tabs.Panel>

          {/* ================================================================ */}
          {/* FEATURE FLAGS TAB                                                 */}
          {/* ================================================================ */}
          <Tabs.Panel value={TAB_ID.FLAGS} pt={20}>
            <AnimatePresence mode="wait">
              <motion.div key="flags" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
                <Stack gap={20}>
                  {flagsLoading ? (
                    <Stack gap={8}>{[1, 2, 3, 4].map((i) => <Skeleton key={i} height={60} radius="md" />)}</Stack>
                  ) : Object.keys(localFlags).length === 0 ? (
                    <Box py={40} style={{ textAlign: 'center' }}>
                      <Text size="sm" c="dimmed">No feature flags configured</Text>
                    </Box>
                  ) : (
                    <>
                      {Object.entries(categorizedFlags).map(([category, flags]) => (
                        <Box key={category}>
                          <Group gap={8} mb={12}>
                            <ThemeIcon size={22} radius="sm" variant="light"
                              color={category === 'Risk Adjustment' ? 'indigo' : category === 'Quality' ? 'teal' : 'blue'}>
                              {category === 'Risk Adjustment' ? <IconShieldCheck size={13} /> : category === 'Quality' ? <IconHeartRateMonitor size={13} /> : <IconAdjustments size={13} />}
                            </ThemeIcon>
                            <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>{category}</Text>
                            <Badge size="xs" variant="light" color="gray">
                              {flags.filter(([, v]) => v).length}/{flags.length} enabled
                            </Badge>
                          </Group>
                          <Stack gap={6}>
                            {flags.map(([key, enabled]) => {
                              const displayName = key.replace(/^enable_/, '').replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
                              return (
                                <Box key={key} style={{
                                  padding: '12px 16px', borderRadius: 'var(--mi-radius-lg)',
                                  backgroundColor: enabled ? 'color-mix(in srgb, var(--mi-success) 5%, var(--mi-surface))' : 'var(--mi-surface)',
                                  border: `1px solid ${enabled ? 'color-mix(in srgb, var(--mi-success) 20%, transparent)' : 'var(--mi-border)'}`,
                                  transition: 'all 0.15s ease',
                                }}>
                                  <Group justify="space-between" align="center" wrap="nowrap">
                                    <Box style={{ minWidth: 0 }}>
                                      <Text size="sm" fw={600} style={{ color: 'var(--mi-text)' }}>{displayName}</Text>
                                      <Text size="xs" style={{ color: 'var(--mi-text-muted)', lineHeight: 1.4 }}>
                                        {FLAG_DESCRIPTIONS[key] || key}
                                      </Text>
                                    </Box>
                                    <Switch checked={enabled} onChange={() => toggleFlag(key)} size="md" color="green" />
                                  </Group>
                                </Box>
                              );
                            })}
                          </Stack>
                        </Box>
                      ))}

                      <Button variant="filled" size="sm" color="green"
                        leftSection={updateFlagsMutation.isPending ? <Loader size={14} color="white" /> : <IconDeviceFloppy size={14} />}
                        onClick={handleSaveFlags} loading={updateFlagsMutation.isPending}
                        style={{ borderRadius: 'var(--mi-radius-full)', alignSelf: 'flex-end' }}>
                        Save Feature Flags
                      </Button>
                    </>
                  )}
                </Stack>
              </motion.div>
            </AnimatePresence>
          </Tabs.Panel>

          {/* ================================================================ */}
          {/* QUALITY / HEDIS TAB                                               */}
          {/* ================================================================ */}
          <Tabs.Panel value={TAB_ID.HEDIS} pt={20}>
            <AnimatePresence mode="wait">
              <motion.div key="hedis" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
                <Stack gap={16}>
                  {/* Summary bar */}
                  <Group justify="space-between" align="center" wrap="wrap">
                    <Group gap={12}>
                      <Box style={{ padding: '8px 16px', borderRadius: 'var(--mi-radius-lg)', backgroundColor: 'var(--mi-surface)', border: '1px solid var(--mi-border)' }}>
                        <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>Total</Text>
                        <Text size="lg" fw={800} style={{ color: 'var(--mi-text)' }}>{hedisCatalog?.total_measures ?? 0}</Text>
                      </Box>
                      <Box style={{ padding: '8px 16px', borderRadius: 'var(--mi-radius-lg)', backgroundColor: 'color-mix(in srgb, var(--mi-success) 8%, var(--mi-surface))', border: '1px solid color-mix(in srgb, var(--mi-success) 20%, transparent)' }}>
                        <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>Active</Text>
                        <Text size="lg" fw={800} style={{ color: '#10B981' }}>{activeMeasureIds.length}</Text>
                      </Box>
                      <Box style={{ padding: '8px 16px', borderRadius: 'var(--mi-radius-lg)', backgroundColor: 'var(--mi-surface)', border: '1px solid var(--mi-border)' }}>
                        <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>Inactive</Text>
                        <Text size="lg" fw={800} style={{ color: 'var(--mi-text-muted)' }}>{Math.max((hedisCatalog?.total_measures ?? 0) - activeMeasureIds.length, 0)}</Text>
                      </Box>
                    </Group>
                    <Button size="sm" color="teal"
                      leftSection={updateHedisProfileMutation.isPending ? <Loader size={14} color="white" /> : <IconDeviceFloppy size={14} />}
                      onClick={saveHedisProfile} loading={updateHedisProfileMutation.isPending}
                      style={{ borderRadius: 'var(--mi-radius-full)' }}>
                      Save Measure Profile
                    </Button>
                  </Group>

                  {/* Search */}
                  <TextInput
                    placeholder="Search measures by code, name, or domain..."
                    leftSection={<IconSearch size={15} color="var(--mi-text-muted)" />}
                    value={measureSearch} onChange={(e) => setMeasureSearch(e.currentTarget.value)}
                    size="sm" styles={inputStyles}
                  />

                  {/* Measure list */}
                  <ScrollArea.Autosize mah={500} type="auto" style={{ border: '1px solid var(--mi-border)', borderRadius: 'var(--mi-radius-lg)' }}>
                    <Stack gap={0} style={{ padding: 8 }}>
                      {hedisCatalogLoading && [1, 2, 3].map((i) => <Skeleton key={i} height={72} radius="md" mb={6} />)}
                      {!hedisCatalogLoading && filteredMeasures.map((m) => {
                        const active = activeMeasureIds.includes(m.measure_id);
                        return (
                          <Box key={m.measure_id} style={{
                            padding: '12px 16px', borderRadius: 'var(--mi-radius-md)', marginBottom: 4,
                            backgroundColor: active ? 'color-mix(in srgb, var(--mi-success) 4%, var(--mi-surface))' : 'var(--mi-surface)',
                            border: `1px solid ${active ? 'color-mix(in srgb, var(--mi-success) 15%, transparent)' : 'var(--mi-border)'}`,
                            transition: 'all 0.15s ease',
                          }}>
                            <Group justify="space-between" align="flex-start" wrap="nowrap">
                              <Box style={{ minWidth: 0, flex: 1 }}>
                                <Group gap={8} mb={4}>
                                  <Badge size="xs" variant="filled" color={active ? 'teal' : 'gray'}>{m.measure_id}</Badge>
                                  <Badge size="xs" variant="light" color="blue">{m.domain || 'general'}</Badge>
                                  <Text size="sm" fw={700} style={{ color: 'var(--mi-text)' }}>{m.name}</Text>
                                </Group>
                                {m.description && (
                                  <Text size="xs" style={{ color: 'var(--mi-text-secondary)', lineHeight: 1.4 }}>{m.description}</Text>
                                )}
                                {(m.rules_summary ?? []).length > 0 && (
                                  <Group gap={4} mt={6}>
                                    {m.rules_summary.slice(0, 3).map((r) => (
                                      <Badge key={`${m.measure_id}-${r}`} size="xs" variant="light" color="grape" styles={{ root: { textTransform: 'none' } }}>{r}</Badge>
                                    ))}
                                  </Group>
                                )}
                              </Box>
                              <Switch checked={active} onChange={() => toggleHedisMeasure(m.measure_id)} color="teal" size="md" />
                            </Group>
                          </Box>
                        );
                      })}
                    </Stack>
                  </ScrollArea.Autosize>

                  {/* Measure Rule Editor */}
                  <Divider label="Measure Rule Editor" labelPosition="left" styles={{ label: { color: 'var(--mi-text-muted)', fontSize: 12, fontWeight: 600 } }} />
                  <SimpleGrid cols={{ base: 1, md: 2 }} spacing={12}>
                    <Select
                      label="Select Measure" placeholder="Choose measure..."
                      data={(hedisCatalog?.measures ?? []).map((m) => ({ value: m.measure_id, label: `${m.measure_id} - ${m.name}` }))}
                      value={selectedMeasureId} onChange={setSelectedMeasureId}
                      searchable size="sm" styles={inputStyles}
                    />
                    <Group gap={8} align="flex-end">
                      <Button size="sm" color="teal" onClick={saveMeasureDefinition} loading={saveMeasureDefMutation.isPending}
                        leftSection={<IconDeviceFloppy size={14} />}>
                        Save Rule
                      </Button>
                      <Button size="sm" color="red" variant="light" disabled={!selectedMeasureId}
                        loading={deleteMeasureDefMutation.isPending} leftSection={<IconTrash size={14} />}
                        onClick={() => selectedMeasureId && deleteMeasureDefMutation.mutate(selectedMeasureId)}>
                        Delete
                      </Button>
                    </Group>
                  </SimpleGrid>
                  <Textarea minRows={8} autosize value={measureDefinitionText}
                    onChange={(e) => setMeasureDefinitionText(e.currentTarget.value)}
                    styles={{ ...inputStyles, input: { ...inputStyles.input, fontFamily: '"JetBrains Mono", "Fira Code", monospace', fontSize: 12, lineHeight: 1.6 } }}
                  />
                </Stack>
              </motion.div>
            </AnimatePresence>
          </Tabs.Panel>

          {/* ================================================================ */}
          {/* PROMPTS TAB                                                       */}
          {/* ================================================================ */}
          <Tabs.Panel value={TAB_ID.PROMPTS} pt={20}>
            <AnimatePresence mode="wait">
              <motion.div key="prompts" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
                {promptsLoading ? (
                  <Stack gap={8}>
                    <Skeleton height={34} radius="md" />
                    <Skeleton height={280} radius="md" />
                  </Stack>
                ) : promptOptions.length === 0 ? (
                  <Box py={40} style={{ textAlign: 'center' }}>
                    <IconCode size={36} stroke={1.2} color="var(--mi-text-muted)" style={{ opacity: 0.5 }} />
                    <Text size="sm" c="dimmed" mt={12}>No prompt templates available</Text>
                  </Box>
                ) : (
                  <Stack gap={16}>
                    {/* Prompt selector as pill buttons */}
                    <Box>
                      <Text size="sm" fw={700} mb={10} style={{ color: 'var(--mi-text)' }}>Pipeline Prompts</Text>
                      <Group gap={6} style={{ flexWrap: 'wrap' }}>
                        {promptOptions.map((p) => (
                          <Button
                            key={p.value}
                            size="xs"
                            variant={selectedPrompt === p.value ? 'filled' : 'light'}
                            color={selectedPrompt === p.value ? 'orange' : 'gray'}
                            onClick={() => handlePromptSelect(p.value)}
                            style={{ borderRadius: 'var(--mi-radius-full)', textTransform: 'none' }}
                          >
                            {p.label}
                          </Button>
                        ))}
                      </Group>
                    </Box>

                    {/* Editor */}
                    <Box style={{ position: 'relative' }}>
                      <Group justify="space-between" mb={8}>
                        <Group gap={6}>
                          <Badge size="sm" variant="light" color="orange">{selectedPrompt}</Badge>
                          <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>
                            {promptText.length.toLocaleString()} characters
                          </Text>
                        </Group>
                      </Group>
                      <Textarea
                        value={promptText}
                        onChange={(e) => setPromptText(e.currentTarget.value)}
                        minRows={16}
                        maxRows={30}
                        autosize
                        styles={{
                          ...inputStyles,
                          input: {
                            ...inputStyles.input,
                            fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                            fontSize: 12,
                            lineHeight: 1.7,
                            whiteSpace: 'pre-wrap' as const,
                            padding: 16,
                          },
                        }}
                      />
                    </Box>

                    <Box style={{ padding: 12, borderRadius: 'var(--mi-radius-md)', backgroundColor: 'color-mix(in srgb, var(--mi-warning) 6%, var(--mi-surface))', border: '1px solid color-mix(in srgb, var(--mi-warning) 15%, transparent)' }}>
                      <Group gap={6}>
                        <IconInfoCircle size={13} color="#F59E0B" />
                        <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                          Changes to prompt templates are saved with the main configuration. Click "Save All Changes" above.
                        </Text>
                      </Group>
                    </Box>
                  </Stack>
                )}
              </motion.div>
            </AnimatePresence>
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Box>
  );
}
