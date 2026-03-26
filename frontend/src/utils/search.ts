import React from 'react';

export function searchItems<T>(
  items: T[],
  query: string,
  keys: (keyof T)[],
): T[] {
  if (!query || query.trim().length === 0) return items;

  const normalizedQuery = query.toLowerCase().trim();
  const queryTerms = normalizedQuery.split(/\s+/);

  return items.filter((item) =>
    queryTerms.every((term) =>
      keys.some((key) => {
        const value = item[key];
        if (value === null || value === undefined) return false;
        return String(value).toLowerCase().includes(term);
      }),
    ),
  );
}

export function highlightText(
  text: string,
  query: string,
): React.ReactNode {
  if (!query || query.trim().length === 0) return text;

  const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escapedQuery})`, 'gi');
  const parts = text.split(regex);

  if (parts.length === 1) return text;

  return parts.map((part, index) => {
    if (part.toLowerCase() === query.toLowerCase()) {
      return React.createElement(
        'mark',
        {
          key: index,
          style: {
            backgroundColor: 'var(--mi-warning)',
            color: 'var(--mi-text)',
            padding: '0 2px',
            borderRadius: '2px',
          },
        },
        part,
      );
    }
    return part;
  });
}

export function fuzzyMatch(text: string, query: string): boolean {
  if (!query) return true;
  const normalizedText = text.toLowerCase();
  const normalizedQuery = query.toLowerCase();

  let queryIdx = 0;
  for (let i = 0; i < normalizedText.length && queryIdx < normalizedQuery.length; i++) {
    if (normalizedText[i] === normalizedQuery[queryIdx]) {
      queryIdx++;
    }
  }
  return queryIdx === normalizedQuery.length;
}

export function calculateRelevance(text: string, query: string): number {
  if (!query) return 0;
  const normalizedText = text.toLowerCase();
  const normalizedQuery = query.toLowerCase();

  if (normalizedText === normalizedQuery) return 100;
  if (normalizedText.startsWith(normalizedQuery)) return 90;
  if (normalizedText.includes(normalizedQuery)) return 70;

  const terms = normalizedQuery.split(/\s+/);
  const matchedTerms = terms.filter((term) => normalizedText.includes(term));
  return (matchedTerms.length / terms.length) * 50;
}
