module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest',
  },
  roots: ['<rootDir>/src', '<rootDir>/tests', '<rootDir>/canvas-interface'],
  testMatch: [
    '**/__tests__/**/*.+(ts|tsx|js)',
    '**/*.(test|spec).+(ts|tsx|js)'
  ],
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    'canvas-interface/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!canvas-interface/**/*.d.ts',
    '!src/**/*.test.{ts,tsx}',
    '!canvas-interface/**/*.test.{ts,tsx}',
    '!src/**/*.spec.{ts,tsx}',
    '!canvas-interface/**/*.spec.{ts,tsx}',
    '!src/index.ts', // Entry point excluded from coverage
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  testPathIgnorePatterns: ['/node_modules/', '/dist/'],
  moduleNameMapper: {
    // Add path mappings if needed for Clean Architecture layers
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@interface/(.*)$': '<rootDir>/src/interface/$1',
    '^@application/(.*)$': '<rootDir>/src/application/$1',
    '^@domain/(.*)$': '<rootDir>/src/domain/$1',
    '^@infrastructure/(.*)$': '<rootDir>/src/infrastructure/$1',
    '^@shared/(.*)$': '<rootDir>/src/shared/$1',
  },
  // Clean Architecture testing strategy
  testPathIgnorePatterns: ['/node_modules/', '/dist/'],
  verbose: true,
  bail: false,
  maxWorkers: '50%',
};