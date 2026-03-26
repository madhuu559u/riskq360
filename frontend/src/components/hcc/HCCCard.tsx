import { Accordion, Box, Text, Group, Badge, Stack, Tooltip, HoverCard } from '@mantine/core';
import {
  IconChevronRight,
  IconShieldCheck,
  IconAlertTriangle,
} from '@tabler/icons-react';
import type { HCCCode, HCCSupportingICD } from '../../types/risk';
import { usePDFStore } from '../../stores/pdfStore';
import { formatRAF, formatDate } from '../../utils/formatters';
import { getRiskLevelColor } from '../../utils/colors';
import { ConfidenceBar } from '../shared/ConfidenceBar';
import { EvidenceSnippet } from '../shared/EvidenceSnippet';
import { MEATDisplay } from './MEATDisplay';

interface HCCCardProps {
  hcc: HCCCode;
}

/* -------------------------------------------------------------------------- */
/* Single ICD detail row                                                       */
/* -------------------------------------------------------------------------- */
function ICDDetail({ icd }: { icd: HCCSupportingICD }) {
  const navigateToText = usePDFStore((s) => s.navigateToText);

  const primaryEvidenceText =
    (icd.evidence_spans ?? []).length > 0
      ? icd.evidence_spans[0].text
      : null;

  return (
    <Box
      style={{
        padding: '12px 14px',
        borderRadius: 'var(--mi-radius-md)',
        backgroundColor: 'var(--mi-surface)',
        border: '1px solid var(--mi-border)',
        transition: 'all var(--mi-transition-fast)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--mi-primary) 30%, transparent)';
        e.currentTarget.style.boxShadow = 'var(--mi-shadow-sm)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--mi-border)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      {/* ICD Header */}
      <Group justify="space-between" align="flex-start" mb={8} wrap="nowrap">
        <Group gap={8} align="center" style={{ minWidth: 0 }}>
          <Badge
            size="sm"
            variant="filled"
            color="blue"
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
            {icd.icd10_code}
          </Badge>
          <Text
            size="xs"
            fw={500}
            style={{
              color: 'var(--mi-text)',
              lineHeight: 1.3,
              minWidth: 0,
            }}
            lineClamp={2}
          >
            {icd.icd10_description}
          </Text>
        </Group>

        {icd.is_suppressed && icd.suppressed_by && (
          <Badge
            size="xs"
            variant="light"
            color="gray"
            styles={{
              root: {
                textTransform: 'none',
                textDecoration: 'line-through',
                flexShrink: 0,
              },
            }}
          >
            Suppressed by {icd.suppressed_by}
          </Badge>
        )}
      </Group>

      {/* Confidence */}
      <Group gap={8} wrap="nowrap" mb={10}>
        <Text
          size="xs"
          style={{
            color: 'var(--mi-text-muted)',
            flexShrink: 0,
            fontSize: 10,
          }}
        >
          Confidence
        </Text>
        <ConfidenceBar confidence={icd.confidence} size="sm" />
      </Group>

      {/* MEAT Evidence */}
      <Group justify="space-between" align="center" mb={8}>
        <MEATDisplay meat={icd.meat_evidence} compact />
        {icd.date_of_service && (
          <Text size="xs" style={{ color: 'var(--mi-text-muted)' }}>
            DOS: {formatDate(icd.date_of_service)}
          </Text>
        )}
      </Group>

      {/* Provider */}
      {icd.provider && (
        <Text size="xs" style={{ color: 'var(--mi-text-muted)', marginBottom: 8 }}>
          Provider: {icd.provider}
        </Text>
      )}

      {/* Evidence Text */}
      {primaryEvidenceText && (
        <EvidenceSnippet
          text={primaryEvidenceText}
          type="icd"
          label={`${icd.hcc_code} - ${icd.icd10_code}`}
          meta={{
            confidence: icd.confidence,
            code: icd.icd10_code,
            description: icd.icd10_description,
            sourceSection: icd.evidence_spans?.[0]?.section ?? undefined,
            provider: icd.provider ?? undefined,
            dateOfService: icd.date_of_service ?? undefined,
          }}
        />
      )}

      {/* Additional evidence spans */}
      {(icd.evidence_spans ?? []).length > 1 && (
        <Stack gap={4} mt={6}>
          {(icd.evidence_spans ?? []).slice(1).map((span, idx) => (
            <Box
              key={idx}
              onClick={() => navigateToText(span.text, 'icd', `${icd.icd10_code}`, {
                confidence: icd.confidence,
                code: icd.icd10_code,
                description: icd.icd10_description,
                sourceSection: span.section ?? undefined,
                provider: icd.provider ?? undefined,
                dateOfService: icd.date_of_service ?? undefined,
              })}
              style={{
                padding: '4px 8px',
                borderRadius: 'var(--mi-radius-sm)',
                cursor: 'pointer',
                transition: 'background-color var(--mi-transition-fast)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--mi-surface-hover)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              <Group gap={4}>
                {span.section && (
                  <Badge size="xs" variant="outline" color="gray" styles={{ root: { textTransform: 'none' } }}>
                    {span.section}
                  </Badge>
                )}
                <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontStyle: 'italic' }} lineClamp={1}>
                  &ldquo;{span.text}&rdquo;
                </Text>
              </Group>
            </Box>
          ))}
        </Stack>
      )}
    </Box>
  );
}

/* -------------------------------------------------------------------------- */
/* HCC Card (Accordion Item)                                                   */
/* -------------------------------------------------------------------------- */
export function HCCCard({ hcc }: HCCCardProps) {
  const riskColor = getRiskLevelColor(hcc.audit_risk ?? 'low');
  const icdCount = (hcc.supported_icds ?? []).length;

  return (
    <Accordion.Item
      value={hcc.hcc_code}
      style={{
        border: '1px solid var(--mi-border)',
        borderRadius: 10,
        backgroundColor: 'var(--mi-surface)',
        overflow: 'hidden',
        transition: 'all var(--mi-transition-fast)',
      }}
    >
      <Accordion.Control
        chevron={<IconChevronRight size={16} stroke={1.5} />}
        styles={{
          control: {
            padding: '12px 16px',
            backgroundColor: 'transparent',
            transition: 'background-color var(--mi-transition-fast)',
            '&:hover': {
              backgroundColor: 'var(--mi-surface-hover)',
            },
          },
          chevron: {
            transition: 'transform var(--mi-transition-fast)',
          },
        }}
      >
        <Group justify="space-between" align="center" wrap="nowrap" style={{ width: '100%' }}>
          <Group gap={10} align="center" wrap="nowrap" style={{ minWidth: 0 }}>
            {/* Risk indicator dot */}
            <Tooltip label={`Audit risk: ${hcc.audit_risk ?? 'unknown'}`} withArrow>
              <Box
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  flexShrink: 0,
                  backgroundColor: `var(--mi-${riskColor === 'yellow' ? 'warning' : riskColor === 'red' ? 'error' : 'success'})`,
                  boxShadow: `0 0 6px color-mix(in srgb, var(--mi-${riskColor === 'yellow' ? 'warning' : riskColor === 'red' ? 'error' : 'success'}) 40%, transparent)`,
                }}
              />
            </Tooltip>

            {/* HCC Code badge */}
            <Badge
              size="md"
              variant="light"
              color="blue"
              radius="md"
              styles={{
                root: {
                  fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                  fontWeight: 700,
                  textTransform: 'none',
                  flexShrink: 0,
                },
              }}
            >
              HCC {hcc.hcc_code}
            </Badge>

            {/* Description with HoverCard */}
            <HoverCard openDelay={300} position="bottom" width={340} shadow="lg" withArrow>
              <HoverCard.Target>
                <Text
                  size="sm"
                  fw={600}
                  style={{
                    color: 'var(--mi-text)',
                    minWidth: 0,
                    lineHeight: 1.3,
                  }}
                  lineClamp={1}
                >
                  {hcc.hcc_description}
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
                      variant="light"
                      color="blue"
                      radius="md"
                      styles={{ root: { fontFamily: '"JetBrains Mono", "Fira Code", monospace', fontWeight: 700, textTransform: 'none' } }}
                    >
                      HCC {hcc.hcc_code}
                    </Badge>
                    <Badge
                      size="sm"
                      variant="filled"
                      styles={{ root: { background: 'linear-gradient(135deg, var(--mi-primary), var(--mi-accent))', textTransform: 'none', fontWeight: 700, fontVariantNumeric: 'tabular-nums' } }}
                    >
                      RAF {formatRAF(hcc.raf_weight)}
                    </Badge>
                  </Group>
                  <Text size="sm" fw={600} style={{ color: 'var(--mi-text)', lineHeight: 1.4 }}>
                    {hcc.hcc_description}
                  </Text>
                  <Group gap={12}>
                    <Box>
                      <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 9 }}>ICD Codes</Text>
                      <Text size="xs" fw={600} style={{ color: 'var(--mi-text)' }}>{icdCount}</Text>
                    </Box>
                    <Box>
                      <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 9 }}>Audit Risk</Text>
                      <Text size="xs" fw={600} style={{ color: `var(--mi-${riskColor === 'yellow' ? 'warning' : riskColor === 'red' ? 'error' : 'success'})` }}>
                        {hcc.audit_risk ?? 'unknown'}
                      </Text>
                    </Box>
                    {hcc.hierarchy_applied && (
                      <Box>
                        <Text size="xs" style={{ color: 'var(--mi-text-muted)', fontSize: 9 }}>Hierarchy</Text>
                        <Text size="xs" fw={600} style={{ color: 'var(--mi-warning)' }}>
                          Suppresses {(hcc.suppresses ?? []).length}
                        </Text>
                      </Box>
                    )}
                  </Group>
                  {/* First 4 ICD code badges */}
                  {icdCount > 0 && (
                    <Group gap={4} wrap="wrap">
                      {(hcc.supported_icds ?? []).slice(0, 4).map((icd, idx) => (
                        <Badge
                          key={`${icd.icd10_code}-${idx}`}
                          size="xs"
                          variant="light"
                          color="blue"
                          radius="md"
                          styles={{ root: { fontFamily: '"JetBrains Mono", "Fira Code", monospace', fontWeight: 600, textTransform: 'none', fontSize: 10 } }}
                        >
                          {icd.icd10_code}
                        </Badge>
                      ))}
                      {icdCount > 4 && (
                        <Badge size="xs" variant="light" color="gray" radius="md" styles={{ root: { textTransform: 'none', fontSize: 10 } }}>
                          +{icdCount - 4} more
                        </Badge>
                      )}
                    </Group>
                  )}
                </Stack>
              </HoverCard.Dropdown>
            </HoverCard>
          </Group>

          {/* Right side: RAF weight + ICD count */}
          <Group gap={8} wrap="nowrap" style={{ flexShrink: 0 }}>
            <Badge
              size="sm"
              variant="filled"
              styles={{
                root: {
                  background: 'linear-gradient(135deg, var(--mi-primary), var(--mi-accent))',
                  textTransform: 'none',
                  fontWeight: 700,
                  fontVariantNumeric: 'tabular-nums',
                },
              }}
            >
              {formatRAF(hcc.raf_weight)}
            </Badge>

            <Badge
              size="sm"
              variant="light"
              color="gray"
              styles={{ root: { textTransform: 'none' } }}
            >
              {icdCount} ICD{icdCount !== 1 ? 's' : ''}
            </Badge>

            {hcc.hierarchy_applied && (hcc.suppresses?.length ?? 0) > 0 && (
              <Tooltip
                label={`Suppresses: ${(hcc.suppresses ?? []).join(', ')}`}
                withArrow
                multiline
                maw={260}
              >
                <Badge
                  size="sm"
                  variant="light"
                  color="orange"
                  leftSection={<IconAlertTriangle size={10} stroke={2} />}
                  styles={{ root: { textTransform: 'none' } }}
                >
                  Hierarchy
                </Badge>
              </Tooltip>
            )}
          </Group>
        </Group>
      </Accordion.Control>

      <Accordion.Panel
        styles={{
          content: {
            padding: '4px 16px 16px',
          },
        }}
      >
        <Stack gap={10}>
          {(hcc.supported_icds ?? []).map((icd, idx) => (
            <ICDDetail key={`${icd.icd10_code}-${icd.hcc_code}-${idx}`} icd={icd} />
          ))}

          {(hcc.supported_icds ?? []).length === 0 && (
            <Box
              style={{
                padding: 20,
                textAlign: 'center',
                borderRadius: 'var(--mi-radius-md)',
                backgroundColor: 'var(--mi-surface-hover)',
              }}
            >
              <Text size="sm" c="dimmed">
                No supporting ICD codes found
              </Text>
            </Box>
          )}

          {/* Suppression info */}
          {(hcc.suppresses?.length ?? 0) > 0 && (
            <Box
              style={{
                padding: '10px 14px',
                borderRadius: 'var(--mi-radius-md)',
                backgroundColor: 'color-mix(in srgb, var(--mi-warning) 6%, var(--mi-surface))',
                border: '1px solid color-mix(in srgb, var(--mi-warning) 20%, transparent)',
              }}
            >
              <Group gap={6} align="center" mb={4}>
                <IconAlertTriangle size={14} stroke={1.5} color="var(--mi-warning)" />
                <Text size="xs" fw={600} style={{ color: 'var(--mi-warning)' }}>
                  Hierarchy Suppression Active
                </Text>
              </Group>
              <Text size="xs" style={{ color: 'var(--mi-text-secondary)' }}>
                This HCC suppresses: {(hcc.suppresses ?? []).map((code) => `HCC ${code}`).join(', ')}
              </Text>
            </Box>
          )}
        </Stack>
      </Accordion.Panel>
    </Accordion.Item>
  );
}
