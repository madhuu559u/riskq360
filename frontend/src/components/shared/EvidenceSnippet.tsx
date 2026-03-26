import { Box, Text, ActionIcon, Tooltip } from '@mantine/core';
import { IconFileSearch } from '@tabler/icons-react';
import { usePDFStore, type PDFHighlight, type PDFHighlightMeta } from '../../stores/pdfStore';

interface EvidenceSnippetProps {
  text: string | null;
  type?: PDFHighlight['type'];
  label?: string;
  maxLength?: number;
  showIcon?: boolean;
  meta?: PDFHighlightMeta;
}

export function EvidenceSnippet({
  text,
  type = 'diagnosis',
  label,
  maxLength = 180,
  showIcon = true,
  meta,
}: EvidenceSnippetProps) {
  const navigateToText = usePDFStore((s) => s.navigateToText);

  if (!text) return null;

  const displayText = text.length > maxLength ? text.slice(0, maxLength) + '...' : text;

  const handleClick = () => {
    navigateToText(text, type, label, meta);
  };

  return (
    <Box
      onClick={handleClick}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
        padding: '8px 10px',
        borderRadius: 'var(--mi-radius-md)',
        backgroundColor: 'color-mix(in srgb, var(--mi-primary) 4%, var(--mi-surface))',
        border: '1px solid color-mix(in srgb, var(--mi-primary) 12%, transparent)',
        cursor: 'pointer',
        transition: 'all var(--mi-transition-fast)',
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget;
        el.style.backgroundColor = 'color-mix(in srgb, var(--mi-primary) 8%, var(--mi-surface))';
        el.style.borderColor = 'color-mix(in srgb, var(--mi-primary) 25%, transparent)';
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget;
        el.style.backgroundColor = 'color-mix(in srgb, var(--mi-primary) 4%, var(--mi-surface))';
        el.style.borderColor = 'color-mix(in srgb, var(--mi-primary) 12%, transparent)';
      }}
    >
      <Text
        size="xs"
        style={{
          flex: 1,
          color: 'var(--mi-text-secondary)',
          lineHeight: 1.5,
          fontStyle: 'italic',
          minWidth: 0,
          wordBreak: 'break-word',
        }}
      >
        &ldquo;{displayText}&rdquo;
      </Text>
      {showIcon && (
        <Tooltip label="View in PDF" withArrow>
          <ActionIcon
            size="sm"
            variant="subtle"
            color="blue"
            onClick={(e) => {
              e.stopPropagation();
              handleClick();
            }}
            style={{ flexShrink: 0, marginTop: 1 }}
          >
            <IconFileSearch size={14} stroke={1.5} />
          </ActionIcon>
        </Tooltip>
      )}
    </Box>
  );
}
