import { useState, useCallback, useRef, useEffect } from 'react';
import {
  Modal,
  TextInput,
  Text,
  Badge,
  Group,
  Stack,
  Box,
  Button,
  Loader,
  Switch,
  Tooltip,
  ScrollArea,
} from '@mantine/core';
import {
  IconSearch,
  IconCode,
  IconPlus,
  IconStethoscope,
} from '@tabler/icons-react';
import { useCodingSuggestions } from '../../hooks/useChart';
import type { CodingHelperResult } from '../../api/review';

interface CodingHelperModalProps {
  opened: boolean;
  onClose: () => void;
  onSelect: (result: CodingHelperResult) => void;
  initialQuery?: string;
}

export function CodingHelperModal({
  opened,
  onClose,
  onSelect,
  initialQuery = '',
}: CodingHelperModalProps) {
  const [query, setQuery] = useState(initialQuery);
  const [paymentOnly, setPaymentOnly] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Update query when initialQuery changes (e.g., from text selection)
  useEffect(() => {
    if (opened && initialQuery) {
      setQuery(initialQuery);
    }
  }, [opened, initialQuery]);

  // Focus input on open
  useEffect(() => {
    if (opened) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [opened]);

  const { data, isLoading, isFetching } = useCodingSuggestions(query, 20, paymentOnly);

  const handleSelect = useCallback(
    (result: CodingHelperResult) => {
      onSelect(result);
      onClose();
    },
    [onSelect, onClose],
  );

  const handleClose = useCallback(() => {
    setQuery('');
    onClose();
  }, [onClose]);

  const results = data?.results ?? [];
  const indexSize = data?.index_size ?? 0;

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title={
        <Group gap={8}>
          <IconStethoscope size={18} color="var(--mi-primary)" />
          <Text fw={700} size="sm">
            ICD-10 Code Helper
          </Text>
          {indexSize > 0 && (
            <Badge size="xs" variant="light" color="gray" styles={{ root: { textTransform: 'none' } }}>
              {indexSize.toLocaleString()} codes indexed
            </Badge>
          )}
        </Group>
      }
      size="lg"
      centered
      styles={{
        header: { borderBottom: '1px solid var(--mi-border)' },
        body: { padding: 0 },
      }}
    >
      <Box p={16}>
        <Group gap={8} mb={12} align="flex-end">
          <TextInput
            ref={inputRef}
            placeholder="Search by description, ICD code, or clinical term..."
            leftSection={<IconSearch size={14} />}
            rightSection={isFetching ? <Loader size={14} /> : null}
            value={query}
            onChange={(e) => setQuery(e.currentTarget.value)}
            size="sm"
            style={{ flex: 1 }}
            styles={{
              input: {
                backgroundColor: 'var(--mi-surface)',
                borderColor: 'var(--mi-border)',
                color: 'var(--mi-text)',
              },
            }}
          />
          <Switch
            label="HCC only"
            size="xs"
            checked={paymentOnly}
            onChange={(e) => setPaymentOnly(e.currentTarget.checked)}
            styles={{
              label: { fontSize: 11, color: 'var(--mi-text-muted)' },
            }}
          />
        </Group>

        {query.trim().length < 2 && (
          <Text size="sm" c="dimmed" ta="center" py={32}>
            Type at least 2 characters to search ICD-10 codes
          </Text>
        )}

        {query.trim().length >= 2 && isLoading && (
          <Box ta="center" py={32}>
            <Loader size="md" />
            <Text size="sm" c="dimmed" mt={8}>
              Searching...
            </Text>
          </Box>
        )}

        {query.trim().length >= 2 && !isLoading && results.length === 0 && (
          <Text size="sm" c="dimmed" ta="center" py={32}>
            No matching ICD-10 codes found for "{query}"
          </Text>
        )}

        {results.length > 0 && (
          <>
            <Text size="xs" c="dimmed" mb={8}>
              {results.length} result{results.length !== 1 ? 's' : ''} found
            </Text>
            <ScrollArea.Autosize mah={400}>
              <Stack gap={4}>
                {results.map((r) => (
                  <SuggestionRow
                    key={`${r.icd10_code}-${r.hcc_code}`}
                    result={r}
                    onSelect={handleSelect}
                  />
                ))}
              </Stack>
            </ScrollArea.Autosize>
          </>
        )}
      </Box>
    </Modal>
  );
}

/* -------------------------------------------------------------------------- */
/* Suggestion Row                                                              */
/* -------------------------------------------------------------------------- */
function SuggestionRow({
  result,
  onSelect,
}: {
  result: CodingHelperResult;
  onSelect: (r: CodingHelperResult) => void;
}) {
  return (
    <Box
      onClick={() => onSelect(result)}
      style={{
        padding: '8px 10px',
        borderRadius: 8,
        border: '1px solid var(--mi-border)',
        backgroundColor: 'var(--mi-surface)',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--mi-primary) 30%, transparent)';
        e.currentTarget.style.backgroundColor = 'color-mix(in srgb, var(--mi-primary) 4%, var(--mi-surface))';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--mi-border)';
        e.currentTarget.style.backgroundColor = 'var(--mi-surface)';
      }}
    >
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <Group gap={8} align="center" style={{ minWidth: 0, flex: 1 }}>
          <Badge
            size="sm"
            variant="filled"
            color="violet"
            radius="md"
            styles={{
              root: {
                fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                fontWeight: 700,
                fontSize: 11,
                textTransform: 'none',
                flexShrink: 0,
              },
            }}
          >
            {result.icd10_code}
          </Badge>
          <Text
            size="xs"
            fw={500}
            style={{ color: 'var(--mi-text)', minWidth: 0 }}
            lineClamp={2}
          >
            {result.description}
          </Text>
        </Group>

        <Group gap={6} style={{ flexShrink: 0 }}>
          {result.hcc_code && (
            <Badge
              size="xs"
              variant="light"
              color={result.is_payment_hcc ? 'green' : 'gray'}
              styles={{ root: { textTransform: 'none', fontFamily: '"JetBrains Mono", monospace', fontSize: 9 } }}
            >
              {result.hcc_code}
            </Badge>
          )}
          <Badge
            size="xs"
            variant="outline"
            color="gray"
            styles={{
              root: {
                textTransform: 'none',
                fontFamily: '"JetBrains Mono", monospace',
                fontSize: 9,
              },
            }}
          >
            {result.score.toFixed(2)}
          </Badge>
          <Tooltip label="Add this code" withArrow>
            <Box
              style={{
                width: 22,
                height: 22,
                borderRadius: 6,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'color-mix(in srgb, var(--mi-primary) 10%, transparent)',
                color: 'var(--mi-primary)',
              }}
            >
              <IconPlus size={12} stroke={2.5} />
            </Box>
          </Tooltip>
        </Group>
      </Group>

      {result.hcc_label && result.hcc_label !== result.description && (
        <Text size="xs" c="dimmed" mt={4} lineClamp={1}>
          HCC: {result.hcc_label}
        </Text>
      )}
    </Box>
  );
}
