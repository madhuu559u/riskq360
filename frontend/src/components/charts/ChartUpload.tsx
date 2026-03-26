import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Modal,
  Text,
  Group,
  Box,
  Progress,
  Stack,
  ThemeIcon,
  Badge,
} from '@mantine/core';
import { Dropzone, MIME_TYPES } from '@mantine/dropzone';
import {
  IconUpload,
  IconFileTypePdf,
  IconX,
  IconCheck,
  IconCloudUpload,
} from '@tabler/icons-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useUploadChart } from '../../hooks/useChart';
import { useChartStore } from '../../stores/chartStore';

interface ChartUploadProps {
  opened: boolean;
  onClose: () => void;
}

export function ChartUpload({ opened, onClose }: ChartUploadProps) {
  const navigate = useNavigate();
  const { setActiveChart } = useChartStore();
  const uploadMutation = useUploadChart();

  const handleDrop = useCallback(
    (files: File[]) => {
      const file = files[0];
      if (!file) return;

      uploadMutation.mutate(file, {
        onSuccess: (data) => {
          setTimeout(() => {
            setActiveChart(data.chart_id);
            navigate(`/charts/${data.chart_id}`);
            onClose();
          }, 1200);
        },
      });
    },
    [uploadMutation, navigate, setActiveChart, onClose],
  );

  const isUploading = uploadMutation.isPending;
  const isSuccess = uploadMutation.isSuccess;
  const isError = uploadMutation.isError;

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap={10}>
          <ThemeIcon
            size={28}
            radius="md"
            variant="light"
            color="blue"
          >
            <IconCloudUpload size={16} stroke={2} />
          </ThemeIcon>
          <Text fw={700} size="lg" style={{ color: 'var(--mi-text)' }}>
            Upload Medical Chart
          </Text>
        </Group>
      }
      size="lg"
      radius="xl"
      centered
      overlayProps={{ backgroundOpacity: 0.25, blur: 6 }}
      styles={{
        content: {
          backgroundColor: 'var(--mi-surface)',
          borderColor: 'var(--mi-border)',
        },
        header: {
          backgroundColor: 'var(--mi-surface)',
          borderBottom: '1px solid var(--mi-border)',
          paddingBottom: 16,
        },
        body: {
          padding: 24,
        },
      }}
      closeButtonProps={{ 'aria-label': 'Close upload dialog' }}
    >
      <AnimatePresence mode="wait">
        {isSuccess ? (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Stack align="center" gap={16} py={40}>
              <ThemeIcon
                size={64}
                radius="xl"
                color="green"
                variant="light"
              >
                <IconCheck size={32} stroke={2} />
              </ThemeIcon>
              <Text size="lg" fw={700} style={{ color: 'var(--mi-text)' }}>
                Upload Successful!
              </Text>
              <Text size="sm" c="dimmed" ta="center">
                Your chart has been uploaded and processing has started.
                <br />
                Redirecting to chart viewer...
              </Text>
              <Progress
                value={100}
                color="green"
                size="sm"
                radius="xl"
                w="60%"
                animated
              />
            </Stack>
          </motion.div>
        ) : (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Dropzone
              onDrop={handleDrop}
              accept={[MIME_TYPES.pdf]}
              maxSize={100 * 1024 * 1024}
              maxFiles={1}
              disabled={isUploading}
              loading={isUploading}
              radius="lg"
              styles={{
                root: {
                  minHeight: 200,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderWidth: 2,
                  borderStyle: 'dashed',
                  borderColor: isError ? 'var(--mi-error)' : 'var(--mi-border)',
                  backgroundColor: 'var(--mi-surface)',
                  transition: 'all var(--mi-transition-fast)',
                  cursor: isUploading ? 'wait' : 'pointer',
                },
              }}
            >
              <Stack align="center" gap={12} style={{ pointerEvents: 'none' }}>
                <Dropzone.Accept>
                  <ThemeIcon size={52} radius="xl" color="blue" variant="light">
                    <IconUpload size={28} stroke={1.8} />
                  </ThemeIcon>
                </Dropzone.Accept>
                <Dropzone.Reject>
                  <ThemeIcon size={52} radius="xl" color="red" variant="light">
                    <IconX size={28} stroke={1.8} />
                  </ThemeIcon>
                </Dropzone.Reject>
                <Dropzone.Idle>
                  <ThemeIcon size={52} radius="xl" color="blue" variant="light">
                    <IconFileTypePdf size={28} stroke={1.8} />
                  </ThemeIcon>
                </Dropzone.Idle>

                <Box ta="center">
                  <Text size="md" fw={600} style={{ color: 'var(--mi-text)' }}>
                    {isUploading
                      ? 'Uploading...'
                      : 'Drag & drop a PDF file here'}
                  </Text>
                  <Text size="sm" c="dimmed" mt={4}>
                    {isUploading
                      ? 'Please wait while the chart is being uploaded and processed'
                      : 'or click to browse. Max file size: 100MB'}
                  </Text>
                </Box>

                {isError && (
                  <Text size="sm" c="red" fw={500}>
                    Upload failed. Please try again.
                  </Text>
                )}
              </Stack>
            </Dropzone>

            {/* Upload Progress */}
            {isUploading && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                transition={{ duration: 0.2 }}
              >
                <Box mt={16}>
                  <Group justify="space-between" mb={6}>
                    <Text size="xs" fw={500} c="dimmed">Uploading</Text>
                    <Text size="xs" fw={500} c="dimmed">Processing will begin automatically</Text>
                  </Group>
                  <Progress
                    value={100}
                    color="blue"
                    size="sm"
                    radius="xl"
                    animated
                    striped
                  />
                </Box>
              </motion.div>
            )}

            {/* File type hints */}
            <Group mt={20} gap={8} justify="center">
              <Badge variant="light" color="gray" size="sm" radius="md">
                PDF only
              </Badge>
              <Badge variant="light" color="gray" size="sm" radius="md">
                Max 100MB
              </Badge>
              <Badge variant="light" color="gray" size="sm" radius="md">
                Medical charts
              </Badge>
            </Group>
          </motion.div>
        )}
      </AnimatePresence>
    </Modal>
  );
}
