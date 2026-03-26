import { useRef, useEffect, useCallback } from 'react';
import { Box, Text, ScrollArea, Tooltip } from '@mantine/core';
import { motion, AnimatePresence } from 'framer-motion';
import { Document, Page, pdfjs } from 'react-pdf';
import { usePDFStore } from '../../stores/pdfStore';

/* ========================================================================= */
/* Props                                                                      */
/* ========================================================================= */
interface PDFThumbnailsProps {
  pdfUrl: string;
  visible: boolean;
}

/* ========================================================================= */
/* Component                                                                  */
/* ========================================================================= */
export function PDFThumbnails({ pdfUrl, visible }: PDFThumbnailsProps) {
  const { currentPage, numPages, setCurrentPage } = usePDFStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLDivElement>(null);

  /* Scroll active thumbnail into view */
  useEffect(() => {
    if (visible && activeRef.current) {
      activeRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }
  }, [currentPage, visible]);

  const handlePageClick = useCallback(
    (page: number) => {
      setCurrentPage(page);
    },
    [setCurrentPage],
  );

  const pages = Array.from({ length: numPages }, (_, i) => i + 1);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 140, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
          style={{
            height: '100%',
            overflow: 'hidden',
            flexShrink: 0,
            borderRight: '1px solid var(--mi-border)',
            background: 'var(--mi-surface)',
          }}
        >
          <ScrollArea
            h="100%"
            type="scroll"
            scrollbarSize={6}
            ref={scrollRef}
          >
            <Box style={{ padding: '8px 6px' }}>
              <Document
                file={pdfUrl}
                loading={null}
                error={null}
              >
                {pages.map((pageNum) => {
                  const isActive = pageNum === currentPage;
                  return (
                    <Tooltip
                      key={pageNum}
                      label={`Page ${pageNum}`}
                      position="right"
                      offset={8}
                    >
                      <Box
                        ref={isActive ? activeRef : undefined}
                        onClick={() => handlePageClick(pageNum)}
                        style={{
                          position: 'relative',
                          marginBottom: 8,
                          borderRadius: 'var(--mi-radius-sm)',
                          overflow: 'hidden',
                          cursor: 'pointer',
                          border: isActive
                            ? '2px solid var(--mi-primary)'
                            : '2px solid transparent',
                          boxShadow: isActive
                            ? '0 0 0 3px color-mix(in srgb, var(--mi-primary) 20%, transparent)'
                            : 'var(--mi-shadow-sm)',
                          transition: 'all var(--mi-transition-fast)',
                          backgroundColor: 'var(--mi-background)',
                        }}
                      >
                        <Box
                          style={{
                            pointerEvents: 'none',
                            overflow: 'hidden',
                            borderRadius: 'var(--mi-radius-sm)',
                          }}
                        >
                          <Page
                            pageNumber={pageNum}
                            width={120}
                            renderTextLayer={false}
                            renderAnnotationLayer={false}
                            loading={
                              <Box
                                style={{
                                  width: 120,
                                  height: 160,
                                  background:
                                    'linear-gradient(90deg, var(--mi-surface-hover) 0%, var(--mi-surface) 50%, var(--mi-surface-hover) 100%)',
                                  backgroundSize: '200% 100%',
                                  animation: 'mi-shimmer 1.5s infinite',
                                }}
                              />
                            }
                          />
                        </Box>

                        {/* Page number label */}
                        <Box
                          style={{
                            position: 'absolute',
                            bottom: 4,
                            right: 4,
                            backgroundColor: isActive
                              ? 'var(--mi-primary)'
                              : 'rgba(0,0,0,0.6)',
                            color: '#FFFFFF',
                            fontSize: 10,
                            fontWeight: 600,
                            padding: '1px 6px',
                            borderRadius: 'var(--mi-radius-full)',
                            lineHeight: '16px',
                            transition: 'background-color var(--mi-transition-fast)',
                          }}
                        >
                          {pageNum}
                        </Box>
                      </Box>
                    </Tooltip>
                  );
                })}
              </Document>
            </Box>
          </ScrollArea>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
