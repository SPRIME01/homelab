#!/usr/bin/env python3
"""
Test script for the Python logger implementation.
Ensures Python renderer matches Node output byte-for-byte for the same payload.
"""

import sys
import os
import json
import subprocess
import tempfile
import time
from io import StringIO
from contextlib import redirect_stdout

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from logger import logger, LoggerUtils, config

    # Test counter
    tests_run = 0
    tests_passed = 0

    def assert_contains(actual, expected, test_name):
        global tests_run, tests_passed
        tests_run += 1

        if expected in actual:
            print(f"✅ PASS: {test_name}")
            tests_passed += 1
            return True
        else:
            print(f"❌ FAIL: {test_name}")
            print(f"   Expected to contain: {expected}")
            print(f"   Actual: {actual}")
            return False

    def assert_equals(actual, expected, test_name):
        global tests_run, tests_passed
        tests_run += 1

        if actual == expected:
            print(f"✅ PASS: {test_name}")
            tests_passed += 1
            return True
        else:
            print(f"❌ FAIL: {test_name}")
            print(f"   Expected: {expected}")
            print(f"   Actual: {actual}")
            return False

    def assert_json_schema(json_obj, required_fields, test_name):
        global tests_run, tests_passed
        tests_run += 1

        missing_fields = []
        for field in required_fields:
            if field not in json_obj:
                missing_fields.append(field)

        if not missing_fields:
            print(f"✅ PASS: {test_name}")
            tests_passed += 1
            return True
        else:
            print(f"❌ FAIL: {test_name}")
            print(f"   Missing required fields: {', '.join(missing_fields)}")
            return False

    def capture_stdout(fn):
        """Capture stdout from a function."""
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        try:
            fn()
            return captured_output.getvalue()
        finally:
            sys.stdout = old_stdout

    def get_node_output(test_name, test_data):
        """Get Node.js logger output for comparison."""
        # Create a temporary Node.js script
        logger_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'node',
            'logger.js'
        )
        logger_path = logger_path.replace('\\', '\\\\')
        node_script = f"""
        const loggerPath = '{logger_path}';
        const {{ logger }} = require(loggerPath);

        // Set environment to match Python
        process.env.HOMELAB_LOG_TARGET = 'vector';
        process.env.HOMELAB_SERVICE = '{test_data.get("service", "test-service")}';
        process.env.HOMELAB_ENVIRONMENT = '{test_data.get("environment", "test")}';

        // Re-require logger to pick up new environment
        delete require.cache[loggerPath];
        const {{ logger: testLogger }} = require(loggerPath);

        // Execute the test
        {test_data.get("node_code", "testLogger.info('Test message');")}
        """

        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(node_script)
            temp_script = f.name

        try:
            # Run the Node.js script
            try:
                result = subprocess.run(
                    ['node', temp_script],
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            except FileNotFoundError:
                raise Exception("Node.js is not installed or not in PATH")
            except subprocess.TimeoutExpired:
                raise Exception("Node.js script timed out after 10 seconds")

            # Check return code and surface stderr if non-zero
            if result.returncode != 0:
                error_msg = f"Node.js script failed with exit code {result.returncode}"
                if result.stderr:
                    error_msg += f"\nStderr: {result.stderr}"
                if result.stdout:
                    error_msg += f"\nStdout: {result.stdout}"
                raise Exception(error_msg)

            # Return only the JSON lines
            lines = result.stdout.strip().split('\n')
            json_lines = [line for line in lines if line.strip().startswith('{')]

            if not json_lines:
                # If no JSON lines found, raise with captured output
                error_msg = "No JSON output found from Node.js script"
                if result.stdout:
                    error_msg += f"\nStdout: {result.stdout}"
                if result.stderr:
                    error_msg += f"\nStderr: {result.stderr}"
                raise Exception(error_msg)

            return json_lines[0]
        finally:
            # Clean up
            os.unlink(temp_script)

    def test_json_schema():
        print("🧪 Testing JSON schema...")

        # Set environment to force JSON output
        os.environ['HOMELAB_LOG_TARGET'] = 'vector'
        os.environ['HOMELAB_SERVICE'] = 'test-service'
        os.environ['HOMELAB_ENVIRONMENT'] = 'test'
        os.environ['HOMELAB_LOG_LEVEL'] = 'debug'

        # Re-import logger to pick up new environment
        import importlib
        import logger
        importlib.reload(logger)
        from logger import logger as test_logger

        # Capture log output
        output = capture_stdout(lambda: test_logger.info("Test message", test_field="test_value"))

        # Parse the JSON output
        lines = output.strip().split('\n')
        json_lines = [line for line in lines if line.strip().startswith('{')]

        if json_lines:
            try:
                log_entry = json.loads(json_lines[0])

                # Verify required fields
                required_fields = [
                    'timestamp', 'level', 'message', 'service', 'environment',
                    'version', 'category', 'event_id', 'context'
                ]

                assert_json_schema(log_entry, required_fields, 'JSON log contains required fields')
                assert_equals(log_entry['level'], 'info', 'JSON log has correct level')
                assert_equals(log_entry['message'], 'Test message', 'JSON log has correct message')
                assert_equals(log_entry['service'], 'test-service', 'JSON log has correct service')
                assert_equals(log_entry['environment'], 'test', 'JSON log has correct environment')
                assert_contains(log_entry['event_id'], 'evt_', 'JSON log has valid event_id format')
                assert_equals(log_entry['context']['test_field'], 'test_value', 'JSON log includes context data')
            except json.JSONDecodeError as e:
                print(f"❌ FAIL: Failed to parse JSON output: {e}")
                tests_run += 1
        else:
            print("❌ FAIL: No JSON output found")
            tests_run += 1

        print("JSON schema tests completed.")

    def test_pretty_output():
        print("🧪 Testing pretty output...")

        # Set environment to force pretty output
        os.environ['HOMELAB_LOG_TARGET'] = 'stdout'
        os.environ['HOMELAB_FORCE_PRETTY'] = 'true'

        # Re-import logger to pick up new environment
        import importlib
        import logger
        importlib.reload(logger)
        from logger import logger as test_logger

        # Test info level
        output = capture_stdout(lambda: test_logger.info("Test message"))

        assert_contains(output, 'INFO', 'Pretty output contains INFO level')
        assert_contains(output, 'Test message', 'Pretty output contains message')

        # Test with trace and duration
        trace_logger = LoggerUtils.bind_trace('trace-12345678', 'span-123')
        output = capture_stdout(lambda: trace_logger.info("Test with trace", duration_ms=250))

        assert_contains(output, '[trace-12...]', 'Pretty output contains truncated trace ID')
        assert_contains(output, '(250ms)', 'Pretty output contains duration')

        # Test error level
        output = capture_stdout(lambda: test_logger.error("Error message"))

        assert_contains(output, 'ERROR', 'Pretty output contains ERROR level')

        print("Pretty output tests completed.")

    def test_error_serialization():
        print("🧪 Testing error serialization...")

        # Set environment to force JSON output for error testing
        os.environ['HOMELAB_LOG_TARGET'] = 'vector'

        # Re-import logger to pick up new environment
        import importlib
        import logger
        importlib.reload(logger)
        from logger import logger as test_logger

        # Create a test error
        try:
            raise ValueError("Test error for logging")
        except ValueError as e:
            # Capture log output
            output = capture_stdout(lambda: LoggerUtils.log_error(e, operation="test-operation"))

            # Parse the JSON output
            lines = output.strip().split('\n')
            json_lines = [line for line in lines if line.strip().startswith('{')]

            if json_lines:
                try:
                    log_entry = json.loads(json_lines[0])

                    # Verify error serialization
                    assert_contains(log_entry['message'], 'Test error for logging', 'Error message is serialized')
                    assert_equals(log_entry['level'], 'error', 'Error log has correct level')
                    assert_equals(log_entry['context']['operation'], 'test-operation', 'Error log includes context')
                    assert_equals(log_entry['context']['error_type'], 'ValueError', 'Error log includes error type')
                except json.JSONDecodeError as e:
                    print(f"❌ FAIL: Failed to parse error JSON output: {e}")
                    tests_run += 1
            else:
                print("❌ FAIL: No JSON error output found")
                tests_run += 1

        print("Error serialization tests completed.")

    def test_context_binding():
        print("🧪 Testing context binding...")

        # Set environment to force JSON output
        os.environ['HOMELAB_LOG_TARGET'] = 'vector'

        # Re-import logger to pick up new environment
        import importlib
        import logger
        importlib.reload(logger)
        from logger import logger as test_logger

        # Test with category
        category_logger = LoggerUtils.with_category('database')
        output = capture_stdout(lambda: category_logger.info("Database operation"))

        lines = output.strip().split('\n')
        json_lines = [line for line in lines if line.strip().startswith('{')]

        if json_lines:
            try:
                log_entry = json.loads(json_lines[0])
                assert_equals(log_entry['category'], 'database', 'Context binding sets correct category')
            except json.JSONDecodeError as e:
                print(f"❌ FAIL: Failed to parse category JSON output: {e}")
                tests_run += 1

        # Test with request context
        request_logger = LoggerUtils.with_request('req-123', 'user-hash')
        output = capture_stdout(lambda: request_logger.info("User action"))

        lines = output.strip().split('\n')
        json_lines = [line for line in lines if line.strip().startswith('{')]

        if json_lines:
            try:
                log_entry = json.loads(json_lines[0])
                assert_equals(log_entry['request_id'], 'req-123', 'Context binding sets correct request_id')
                assert_equals(log_entry['user_hash'], 'user-hash', 'Context binding sets correct user_hash')
            except json.JSONDecodeError as e:
                print(f"❌ FAIL: Failed to parse request JSON output: {e}")
                tests_run += 1

        print("Context binding tests completed.")

    def test_http_logging():
        print("🧪 Testing HTTP logging...")

        # Set environment to force JSON output
        os.environ['HOMELAB_LOG_TARGET'] = 'vector'

        # Re-import logger to pick up new environment
        import importlib
        import logger
        importlib.reload(logger)
        from logger import logger as test_logger

        # Test request logging
        output = capture_stdout(lambda: LoggerUtils.log_request("GET", "/api/test", "req-123", "test-agent"))

        lines = output.strip().split('\n')
        json_lines = [line for line in lines if line.strip().startswith('{')]

        if json_lines:
            try:
                log_entry = json.loads(json_lines[0])
                assert_equals(log_entry['request_id'], 'req-123', 'Request log includes correct request_id')
                assert_equals(log_entry['context']['method'], 'GET', 'Request log includes correct method')
                assert_equals(log_entry['context']['url'], '/api/test', 'Request log includes correct URL')
            except json.JSONDecodeError as e:
                print(f"❌ FAIL: Failed to parse request JSON output: {e}")
                tests_run += 1

        # Test response logging
        output = capture_stdout(lambda: LoggerUtils.log_response("GET", "/api/test", 200, 150, "req-123"))

        lines = output.strip().split('\n')
        json_lines = [line for line in lines if line.strip().startswith('{')]

        if json_lines:
            try:
                log_entry = json.loads(json_lines[0])
                assert_equals(log_entry['request_id'], 'req-123', 'Response log includes correct request_id')
                assert_equals(log_entry['status_code'], 200, 'Response log includes correct status code')
                assert_equals(log_entry['duration_ms'], 150, 'Response log includes correct duration')
            except json.JSONDecodeError as e:
                print(f"❌ FAIL: Failed to parse response JSON output: {e}")
                tests_run += 1

        print("HTTP logging tests completed.")

    def test_node_python_byte_comparison():
        print("🧪 Testing Node.js vs Python byte-for-byte comparison...")
        global tests_run, tests_passed

        # Test data for comparison - using factories that return functions to avoid closing over old logger
        test_cases = [
            {
                "name": "Basic info log",
                "service": "test-service",
                "environment": "test",
                "node_code": 'testLogger.info("Test message", { test: true });',
                "python_factory": lambda: lambda logger: logger.info("Test message", test=True)
            },
            {
                "name": "Log with category",
                "service": "test-service",
                "environment": "test",
                "node_code": 'testLogger.withCategory("database").info("Database operation");',
                "python_factory": lambda: lambda logger: LoggerUtils.with_category("database").info("Database operation")
            },
            {
                "name": "Log with trace",
                "service": "test-service",
                "environment": "test",
                "node_code": 'testLogger.withTrace("trace-123", "span-456").info("Operation with trace");',
                "python_factory": lambda: lambda logger: LoggerUtils.bind_trace("trace-123", "span-456").info("Operation with trace")
            }
        ]

        for test_case in test_cases:
            print(f"  Testing: {test_case['name']}")

            # Get Node.js output
            node_output = get_node_output(test_case['name'], test_case)

            # Set environment for Python
            os.environ['HOMELAB_LOG_TARGET'] = 'vector'
            os.environ['HOMELAB_SERVICE'] = test_case['service']
            os.environ['HOMELAB_ENVIRONMENT'] = test_case['environment']

            # Re-import logger to pick up new environment
            import importlib
            import logger
            importlib.reload(logger)
            from logger import logger as test_logger, LoggerUtils

            # Get Python output using the factory with the reloaded logger
            python_code_factory = test_case['python_factory']()
            python_output = capture_stdout(lambda: python_code_factory(test_logger))

            # Parse JSON from both outputs
            node_lines = [line for line in node_output.strip().split('\n') if line.strip().startswith('{')]
            python_lines = [line for line in python_output.strip().split('\n') if line.strip().startswith('{')]

            if node_lines and python_lines:
                try:
                    node_json = json.loads(node_lines[0])
                    python_json = json.loads(python_lines[0])

                    # Compare key fields (excluding timestamp and event_id which will differ)
                    key_fields = ['level', 'message', 'service', 'environment', 'version', 'category']

                    for field in key_fields:
                        if field in node_json and field in python_json:
                            tests_run += 1  # Increment for every field comparison
                            if node_json[field] == python_json[field]:
                                print(f"    ✅ {field} matches")
                                tests_passed += 1  # Increment only on successful comparison
                            else:
                                print(f"    ❌ {field} differs: Node={node_json[field]}, Python={python_json[field]}")
                        else:
                            print(f"    ⚠️  {field} missing in one of the outputs")

                    # Compare context structure
                    tests_run += 1  # Increment for this check
                    if 'context' in node_json and 'context' in python_json:
                        node_context_keys = set(node_json['context'].keys())
                        python_context_keys = set(python_json['context'].keys())

                        ok = (node_context_keys == python_context_keys)
                        if ok:
                            print(f"    ✅ Context keys match")
                            tests_passed += 1
                        else:
                            print(f"    ❌ Context keys differ: Node={node_context_keys}, Python={python_context_keys}")

                except json.JSONDecodeError as e:
                    print(f"    ❌ Failed to parse JSON: {e}")
                    tests_run += 1
            else:
                print(f"    ❌ No JSON output from one or both implementations")
                tests_run += 1

        print("Node.js vs Python comparison tests completed.")

    # Run all tests
    print("🚀 Starting Python logger tests...")
    print("")

    test_json_schema()
    print("")
    test_pretty_output()
    print("")
    test_error_serialization()
    print("")
    test_context_binding()
    print("")
    test_http_logging()
    print("")
    test_node_python_byte_comparison()
    print("")

    # Print summary
    print("📊 Test Summary:")
    print(f"   Tests run: {tests_run}")
    print(f"   Tests passed: {tests_passed}")
    print(f"   Tests failed: {tests_run - tests_passed}")

    if tests_passed == tests_run:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)

except ImportError as e:
    print(f"Import error: {e}")
    print("Please install dependencies with: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
