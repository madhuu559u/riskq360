import { useState } from 'react';
import {
  Modal,
  Text,
  Textarea,
  Button,
  Group,
  Stack,
  Badge,
} from '@mantine/core';
import { IconCheck, IconX } from '@tabler/icons-react';

interface ReviewModalProps {
  opened: boolean;
  onClose: () => void;
  onConfirm: (notes: string) => void;
  action: 'accept' | 'reject';
  itemType: 'Diagnosis' | 'HCC' | 'HEDIS';
  itemLabel: string;
  isPending?: boolean;
}

export function ReviewModal({
  opened,
  onClose,
  onConfirm,
  action,
  itemType,
  itemLabel,
  isPending,
}: ReviewModalProps) {
  const [notes, setNotes] = useState('');

  const handleConfirm = () => {
    onConfirm(notes);
    setNotes('');
  };

  const handleClose = () => {
    setNotes('');
    onClose();
  };

  const isAccept = action === 'accept';
  const color = isAccept ? 'green' : 'red';
  const Icon = isAccept ? IconCheck : IconX;
  const actionLabel = isAccept ? 'Accept' : 'Reject';

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title={
        <Group gap={8}>
          <Icon size={18} color={`var(--mantine-color-${color}-6)`} />
          <Text fw={700} size="sm">
            {actionLabel} {itemType}
          </Text>
        </Group>
      }
      size="sm"
      centered
      styles={{
        header: { borderBottom: '1px solid var(--mi-border)' },
        body: { padding: 16 },
      }}
    >
      <Stack gap={12}>
        <Badge
          size="lg"
          variant="light"
          color={color}
          styles={{ root: { textTransform: 'none', fontWeight: 600 } }}
        >
          {itemLabel}
        </Badge>

        <Textarea
          label="Comments (optional)"
          placeholder={`Add notes for why you are ${action === 'accept' ? 'accepting' : 'rejecting'} this ${itemType.toLowerCase()}...`}
          value={notes}
          onChange={(e) => setNotes(e.currentTarget.value)}
          minRows={3}
          maxRows={5}
          autosize
          size="sm"
          styles={{
            input: {
              backgroundColor: 'var(--mi-surface)',
              borderColor: 'var(--mi-border)',
              color: 'var(--mi-text)',
            },
          }}
        />

        <Group justify="flex-end" gap={8}>
          <Button variant="subtle" color="gray" size="sm" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            color={color}
            size="sm"
            leftSection={<Icon size={14} />}
            loading={isPending}
            onClick={handleConfirm}
          >
            {actionLabel}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
