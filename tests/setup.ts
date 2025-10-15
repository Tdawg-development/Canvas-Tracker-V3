/**
 * Jest Test Setup
 * 
 * Global setup for all tests in the Canvas Tracker V3 project
 */

import dotenv from 'dotenv';

// Load environment variables for tests
dotenv.config();

// Set test timeout defaults
jest.setTimeout(30000); // 30 seconds for Canvas API calls

// Global test utilities
global.console = {
  ...console,
  // Suppress console.log in tests unless needed
  log: process.env.NODE_ENV === 'test' && !process.env.VERBOSE_TESTS 
    ? jest.fn() 
    : console.log,
};

// Ensure Canvas credentials are available for integration tests
beforeAll(() => {
  if (process.env.NODE_ENV !== 'test') {
    console.warn('Tests should run with NODE_ENV=test');
  }
});

export {};