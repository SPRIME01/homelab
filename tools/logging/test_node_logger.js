#!/usr/bin/env node

/**
 * Test script for the Node.js logger implementation
 * Verifies schema, pretty printing, and error serialization
 */

const { logger } = require('./node/logger');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Test counter
let testsRun = 0;
let testsPassed = 0;

// Helper functions for testing
function assertContains(actual, expected, testName) {
  testsRun++;
  if (actual.includes(expected)) {
    console.log(`✅ PASS: ${testName}`);
    testsPassed++;
    return true;
  } else {
    console.log(`❌ FAIL: ${testName}`);
    console.log(`   Expected to contain: ${expected}`);
    console.log(`   Actual: ${actual}`);
    return false;
  }
}

function assertEquals(actual, expected, testName) {
  testsRun++;
  if (actual === expected) {
    console.log(`✅ PASS: ${testName}`);
    testsPassed++;
    return true;
  } else {
    console.log(`❌ FAIL: ${testName}`);
    console.log(`   Expected: ${expected}`);
    console.log(`   Actual: ${actual}`);
    return false;
  }
}

function assertJsonSchema(jsonObj, requiredFields, testName) {
  testsRun++;
  let missingFields = [];

  for (const field of requiredFields) {
    if (!(field in jsonObj)) {
      missingFields.push(field);
    }
  }

  if (missingFields.length === 0) {
    console.log(`✅ PASS: ${testName}`);
    testsPassed++;
    return true;
  } else {
    console.log(`❌ FAIL: ${testName}`);
    console.log(`   Missing required fields: ${missingFields.join(', ')}`);
    return false;
  }
}

// Capture stdout for testing
function captureStdout(fn) {
  const originalWrite = process.stdout.write;
  let output = '';

  process.stdout.write = function(string) {
    output += string;
    return true;
  };

  try {
    fn();
  } finally {
    process.stdout.write = originalWrite;
  }

  return output;
}

// Test functions
function testJsonSchema() {
  console.log('🧪 Testing JSON schema...');

  // Set environment to force JSON output
  process.env.HOMELAB_LOG_TARGET = 'vector';
  process.env.HOMELAB_SERVICE = 'test-service';
  process.env.HOMELAB_ENVIRONMENT = 'test';
  process.env.HOMELAB_LOG_LEVEL = 'debug';

  // Re-require logger to pick up new environment
  delete require.cache[require.resolve('./node/logger')];
  const { logger: testLogger } = require('./node/logger');

  // Capture log output
  let output = captureStdout(() => {
    testLogger.info('Test message', { context: { test: true } });
  });

  // Parse the JSON output (may contain ANSI codes for pretty printing)
  const jsonLines = output.split('\n').filter(line => line.trim().startsWith('{'));
  if (jsonLines.length > 0) {
    try {
      const logEntry = JSON.parse(jsonLines[0]);

      // Verify required fields
      const requiredFields = [
        'timestamp', 'level', 'message', 'service', 'environment',
        'version', 'category', 'event_id', 'context'
      ];

      assertJsonSchema(logEntry, requiredFields, 'JSON log contains required fields');
      assertEquals(logEntry.level, 'info', 'JSON log has correct level');
      assertEquals(logEntry.message, 'Test message', 'JSON log has correct message');
      assertEquals(logEntry.service, 'test-service', 'JSON log has correct service');
      assertEquals(logEntry.environment, 'test', 'JSON log has correct environment');
      assertContains(logEntry.event_id, 'evt_', 'JSON log has valid event_id format');
      assertEquals(logEntry.context.test, true, 'JSON log includes context data');
    } catch (e) {
      console.log(`❌ FAIL: Failed to parse JSON output: ${e.message}`);
      testsRun++;
    }
  } else {
    console.log('❌ FAIL: No JSON output found');
    testsRun++;
  }

  console.log('JSON schema tests completed.');
}

function testPrettyPrinting() {
  console.log('🧪 Testing pretty printing...');

  // Set environment to force pretty output
  process.env.HOMELAB_LOG_TARGET = 'stdout';
  process.env.HOMELAB_FORCE_PRETTY = 'true';

  // Re-require logger to pick up new environment
  delete require.cache[require.resolve('./node/logger')];
  const { logger: testLogger } = require('./node/logger');

  // Test info level
  let output = captureStdout(() => {
    testLogger.info('Test message');
  });

  assertContains(output, 'INFO', 'Pretty output contains INFO level');
  assertContains(output, 'Test message', 'Pretty output contains message');

  // Test with trace and duration
  output = captureStdout(() => {
    const traceLogger = testLogger.withTrace('trace-12345678', 'span-123');
    traceLogger.info('Test with trace', { duration_ms: 250 });
  });

  assertContains(output, '[trace-12...]', 'Pretty output contains truncated trace ID');
  assertContains(output, '(250ms)', 'Pretty output contains duration');

  // Test error level
  output = captureStdout(() => {
    testLogger.error('Error message');
  });

  assertContains(output, 'ERROR', 'Pretty output contains ERROR level');

  console.log('Pretty printing tests completed.');
}

