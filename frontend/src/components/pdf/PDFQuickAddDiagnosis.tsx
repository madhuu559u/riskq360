import { useState, useCallback, useRef, useEffect } from 'react';
import {
  TextInput,
  Textarea,
  Text,
  Badge,
  Group,
  Stack,
  Box,
  Button,
  Loader,
  Switch,
  ScrollArea,
  Select,
  CloseButton,
} from '@mantine/core';
import {
  IconSearch,
  IconPlus,
  IconStethoscope,
  IconCalendar,
  IconNote,
  IconArrowRight,
} from '@tabler/icons-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCodingSuggestions, useAddDiagnosis } from '../../hooks/useChart';
import { useChartStore } from '../../stores/chartStore';
import type { CodingHelperResult } from '../../api/review';

interface PDFQuickAddDiagnosisProps {
  opened: boolean;
  onClose: () => void;
  selectedText: string;
  pageNumber: number;
}

export function PDFQuickAddDiagnosis({
  opened,
  onClose,
  selectedText,
  pageNumber,
}: PDFQuickAddDiagnosisProps) {
  const activeChartId = useChartStore((s) => s.activeChartId);
  const addDiagnosis = useAddDiagnosis();

  const [query, setQuery] = useState('');
  const [paymentOnly, setPaymentOnly] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const [selectedCode, setSelectedCode] = useState<CodingHelperResult | null>(null);
  const [dateOfService, setDateOfService] = useState('');
  const [notes, setNotes] = useState('');
  const [status, setStatus] = useState<string>('active');

  const { data, isLoading, isFetching } = useCodingSuggestions(query, 12, paymentOnly);
  const results = data?.results ?? [];

  /* Draggable panel state */
  const panelRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 80 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef<{ mouseX: number; mouseY: number; startX: number; startY: number } | null>(null);

  useEffect(() => {
    if (opened && selectedText) {
      const words = selectedText.trim().split(/\s+/).slice(0, 6).join(' ');
      setQuery(words);
      setSelectedCode(null);
      setDateOfService('');
      setNotes('');
      setStatus('active');
      setPosition({ x: Math.max(20, window.innerWidth - 460), y: 80 });
      setTimeout(() => searchRef.current?.focus(), 150);
    }
  }, [opened, selectedText]);

  const handleSubmit = useCallback(() => {
    if (!selectedCode || !activeChartId) return;
    addDiagnosis.mutate(
      {
        chart_id: Number(activeChartId),
        icd10_code: selectedCode.icd10_code,
        description: `[Coder-added] ${selectedCode.description}`,
        reviewer: 'RiskQ360',
        notes: notes.trim() || null,
        date_of_service: dateOfService.trim() || null,
        page_number: pageNumber,
        exact_quote: selectedText.trim().slice(0, 500) || null,
        hcc_code: selectedCode.hcc_code || null,
        status,
      },
      { onSuccess: () => onClose() },
    );
  }, [selectedCode, activeChartId, addDiagnosis, notes, dateOfService, pageNumber, selectedText, status, onClose]);

  const handleClose = useCallback(() => {
    setQuery('');
    setSelectedCode(null);
    setDateOfService('');
    setNotes('');
    onClose();
  }, [onClose]);

  /* Drag handlers for the floating panel */
  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const rect = panelRef.current?.getBoundingClientRect();
    if (!rect) return;
    dragStartRef.current = { mouseX: e.clientX, mouseY: e.clientY, startX: rect.left, startY: rect.top };
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;
    const handleMouseMove = (e: MouseEvent) => {
      if (!dragStartRef.current) return;
      setPosition({
        x: dragStartRef.current.startX + (e.clientX - dragStartRef.current.mouseX),
        y: dragStartRef.current.startY + (e.clientY - dragStartRef.current.mouseY),
      });
    };
    const handleMouseUp = () => { setIsDragging(false); dragStartRef.current = null; };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  /* Click-outside to close */
  useEffect(() => {
    if (!opened) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        if ((e.target as HTMLElement).closest('[data-add-dx-btn]')) return;
        handleClose();
      }
    };
    const timer = setTimeout(() => document.addEventListener('mousedown', handler), 200);
    return () => { clearTimeout(timer); document.removeEventListener('mousedown', handler); };
  }, [opened, handleClose]);

  return (
    <AnimatePresence>
      {opened && (
          <motion.div
            ref={panelRef}
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.97 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
            style={{
              position: 'fixed',
              top: position.y,
              left: position.x,
              zIndex: 900,
              width: 420,
              maxHeight: '80vh',
              overflow: 'hidden',
              borderRadius: 14,
              border: '1px solid var(--mi-border)',
              backgroundColor: 'var(--mi-surface)',
              boxShadow: '0 20px 60px rgba(0,0,0,0.25), 0 0 0 1px rgba(255,255,255,0.04) inset',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Header */}
            <Group
              justify="space-between"
              align="center"
              onMouseDown={handleDragStart}
              style={{
                padding: '10px 14px',
                borderBottom: '1px solid var(--mi-border)',
                flexShrink: 0,
                cursor: isDragging ? 'grabbing' : 'grab',
                userSelect: 'none',
              }}
            >
              <Group gap={8}>
                <Box
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: 7,
                    background: 'linear-gradient(135deg, var(--mi-primary), var(--mi-accent))',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <IconStethoscope size={13} color="#fff" stroke={2} />
                </Box>
                <Box>
                  <Text fw={700} size="xs" style={{ lineHeight: 1.2, color: 'var(--mi-text)' }}>Add Diagnosis</Text>
                  <Text size="xs" c="dimmed" style={{ lineHeight: 1.2, fontSize: 10 }}>
                    Page {pageNumber}
                  </Text>
                </Box>
              </Group>
              <CloseButton size="sm" onClick={handleClose} />
            </Group>

            {/* Scrollable body */}
            <Box style={{ flex: 1, overflow: 'auto', padding: '10px 14px 14px' }}>
              {/* Selected text preview — compact */}
              <Box
                style={{
                  padding: '6px 10px',
                  borderRadius: 8,
                  backgroundColor: 'color-mix(in srgb, var(--mi-primary) 5%, var(--mi-background))',
                  border: '1px solid color-mix(in srgb, var(--mi-primary) 12%, transparent)',
                  marginBottom: 10,
                }}
              >
                <Text
                  size="xs"
                  style={{
                    color: 'var(--mi-text-secondary)',
                    fontStyle: 'italic',
                    fontSize: 10,
                    lineHeight: 1.5,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  &ldquo;{selectedText.slice(0, 200)}&rdquo;
                </Text>
              </Box>

              {/* Search bar */}
              <Group gap={6} mb={8} align="center">
                <TextInput
                  ref={searchRef}
                  placeholder="Search ICD-10..."
                  leftSection={<IconSearch size={13} />}
                  rightSection={isFetching ? <Loader size={12} /> : null}
                  value={query}
                  onChange={(e) => {
                    setQuery(e.currentTarget.value);
                    if (selectedCode) setSelectedCode(null);
                  }}
                  size="xs"
                  style={{ flex: 1 }}
                  styles={{
                    input: {
                      backgroundColor: 'var(--mi-background)',
                      borderColor: 'var(--mi-border)',
                      color: 'var(--mi-text)',
                      borderRadius: 8,
                      height: 30,
                      fontSize: 11,
                    },
                  }}
                />
                <Switch
                  label="HCC"
                  size="xs"
                  checked={paymentOnly}
                  onChange={(e) => setPaymentOnly(e.currentTarget.checked)}
                  styles={{ label: { fontSize: 9, color: 'var(--mi-text-muted)', fontWeight: 600 } }}
                />
              </Group>

              {/* Selected code chip */}
              {selectedCode && (
                <Box
                  style={{
                    padding: '8px 10px',
                    borderRadius: 8,
                    border: '2px solid var(--mi-primary)',
                    backgroundColor: 'color-mix(in srgb, var(--mi-primary) 6%, var(--mi-surface))',
                    marginBottom: 10,
                  }}
                >
                  <Group justify="space-between" align="center" wrap="nowrap">
                    <Group gap={8} style={{ minWidth: 0 }}>
                      <Badge
                        size="sm"
                        variant="filled"
                        color="violet"
                        radius="md"
                        styles={{
                          root: {
                            fontFamily: '"JetBrains Mono", monospace',
                            fontWeight: 700,
                            textTransform: 'none',
                            flexShrink: 0,
                            fontSize: 10,
                          },
                        }}
                      >
                        {selectedCode.icd10_code}
                      </Badge>
                      <Box style={{ minWidth: 0 }}>
                        <Text size="xs" fw={600} lineClamp={1} style={{ color: 'var(--mi-text)', fontSize: 11 }}>
                          {selectedCode.description}
                        </Text>
                        {selectedCode.hcc_code && (
                          <Group gap={4} mt={1}>
                            <IconArrowRight size={9} color="var(--mi-text-muted)" />
                            <Badge
                              size="xs"
                              variant="light"
                              color={selectedCode.is_payment_hcc ? 'green' : 'gray'}
                              styles={{ root: { textTransform: 'none', fontFamily: '"JetBrains Mono", monospace', fontSize: 8 } }}
                            >
                              {selectedCode.hcc_code}
                            </Badge>
                            <Text size="xs" c="dimmed" style={{ fontSize: 9 }}>{selectedCode.hcc_label}</Text>
                          </Group>
                        )}
                      </Box>
                    </Group>
                    <Button
                      size="compact-xs"
                      variant="subtle"
                      color="gray"
                      onClick={() => setSelectedCode(null)}
                      styles={{ root: { fontSize: 9, fontWeight: 500 } }}
                    >
                      Change
                    </Button>
                  </Group>
                </Box>
              )}

              {/* Code search results */}
              {!selectedCode && (
                <>
                  {query.trim().length < 2 && (
                    <Text size="xs" c="dimmed" ta="center" py={10} style={{ fontSize: 10 }}>
                      Type 2+ characters to search
                    </Text>
                  )}
                  {query.trim().length >= 2 && isLoading && (
                    <Box ta="center" py={10}><Loader size="xs" /></Box>
                  )}
                  {query.trim().length >= 2 && !isLoading && results.length === 0 && (
                    <Text size="xs" c="dimmed" ta="center" py={10} style={{ fontSize: 10 }}>
                      No codes found
                    </Text>
                  )}
                  {results.length > 0 && (
                    <>
                      <Text size="xs" c="dimmed" mb={4} style={{ fontSize: 9 }}>{results.length} results</Text>
                      <ScrollArea.Autosize mah={180}>
                        <Stack gap={3}>
                          {results.map((r) => (
                            <Box
                              key={`${r.icd10_code}-${r.hcc_code}`}
                              onClick={() => setSelectedCode(r)}
                              style={{
                                padding: '5px 8px',
                                borderRadius: 6,
                                border: '1px solid var(--mi-border)',
                                backgroundColor: 'var(--mi-background)',
                                cursor: 'pointer',
                                transition: 'all 0.1s ease',
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--mi-primary) 35%, transparent)';
                                e.currentTarget.style.backgroundColor = 'color-mix(in srgb, var(--mi-primary) 5%, var(--mi-surface))';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = 'var(--mi-border)';
                                e.currentTarget.style.backgroundColor = 'var(--mi-background)';
                              }}
                            >
                              <Group justify="space-between" wrap="nowrap" gap={6}>
                                <Group gap={6} style={{ minWidth: 0, flex: 1 }}>
                                  <Badge
                                    size="xs"
                                    variant="filled"
                                    color="violet"
                                    radius="md"
                                    styles={{
                                      root: {
                                        fontFamily: '"JetBrains Mono", monospace',
                                        fontWeight: 700,
                                        fontSize: 9,
                                        textTransform: 'none',
                                        flexShrink: 0,
                                      },
                                    }}
                                  >
                                    {r.icd10_code}
                                  </Badge>
                                  <Text size="xs" fw={500} lineClamp={1} style={{ color: 'var(--mi-text)', minWidth: 0, fontSize: 10 }}>
                                    {r.description}
                                  </Text>
                                </Group>
                                <Group gap={3} style={{ flexShrink: 0 }}>
                                  {r.hcc_code && (
                                    <Badge
                                      size="xs"
                                      variant="light"
                                      color={r.is_payment_hcc ? 'green' : 'gray'}
                                      styles={{ root: { textTransform: 'none', fontSize: 7, fontFamily: '"JetBrains Mono", monospace' } }}
                                    >
                                      {r.hcc_code}
                                    </Badge>
                                  )}
                                  <IconPlus size={10} stroke={2.5} color="var(--mi-primary)" />
                                </Group>
                              </Group>
                            </Box>
                          ))}
                        </Stack>
                      </ScrollArea.Autosize>
                    </>
                  )}
                </>
              )}

              {/* Detail form (step 2) */}
              {selectedCode && (
                <>
                  <Group gap={8} mb={8}>
                    <TextInput
                      label="Date of Service"
                      placeholder="YYYY-MM-DD"
                      leftSection={<IconCalendar size={11} />}
                      value={dateOfService}
                      onChange={(e) => setDateOfService(e.currentTarget.value)}
                      size="xs"
                      style={{ flex: 1 }}
                      styles={{
                        input: { backgroundColor: 'var(--mi-background)', borderColor: 'var(--mi-border)', color: 'var(--mi-text)', borderRadius: 6, height: 28, fontSize: 10 },
                        label: { fontSize: 10, fontWeight: 600, marginBottom: 2 },
                      }}
                    />
                    <Select
                      label="Status"
                      data={[
                        { value: 'active', label: 'Active' },
                        { value: 'historical', label: 'Historical' },
                        { value: 'resolved', label: 'Resolved' },
                        { value: 'uncertain', label: 'Uncertain' },
                      ]}
                      value={status}
                      onChange={(v) => { if (v) setStatus(v); }}
                      size="xs"
                      style={{ width: 110 }}
                      styles={{
                        input: { backgroundColor: 'var(--mi-background)', borderColor: 'var(--mi-border)', color: 'var(--mi-text)', borderRadius: 6, height: 28, fontSize: 10 },
                        label: { fontSize: 10, fontWeight: 600, marginBottom: 2 },
                      }}
                    />
                  </Group>
                  <Textarea
                    label="Notes"
                    placeholder="Optional..."
                    leftSection={<IconNote size={11} />}
                    value={notes}
                    onChange={(e) => setNotes(e.currentTarget.value)}
                    minRows={1}
                    maxRows={2}
                    autosize
                    size="xs"
                    mb={10}
                    styles={{
                      input: { backgroundColor: 'var(--mi-background)', borderColor: 'var(--mi-border)', color: 'var(--mi-text)', borderRadius: 6, fontSize: 10 },
                      label: { fontSize: 10, fontWeight: 600, marginBottom: 2 },
                    }}
                  />
                  <Group justify="flex-end" gap={8}>
                    <Button variant="subtle" color="gray" size="compact-xs" onClick={handleClose} styles={{ root: { fontSize: 10 } }}>
                      Cancel
                    </Button>
                    <Button
                      size="compact-sm"
                      leftSection={<IconPlus size={12} />}
                      loading={addDiagnosis.isPending}
                      onClick={handleSubmit}
                      style={{
                        background: 'linear-gradient(135deg, var(--mi-primary), var(--mi-accent))',
                        border: 'none',
                        fontWeight: 700,
                        fontSize: 11,
                      }}
                    >
                      Add Diagnosis
                    </Button>
                  </Group>
                </>
              )}
            </Box>
          </motion.div>
      )}
    </AnimatePresence>
  );
}
