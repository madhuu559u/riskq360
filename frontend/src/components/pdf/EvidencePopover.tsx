import { useRef, useState, useCallback } from 'react';
import {
  Box,
  Text,
  Badge,
  Progress,
  Group,
  Button,
  CloseButton,
  Textarea,
  ActionIcon,
  Tooltip,
} from '@mantine/core';
import {
  IconStethoscope,
  IconHeartRateMonitor,
  IconFlask,
  IconBrain,
  IconSearch,
  IconCode,
  IconBandage,
  IconCheck,
  IconX,
  IconMessage,
  IconChevronDown,
} from '@tabler/icons-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { PDFHighlight } from '../../stores/pdfStore';

/* ========================================================================= */
/* Highlight type metadata                                                    */
/* ========================================================================= */
const HIGHLIGHT_META: Record<
  PDFHighlight['type'],
  { label: string; color: string; icon: typeof IconStethoscope; gradient: string }
> = {
  diagnosis: {
    label: 'Diagnosis',
    color: 'var(--mi-info)',
    icon: IconStethoscope,
    gradient: 'linear-gradient(135deg, var(--mi-primary), var(--mi-accent))',
  },
  hedis: {
    label: 'HEDIS',
    color: 'var(--mi-success)',
    icon: IconHeartRateMonitor,
    gradient: 'linear-gradient(135deg, var(--mi-success), #34D399)',
  },
  negated: {
    label: 'Negated',
    color: 'var(--mi-error)',
    icon: IconBandage,
    gradient: 'linear-gradient(135deg, var(--mi-error), #F87171)',
  },
  meat: {
    label: 'MEAT Evidence',
    color: 'var(--mi-warning)',
    icon: IconFlask,
    gradient: 'linear-gradient(135deg, var(--mi-warning), #FBBF24)',
  },
  ml: {
    label: 'ML Prediction',
    color: '#8B5CF6',
    icon: IconBrain,
    gradient: 'linear-gradient(135deg, #8B5CF6, #A78BFA)',
  },
  search: {
    label: 'Search Match',
    color: '#FBBF24',
    icon: IconSearch,
    gradient: 'linear-gradient(135deg, #FBBF24, #FDE68A)',
  },
  icd: {
    label: 'ICD Code',
    color: '#06B6D4',
    icon: IconCode,
    gradient: 'linear-gradient(135deg, #06B6D4, #22D3EE)',
  },
};

/* ========================================================================= */
/* Props                                                                      */
/* ========================================================================= */
interface EvidencePopoverProps {
  highlight: PDFHighlight;
  position: { x: number; y: number };
  containerRect: DOMRect | null;
  onClose: () => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  onViewInPanel?: () => void;
  confidence?: number;
  icdCode?: string;
  icdDescription?: string;
  sourceSection?: string;
  provider?: string;
  dateOfService?: string;
}

