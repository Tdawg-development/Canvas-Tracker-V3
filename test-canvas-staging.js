#!/usr/bin/env node

/**
 * Canvas API Staging Tests Runner
 * 
 * Quick script to run just the Canvas interface staging tests
 */

const { execSync } = require('child_process');
const path = require('path');

// Load environment variables
require('dotenv').config();

console.log('🧪 Canvas API Staging Integration Tests');
console.log('=====================================\n');

// Check for Canvas credentials
if (!process.env.CANVAS_URL || !process.env.CANVAS_TOKEN) {
  console.error('❌ Missing Canvas credentials!');
  console.error('Please ensure CANVAS_URL and CANVAS_TOKEN are set in your .env file');
  process.exit(1);
}

console.log('✅ Canvas credentials found');
console.log(`📍 Canvas URL: ${process.env.CANVAS_URL}`);
console.log(`🔑 Token: ${process.env.CANVAS_TOKEN.substring(0, 10)}...`);
console.log('');

try {
  // Run Jest specifically for Canvas interface tests
  const command = 'npx jest canvas-interface/tests/api-staging-integration.test.ts --verbose --no-coverage';
  
  console.log('🚀 Running Canvas staging integration tests...');
  console.log(`Command: ${command}\n`);
  
  execSync(command, {
    stdio: 'inherit',
    cwd: process.cwd(),
    env: {
      ...process.env,
      NODE_ENV: 'test',
      VERBOSE_TESTS: 'true'
    }
  });
  
  console.log('\n🎉 Canvas staging tests completed successfully!');
  
} catch (error) {
  console.error('\n💥 Canvas staging tests failed:');
  console.error(error.message);
  
  console.log('\n🔧 Troubleshooting tips:');
  console.log('1. Ensure Canvas credentials are valid');
  console.log('2. Check network connectivity to Canvas');
  console.log('3. Verify course ID 7982015 is accessible');
  console.log('4. Check Canvas API rate limits');
  
  process.exit(1);
}