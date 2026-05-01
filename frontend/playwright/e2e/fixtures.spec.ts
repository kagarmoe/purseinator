import { test, expect } from '@playwright/test';
import { existsSync } from 'node:fs';
import { purseFixturePath, KNOWN_PURSES } from '../fixtures/purse-fixtures';

test('purseFixturePath returns path ending with the slug filename', () => {
  const p = purseFixturePath('tan-tote');
  expect(p).toMatch(/tan-tote\.png$/);
});

test('purseFixturePath file exists on disk', () => {
  const p = purseFixturePath('tan-tote');
  expect(existsSync(p)).toBe(true);
});

test('all 20 known purses exist on disk', () => {
  for (const name of KNOWN_PURSES) {
    const p = purseFixturePath(name);
    expect(existsSync(p)).toBe(true);
  }
});

test('KNOWN_PURSES has exactly 20 entries', () => {
  expect(KNOWN_PURSES.length).toBe(20);
});