/* ========================================================================= */
/* Component                                                                  */
/* ========================================================================= */
export function EvidencePopover({
  highlight,
  position,
  containerRect,
  onClose,
  onMouseEnter,
  onMouseLeave,
  onViewInPanel,
  confidence,
  icdCode,
  icdDescription,
  sourceSection,
  provider,
  dateOfService,
}: EvidencePopoverProps) {
  const popoverRef = useRef<HTMLDivElement>(null);
  const [showNoteInput, setShowNoteInput] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [reviewAction, setReviewAction] = useState<'accepted' | 'rejected' | null>(null);

  const meta = HIGHLIGHT_META[highlight.type];
  const Icon = meta.icon;

  const handleAccept = useCallback(() => {
    setReviewAction('accepted');
    setTimeout(() => setReviewAction(null), 2000);
  }, []);

  const handleReject = useCallback(() => {
    setReviewAction('rejected');
    setTimeout(() => setReviewAction(null), 2000);
  }, []);

  const handleAddNote = useCallback(() => {
    if (noteText.trim()) {
      setNoteText('');
      setShowNoteInput(false);
    }
  }, [noteText]);

  /* Position: bottom-left of popup = top-left of highlight.
     position.x = highlight left, position.y = highlight top (viewport coords).
     We use `bottom` positioning: bottom = viewportHeight - position.y */
  const viewportWidth = typeof window !== 'undefined' ? window.innerWidth : 1200;
  const viewportHeight = typeof window !== 'undefined' ? window.innerHeight : 800;
  const popoverWidth = 300;

  let left = position.x;
  /* If popup would go off right edge, shift left */
  if (left + popoverWidth > viewportWidth - 8) {
    left = Math.max(8, viewportWidth - popoverWidth - 8);
  }
  if (left < 8) left = 8;

  /* bottom = distance from viewport bottom to the highlight top */
  let bottom = viewportHeight - position.y;
  /* If popup would go off top of screen, flip to show BELOW highlight instead */
  const showBelow = bottom > viewportHeight - 40;
  let topVal: number | undefined;
  let bottomVal: number | undefined;
  if (showBelow) {
    topVal = position.y + 4;
    bottomVal = undefined;
  } else {
    topVal = undefined;
    bottomVal = Math.max(4, bottom);
  }

  return (
    <AnimatePresence>
      <motion.div
        ref={popoverRef}
        initial={{ opacity: 0, y: showBelow ? -6 : 6, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: showBelow ? -4 : 4, scale: 0.98 }}
        transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        style={{
          position: 'fixed',
          ...(topVal !== undefined ? { top: topVal } : {}),
          ...(bottomVal !== undefined ? { bottom: bottomVal } : {}),
          left,
          width: popoverWidth,
          zIndex: 10000,
          pointerEvents: 'auto',
        }}
      >

        {/* Card body */}
        <Box
          style={{
            borderRadius: 14,
            boxShadow: 'var(--mi-shadow-xl), 0 0 0 1px color-mix(in srgb, var(--mi-primary) 8%, transparent)',
            overflow: 'hidden',
            border: '1px solid color-mix(in srgb, var(--mi-primary) 15%, var(--mi-border))',
            background: 'var(--mi-surface)',
          }}
        >
          {/* Header gradient bar */}
          <Box
            style={{
              height: 3,
              background: meta.gradient,
            }}
          />

          <Box style={{ padding: '10px 12px' }}>
            {/* Top: Type badge + review status + close */}
            <Group justify="space-between" align="center" mb={8}>
              <Group gap={6}>
                <Badge
                  size="sm"
                  variant="light"
                  leftSection={<Icon size={11} />}
                  styles={{
                    root: {
                      backgroundColor: `color-mix(in srgb, ${meta.color} 12%, var(--mi-surface))`,
                      color: meta.color,
                      border: `1px solid color-mix(in srgb, ${meta.color} 25%, transparent)`,
                      fontWeight: 700,
                      fontSize: 10,
                    },
                  }}
                >
                  {meta.label}
                </Badge>
                {reviewAction && (
                  <Badge
                    size="xs"
                    variant="filled"
                    color={reviewAction === 'accepted' ? 'green' : 'red'}
                    styles={{ root: { animation: 'mi-scale-in 0.2s ease-out', fontSize: 9 } }}
                  >
                    {reviewAction === 'accepted' ? 'Accepted' : 'Rejected'}
                  </Badge>
                )}
              </Group>
              <CloseButton size="xs" onClick={onClose} style={{ color: 'var(--mi-text-muted)' }} />
            </Group>

            {/* Evidence text */}
            {highlight.text && (
              <Box
                style={{
                  padding: '8px 10px',
                  borderRadius: 8,
                  backgroundColor: 'color-mix(in srgb, var(--mi-primary) 4%, var(--mi-surface))',
                  border: '1px solid color-mix(in srgb, var(--mi-primary) 10%, transparent)',
                  marginBottom: 8,
                }}
              >
                <Text
                  size="xs"
                  style={{
                    color: 'var(--mi-text-secondary)',
                    lineHeight: 1.5,
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    fontStyle: 'italic',
                    fontSize: 11,
                  }}
                >
                  &ldquo;{highlight.text}&rdquo;
                </Text>
              </Box>
            )}

            {/* ICD code info */}
            {icdCode && (
              <Group gap={6} mb={6} wrap="nowrap">
                <Badge
                  size="xs"
                  variant="outline"
                  styles={{
                    root: {
                      color: 'var(--mi-primary)',
                      borderColor: 'var(--mi-primary)',
                      fontFamily: '"JetBrains Mono", monospace',
                      flexShrink: 0,
                      fontWeight: 700,
                    },
                  }}
                >
                  {icdCode}
                </Badge>
                {icdDescription && (
                  <Text
                    size="xs"
                    style={{
                      color: 'var(--mi-text-muted)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      fontSize: 11,
                    }}
                  >
                    {icdDescription}
                  </Text>
                )}
              </Group>
            )}

            {(sourceSection || provider || dateOfService) && (
              <Box
                style={{
                  marginBottom: 6,
                  padding: '6px 8px',
                  borderRadius: 6,
                  backgroundColor: 'var(--mi-surface-hover)',
                }}
              >
                {sourceSection && (
                  <Text size="xs" style={{ fontSize: 10, color: 'var(--mi-text-muted)' }}>
                    Section: <Text component="span" inherit fw={600} style={{ color: 'var(--mi-text)' }}>{sourceSection}</Text>
                  </Text>
                )}
                {provider && (
                  <Text size="xs" style={{ fontSize: 10, color: 'var(--mi-text-muted)' }}>
                    Provider: <Text component="span" inherit fw={600} style={{ color: 'var(--mi-text)' }}>{provider}</Text>
                  </Text>
                )}
                {dateOfService && (
                  <Text size="xs" style={{ fontSize: 10, color: 'var(--mi-text-muted)' }}>
                    DOS: <Text component="span" inherit fw={600} style={{ color: 'var(--mi-text)' }}>{dateOfService}</Text>
                  </Text>
                )}
              </Box>
            )}

            {/* Confidence bar */}
            {confidence !== undefined && confidence !== null && (
              <Box mb={8}>
                <Group justify="space-between" mb={3}>
                  <Text size="xs" style={{ fontSize: 10, color: 'var(--mi-text-muted)' }}>
                    Confidence
                  </Text>
                  <Text size="xs" fw={700} style={{ color: 'var(--mi-text)', fontSize: 11 }}>
                    {(confidence * 100).toFixed(0)}%
                  </Text>
                </Group>
                <Progress
                  value={confidence * 100}
                  size={6}
                  radius="xl"
                  color={
                    confidence >= 0.8
                      ? 'green'
                      : confidence >= 0.5
                        ? 'yellow'
                        : 'red'
                  }
                  styles={{
                    root: {
                      backgroundColor: 'var(--mi-surface-hover)',
                    },
                  }}
                />
              </Box>
            )}

            {/* Page info */}
            <Group justify="space-between" align="center" mb={8}>
              {highlight.label && (
                <Text
                  size="xs"
                  fw={700}
                  style={{
                    color: meta.color,
                    fontFamily: '"JetBrains Mono", monospace',
                    fontSize: 10,
                  }}
                >
                  {highlight.label}
                </Text>
              )}
              <Badge size="xs" variant="light" color="gray" styles={{ root: { textTransform: 'none', fontSize: 9 } }}>
                Page {highlight.page}
              </Badge>
            </Group>

            {/* Action Buttons - Accept/Reject only for diagnosis/hedis, Note always */}
            <Box
              style={{
                borderTop: '1px solid var(--mi-border)',
                paddingTop: 8,
                marginTop: 4,
              }}
            >
              <Group gap={6} justify="space-between">
                {(highlight.type === 'diagnosis' || highlight.type === 'hedis') && (
                  <Group gap={4}>
                    <Tooltip label="Accept evidence" withArrow>
                      <Button
                        size="compact-xs"
                        variant="light"
                        color="green"
                        leftSection={<IconCheck size={12} stroke={2.5} />}
                        onClick={handleAccept}
                        disabled={reviewAction !== null}
                        styles={{
                          root: {
                            fontSize: 10,
                            fontWeight: 700,
                            height: 26,
                            borderRadius: 8,
                            paddingLeft: 8,
                            paddingRight: 10,
                            border: '1px solid color-mix(in srgb, var(--mi-success) 30%, transparent)',
                            transition: 'all var(--mi-transition-fast)',
                          },
                        }}
                      >
                        Accept
                      </Button>
                    </Tooltip>
                    <Tooltip label="Reject evidence" withArrow>
                      <Button
                        size="compact-xs"
                        variant="light"
                        color="red"
                        leftSection={<IconX size={12} stroke={2.5} />}
                        onClick={handleReject}
                        disabled={reviewAction !== null}
                        styles={{
                          root: {
                            fontSize: 10,
                            fontWeight: 700,
                            height: 26,
                            borderRadius: 8,
                            paddingLeft: 8,
                            paddingRight: 10,
                            border: '1px solid color-mix(in srgb, var(--mi-error) 30%, transparent)',
                            transition: 'all var(--mi-transition-fast)',
                          },
                        }}
                      >
                        Reject
                      </Button>
                    </Tooltip>
                  </Group>
                )}
                {highlight.type !== 'diagnosis' && highlight.type !== 'hedis' && <Box />}
                <Tooltip label="Add a note" withArrow>
                  <ActionIcon
                    size={26}
                    radius={8}
                    variant="light"
                    color="blue"
                    onClick={() => setShowNoteInput(!showNoteInput)}
                    style={{
                      border: '1px solid color-mix(in srgb, var(--mi-primary) 25%, transparent)',
                      transition: 'all var(--mi-transition-fast)',
                    }}
                  >
                    <IconMessage size={13} stroke={2} />
                  </ActionIcon>
                </Tooltip>
              </Group>

              {/* Note Input Area */}
              <AnimatePresence>
                {showNoteInput && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Box mt={6}>
                      <Textarea
                        placeholder="Add a review note..."
                        value={noteText}
                        onChange={(e) => setNoteText(e.currentTarget.value)}
                        minRows={2}
                        maxRows={3}
                        autosize
                        size="xs"
                        styles={{
                          input: {
                            backgroundColor: 'var(--mi-background)',
                            borderColor: 'var(--mi-border)',
                            color: 'var(--mi-text)',
                            fontSize: 11,
                            borderRadius: 8,
                          },
                        }}
                      />
                      <Group justify="flex-end" mt={4}>
                        <Button
                          size="compact-xs"
                          variant="filled"
                          disabled={!noteText.trim()}
                          onClick={handleAddNote}
                          styles={{
                            root: {
                              fontSize: 10,
                              fontWeight: 700,
                              height: 24,
                              borderRadius: 6,
                              backgroundColor: 'var(--mi-primary)',
                            },
                          }}
                        >
                          Save Note
                        </Button>
                      </Group>
                    </Box>
                  </motion.div>
                )}
              </AnimatePresence>
            </Box>

            {/* View in panel button */}
            {onViewInPanel && (
              <Button
                size="xs"
                variant="subtle"
                fullWidth
                mt={6}
                rightSection={<IconChevronDown size={12} />}
                onClick={onViewInPanel}
                styles={{
                  root: {
                    color: 'var(--mi-primary)',
                    fontSize: 10,
                    fontWeight: 600,
                    height: 28,
                    borderRadius: 8,
                  },
                }}
              >
                View in panel
              </Button>
            )}
          </Box>
        </Box>
      </motion.div>
    </AnimatePresence>
  );
}
