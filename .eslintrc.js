// Legacy ESLint configuration (v8 format)
// TODO: Migrate to eslint.config.js format for ESLint v9+
module.exports = {
  parser: '@typescript-eslint/parser',
  parserOptions: {
    project: 'tsconfig.json',
    tsconfigRootDir: __dirname,
    sourceType: 'module',
    ecmaVersion: 2022,
  },
  plugins: ['@typescript-eslint'],
  extends: [
    'eslint:recommended',
    '@typescript-eslint/recommended',
    '@typescript-eslint/recommended-requiring-type-checking',
  ],
  root: true,
  env: {
    node: true,
    jest: true,
    es2022: true,
  },
  ignorePatterns: ['.eslintrc.js', 'dist/', 'node_modules/', 'coverage/'],
  rules: {
    '@typescript-eslint/interface-name-prefix': 'off',
    '@typescript-eslint/explicit-function-return-type': 'error',
    '@typescript-eslint/explicit-module-boundary-types': 'error',
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/no-unused-vars': 'error',
    '@typescript-eslint/prefer-const': 'error',
    '@typescript-eslint/no-var-requires': 'error',
    'prefer-const': 'error',
    'no-var': 'error',
    'no-console': 'warn',
    'no-debugger': 'error',
    // Clean Architecture enforcement rules
    'no-relative-import-paths/no-relative-import-paths': 'off', // We'll add this plugin later if needed
  },
  overrides: [
    {
      files: ['*.test.ts', '*.spec.ts'],
      rules: {
        'no-console': 'off', // Allow console in tests
      },
    },
  ],
};
