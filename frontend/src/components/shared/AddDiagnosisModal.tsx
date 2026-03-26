import { useState, useCallback } from 'react';
import {
  Modal,
  TextInput,
  Textarea,
  Button,
  Group,
  Stack,
  Text,
  Badge,
  Select,
} from '@mantine/core';
import { IconPlus, IconStethoscope, IconSearch } from '@tabler/icons-react';
import type { CodingHelperResult } from '../../api/review';

interface AddDiagnosisModalProps {
  opened: boolean;
  onClose: () => void;
  onSubmit: (data: {
    icd10_code: string;
    description: string;
    date_of_service?: string;
    notes?: string;
    page_number?: number;
    exact_quote?: string;
    hcc_code?: string;
    status: string;
  }) => void;
  onOpenCodingHelper: () => void;
  prefilledCode?: CodingHelperResult | null;
  isPending?: boolean;
}

export function AddDiagnosisModal({
  opened,
  onClose,
  onSubmit,
  onOpenCodingHelper,
  prefilledCode,
  isPending,
}: AddDiagnosisModalProps) {
  const [icdCode, setIcdCode] = useState('');
  const [description, setDescription] = useState('');
  const [dateOfService, setDateOfService] = useState('');
  const [notes, setNotes] = useState('');
  const [pageNumber, setPageNumber] = useState('');
  const [exactQuote, setExactQuote] = useState('');
  const [status, setStatus] = useState<string>('active');

  // Apply prefilled code from coding helper
  if (prefilledCode && icdCode !== prefilledCode.icd10_code) {
    setIcdCode(prefilledCode.icd10_code);
    setDescription(prefilledCode.description);
  }

  const handleSubmit = useCallback(() => {
    if (!icdCode.trim() || !description.trim()) return;
    onSubmit({
      icd10_code: icdCode.trim(),
      description: description.trim(),
      date_of_service: dateOfService.trim() || undefined,
      notes: notes.trim() || undefined,
      page_number: pageNumber ? parseInt(pageNumber, 10) : undefined,
      exact_quote: exactQuote.trim() || undefined,
      hcc_code: prefilledCode?.hcc_code || undefined,
      status,
    });
    // Reset
    setIcdCode('');
    setDescription('');
    setDateOfService('');
    setNotes('');
    setPageNumber('');
    setExactQuote('');
    setStatus('active');
  }, [icdCode, description, dateOfService, notes, pageNumber, exactQuote, status, prefilledCode, onSubmit]);

  const handleClose = () => {
    setIcdCode('');
    setDescription('');
    setDateOfService('');
    setNotes('');
    setPageNumber('');
    setExactQuote('');
    setStatus('active');
    onClose();
  };

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title={
        <Group gap={8}>
          <IconPlus size={18} color="var(--mi-primary)" />
          <Text fw={700} size="sm">Add Diagnosis Code</Text>
        </Group>
      }
      size="md"
      centered
      styles={{
        header: { borderBottom: '1px solid var(--mi-border)' },
        body: { padding: 16 },
      }}
    >
      <Stack gap={12}>
        <Group gap={8} align="flex-end">
          <TextInput
            label="ICD-10 Code"
            placeholder="E11.65"
            value={icdCode}
            onChange={(e) => setIcdCode(e.currentTarget.value)}
            required
            size="sm"
            style={{ flex: 1 }}
            styles={{
              input: {
                fontFamily: '"JetBrains Mono", monospace',
                backgroundColor: 'var(--mi-surface)',
                borderColor: 'var(--mi-border)',
                color: 'var(--mi-text)',
              },
            }}
          />
          <Button
            variant="light"
            color="violet"
            size="sm"
            leftSection={<IconSearch size={14} />}
            onClick={onOpenCodingHelper}
          >
            Search Codes
          </Button>
        </Group>

        {prefilledCode && (
          <Group gap={6}>
            <Badge size="sm" variant="light" color="violet" styles={{ root: { textTransform: 'none' } }}>
              {prefilledCode.icd10_code}
            </Badge>
            {prefilledCode.hcc_code && (
              <Badge size="sm" variant="light" color="green" styles={{ root: { textTransform: 'none' } }}>
                {prefilledCode.hcc_code}
              </Badge>
            )}
            <Text size="xs" c="dimmed">via Coding Helper</Text>
          </Group>
        )}

        <TextInput
          label="Description"
          placeholder="Type 2 diabetes mellitus with hyperglycemia"
          value={description}
          onChange={(e) => setDescription(e.currentTarget.value)}
          required
          size="sm"
          styles={{
            input: { backgroundColor: 'var(--mi-surface)', borderColor: 'var(--mi-border)', color: 'var(--mi-text)' },
          }}
        />

        <Group gap={8}>
          <TextInput
            label="Date of Service"
            placeholder="YYYY-MM-DD"
            value={dateOfService}
            onChange={(e) => setDateOfService(e.currentTarget.value)}
            size="sm"
            style={{ flex: 1 }}
            styles={{
              input: { backgroundColor: 'var(--mi-surface)', borderColor: 'var(--mi-border)', color: 'var(--mi-text)' },
            }}
          />
          <TextInput
            label="Page Number"
            placeholder="3"
            value={pageNumber}
            onChange={(e) => setPageNumber(e.currentTarget.value)}
            size="sm"
            style={{ width: 90 }}
            styles={{
              input: { backgroundColor: 'var(--mi-surface)', borderColor: 'var(--mi-border)', color: 'var(--mi-text)' },
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
            size="sm"
            style={{ width: 120 }}
            styles={{
              input: { backgroundColor: 'var(--mi-surface)', borderColor: 'var(--mi-border)', color: 'var(--mi-text)' },
            }}
          />
        </Group>

        <Textarea
          label="Supporting Text / Exact Quote"
          placeholder="Paste the supporting text from the chart..."
          value={exactQuote}
          onChange={(e) => setExactQuote(e.currentTarget.value)}
          minRows={2}
          maxRows={4}
          autosize
          size="sm"
          styles={{
            input: { backgroundColor: 'var(--mi-surface)', borderColor: 'var(--mi-border)', color: 'var(--mi-text)' },
          }}
        />

        <Textarea
          label="Notes"
          placeholder="Optional coder notes..."
          value={notes}
          onChange={(e) => setNotes(e.currentTarget.value)}
          minRows={2}
          maxRows={3}
          autosize
          size="sm"
          styles={{
            input: { backgroundColor: 'var(--mi-surface)', borderColor: 'var(--mi-border)', color: 'var(--mi-text)' },
          }}
        />

        <Group justify="flex-end" gap={8}>
          <Button variant="subtle" color="gray" size="sm" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            color="blue"
            size="sm"
            leftSection={<IconPlus size={14} />}
            loading={isPending}
            disabled={!icdCode.trim() || !description.trim()}
            onClick={handleSubmit}
          >
            Add Diagnosis
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