function testErrorSerialization() {
  console.log('🧪 Testing error serialization...');

  // Set environment to force JSON output for error testing
  process.env.HOMELAB_LOG_TARGET = 'vector';

  // Re-require logger to pick up new environment
  delete require.cache[require.resolve('./node/logger')];
  const { logger: testLogger } = require('./node/logger');

  // Create a test error with stack trace
  const testError = new Error('Test error for logging');
  testError.code = 'TEST_ERROR';
  testError.statusCode = 500;

  // Capture log output
  let output = captureStdout(() => {
    testLogger.logError(testError, { operation: 'test-operation' });
  });

  // Parse the JSON output
  const jsonLines = output.split('\n').filter(line => line.trim().startsWith('{'));
  if (jsonLines.length > 0) {
    try {
      const logEntry = JSON.parse(jsonLines[0]);

      // Verify error serialization
      assertContains(logEntry.message, 'Test error for logging', 'Error message is serialized');
      assertEquals(logEntry.level, 'error', 'Error log has correct level');
      assertEquals(logEntry.context.operation, 'test-operation', 'Error log includes context');

      if (logEntry.context.err) {
        const errorObj = logEntry.context.err;
        assertEquals(errorObj.message, 'Test error for logging', 'Error object has correct message');
        assertEquals(errorObj.code, 'TEST_ERROR', 'Error object includes code');
        assertEquals(errorObj.statusCode, 500, 'Error object includes statusCode');
        assertContains(JSON.stringify(errorObj), 'stack', 'Error object includes stack trace');
      } else {
        console.log('❌ FAIL: Error object not found in context');
        testsRun++;
      }
    } catch (e) {
      console.log(`❌ FAIL: Failed to parse error JSON output: ${e.message}`);
      testsRun++;
    }
  } else {
    console.log('❌ FAIL: No JSON error output found');
    testsRun++;
  }

  console.log('Error serialization tests completed.');
}

function testContextBinding() {
  console.log('🧪 Testing context binding...');

  // Set environment to force JSON output
  process.env.HOMELAB_LOG_TARGET = 'vector';

  // Re-require logger to pick up new environment
  delete require.cache[require.resolve('./node/logger')];
  const { logger: testLogger } = require('./node/logger');

  // Test with category
  const categoryLogger = testLogger.withCategory('database');
  let output = captureStdout(() => {
    categoryLogger.info('Database operation');
  });

  const jsonLines = output.split('\n').filter(line => line.trim().startsWith('{'));
  if (jsonLines.length > 0) {
    try {
      const logEntry = JSON.parse(jsonLines[0]);
      assertEquals(logEntry.category, 'database', 'Context binding sets correct category');
    } catch (e) {
      console.log(`❌ FAIL: Failed to parse category JSON output: ${e.message}`);
      testsRun++;
    }
  }

  // Test with request context
  const requestLogger = testLogger.withRequest('req-123', 'user-hash');
  output = captureStdout(() => {
    requestLogger.info('User action');
  });

  const jsonLines2 = output.split('\n').filter(line => line.trim().startsWith('{'));
  if (jsonLines2.length > 0) {
    try {
      const logEntry = JSON.parse(jsonLines2[0]);
      assertEquals(logEntry.request_id, 'req-123', 'Context binding sets correct request_id');
      assertEquals(logEntry.user_hash, 'user-hash', 'Context binding sets correct user_hash');
    } catch (e) {
      console.log(`❌ FAIL: Failed to parse request JSON output: ${e.message}`);
      testsRun++;
    }
  }

  console.log('Context binding tests completed.');
}

function testHttpLogging() {
  console.log('🧪 Testing HTTP logging...');

  // Set environment to force JSON output
  process.env.HOMELAB_LOG_TARGET = 'vector';

  // Re-require logger to pick up new environment
  delete require.cache[require.resolve('./node/logger')];
  const { logger: testLogger } = require('./node/logger');

  // Mock HTTP request
  const mockReq = {
    method: 'GET',
    url: '/api/test',
    headers: { 'user-agent': 'test-agent', 'x-request-id': 'req-123' },
    id: 'req-123'
  };

  // Mock HTTP response
  const mockRes = {
    statusCode: 200
  };

  // Test request logging
  let output = captureStdout(() => {
    testLogger.logRequest(mockReq);
  });

  const jsonLines = output.split('\n').filter(line => line.trim().startsWith('{'));
  if (jsonLines.length > 0) {
    try {
      const logEntry = JSON.parse(jsonLines[0]);
      assertEquals(logEntry.request_id, 'req-123', 'Request log includes correct request_id');
      assertEquals(logEntry.context.method, 'GET', 'Request log includes correct method');
      assertEquals(logEntry.context.url, '/api/test', 'Request log includes correct URL');
    } catch (e) {
      console.log(`❌ FAIL: Failed to parse request JSON output: ${e.message}`);
      testsRun++;
    }
  }

  // Test response logging
  output = captureStdout(() => {
    testLogger.logResponse(mockReq, mockRes, 150);
  });

  const jsonLines2 = output.split('\n').filter(line => line.trim().startsWith('{'));
  if (jsonLines2.length > 0) {
    try {
      const logEntry = JSON.parse(jsonLines2[0]);
      assertEquals(logEntry.request_id, 'req-123', 'Response log includes correct request_id');
      assertEquals(logEntry.status_code, 200, 'Response log includes correct status code');
      assertEquals(logEntry.duration_ms, 150, 'Response log includes correct duration');
    } catch (e) {
      console.log(`❌ FAIL: Failed to parse response JSON output: ${e.message}`);
      testsRun++;
    }
  }

  console.log('HTTP logging tests completed.');
}

// Run all tests
console.log('🚀 Starting Node.js logger tests...');
console.log('');

testJsonSchema();
console.log('');
testPrettyPrinting();
console.log('');
testErrorSerialization();
console.log('');
testContextBinding();
console.log('');
testHttpLogging();
console.log('');

// Print summary
console.log('📊 Test Summary:');
console.log(`   Tests run: ${testsRun}`);
console.log(`   Tests passed: ${testsPassed}`);
console.log(`   Tests failed: ${testsRun - testsPassed}`);

if (testsPassed === testsRun) {
  console.log('🎉 All tests passed!');
  process.exit(0);
} else {
  console.log('💥 Some tests failed!');
  process.exit(1);
}
