import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

class MemoryStorage {
  constructor() {
    this._data = new Map();
  }

  getItem(key) {
    return this._data.has(String(key)) ? this._data.get(String(key)) : null;
  }

  setItem(key, value) {
    this._data.set(String(key), String(value));
  }

  removeItem(key) {
    this._data.delete(String(key));
  }

  clear() {
    this._data.clear();
  }

  key(index) {
    return [...this._data.keys()][index] ?? null;
  }

  get length() {
    return this._data.size;
  }
}

// Node 25 exposes a broken experimental `localStorage` global that shadows
// the jsdom one. Replace it with a working in-memory implementation.
if (typeof globalThis.localStorage?.getItem !== 'function') {
  Object.defineProperty(globalThis, 'localStorage', {
    value: new MemoryStorage(),
    writable: true,
    configurable: true,
  });
}

afterEach(() => {
  cleanup();
  localStorage.clear();
});
