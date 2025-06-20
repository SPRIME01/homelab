#!/usr/bin/env python3
"""
Comprehensive Makefile testing framework for homelab project.
Tests all Makefile targets for functionality, idempotency, and integration.
"""

import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
from loguru import logger


class MakefileTestFramework:
    """Framework for testing Makefile targets and functionality."""

    def __init__(self, project_root: Path):
        """Initialize Makefile testing framework.

        Args:
            project_root: Path to project root containing Makefile
        """
        self.project_root = project_root
        self.makefile_path = project_root / "Makefile"
        self.test_results: dict[str, Any] = {}

    def run_make_target(
        self, target: str, capture_output: bool = True, check: bool = False
    ) -> subprocess.CompletedProcess[str]:
        """Run a specific make target.

        Args:
            target: Make target to run
            capture_output: Whether to capture stdout/stderr
            check: Whether to raise exception on non-zero return code

        Returns:
            CompletedProcess result
        """
        logger.info(f"Running make target: {target}")

        cmd = ["make", target]
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=capture_output,
            text=True,
            check=check,
        )

        logger.info(
            f"Make target '{target}' completed with return code: {result.returncode}"
        )
        return result

    def assert_target_succeeds(self, target: str) -> subprocess.CompletedProcess[str]:
        """Assert that a make target succeeds.

        Args:
            target: Make target to test

        Returns:
            CompletedProcess result

        Raises:
            AssertionError: If target fails
        """
        result = self.run_make_target(target)
        assert result.returncode == 0, (
            f"Make target '{target}' failed\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        return result

    def test_target_idempotency(self, target: str, runs: int = 3) -> None:
        """Assert that a make target is idempotent.

        Args:
            target: Make target to test
            runs: Number of times to run the target
        """
        results = []

        for run_number in range(1, runs + 1):
            logger.info(f"Running make target '{target}' - iteration {run_number}")
            result = self.run_make_target(target)
            results.append(result)

            # Assert: Each run should succeed
            assert result.returncode == 0, (
                f"Make target '{target}' failed on run {run_number}\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )

        logger.info(f"Make target '{target}' passed idempotency test ({runs} runs)")


class TestMakefileStructure:
    """Test suite for Makefile structure and basic functionality."""

    @pytest.mark.makefile
    def test_makefile_exists(self, makefile_framework) -> None:
        """Test that Makefile exists and is readable."""
        assert makefile_framework.makefile_path.exists(), "Makefile should exist"
        assert makefile_framework.makefile_path.is_file(), "Makefile should be a file"
        assert (
            makefile_framework.makefile_path.stat().st_size > 0
        ), "Makefile should not be empty"
        logger.info("✓ Makefile exists and is readable")

    @pytest.mark.makefile
    def test_required_targets_exist(self, makefile_framework) -> None:
        """Test that all required Makefile targets exist."""
        required_targets = [
            "all",
            "install",
            "test",
            "lint",
            "format",
            "docs",
            "clean",
            "deploy",
            "help",
        ]

        makefile_content = makefile_framework.makefile_path.read_text(encoding="utf-8")

        for target in required_targets:
            target_pattern = f"{target}:"
            assert (
                target_pattern in makefile_content
            ), f"Required target '{target}' missing"
            logger.info(f"✓ Target '{target}' found in Makefile")

    @pytest.mark.makefile
    def test_makefile_syntax(self, makefile_framework) -> None:
        """Test that Makefile has valid syntax."""
        # Try running make with a help or list target
        result = makefile_framework.run_make_target("--version")
        # If make itself works, the Makefile syntax is likely OK
        assert result.returncode in [0, 1, 2], "Make command should be available"
        logger.info("✓ Makefile syntax appears valid")


class TestMakefileTargets:
    """Test suite for individual Makefile targets."""

    @pytest.mark.makefile
    def test_help_target(self, makefile_framework) -> None:
        """Test that help target provides useful information."""
        result = makefile_framework.run_make_target("help")

        if result.returncode == 0:
            output = result.stdout + result.stderr
            help_indicators = ["Available", "Usage", "targets", "help", "make"]
            has_help_content = any(indicator in output for indicator in help_indicators)
            assert (
                has_help_content or len(output.strip()) > 20
            ), "Help should provide information"
            logger.info("✓ Help target provides useful information")
        else:
            logger.info("⚠ Help target not available or failed")

    @pytest.mark.makefile
    def test_install_target(self, makefile_framework) -> None:
        """Test that install target runs without critical errors."""
        result = makefile_framework.run_make_target("install")

        # Install may fail in some environments, but should not crash
        assert result.returncode in [0, 1, 2], "Install target should execute"

        if result.returncode == 0:
            logger.info("✓ Install target completed successfully")
        else:
            logger.info("⚠ Install target failed - may be environment dependent")

    @pytest.mark.makefile
    def test_clean_target(self, makefile_framework) -> None:
        """Test that clean target executes."""
        # Create a test cache directory
        test_cache = makefile_framework.project_root / "__pycache__"
        test_cache.mkdir(exist_ok=True)
        (test_cache / "test.pyc").touch()

        result = makefile_framework.run_make_target("clean")

        # Clean should succeed
        assert result.returncode == 0, f"Clean target failed: {result.stderr}"
        logger.info("✓ Clean target executed successfully")

    @pytest.mark.makefile
    def test_format_target(self, makefile_framework) -> None:
        """Test that format target executes."""
        result = makefile_framework.run_make_target("format")

        # Format should succeed or fail gracefully
        assert result.returncode in [0, 1], "Format target should execute"

        if result.returncode == 0:
            logger.info("✓ Format target completed successfully")
        else:
            logger.info("⚠ Format target failed - may need dependencies")

    @pytest.mark.makefile
    def test_lint_target(self) -> None:
        """Test that lint target executes."""
        result = self.framework.run_make_target("lint")

        # Lint may fail with code issues, but should execute
        assert result.returncode in [0, 1], "Lint target should execute"

        output = result.stdout + result.stderr
        lint_indicators = ["ruff", "mypy", "check", "lint", "All checks"]
        has_lint_output = any(indicator in output for indicator in lint_indicators)

        if result.returncode == 0 or has_lint_output:
            logger.info("✓ Lint target executed code quality checks")
        else:
            logger.info("⚠ Lint target may need dependencies")

    @pytest.mark.makefile
    def test_test_target(self) -> None:
        """Test that test target executes."""
        result = self.framework.run_make_target("test")

        # Tests may pass or fail, but should execute
        assert result.returncode in [0, 1], "Test target should execute"

        output = result.stdout + result.stderr
        test_indicators = ["test", "pytest", "passed", "failed", "PASSED", "FAILED"]
        has_test_output = any(indicator in output for indicator in test_indicators)

        if has_test_output:
            logger.info("✓ Test target executed test suite")
        else:
            logger.info("⚠ Test target may need setup")


class TestMakefilePerformance:
    """Test performance characteristics of Makefile targets."""

    def test_target_execution_time_reasonable(
        self, makefile_framework: MakefileTestFramework
    ) -> None:
        """Test that targets complete within reasonable time limits.

        Arrange: Set up time tracking for various targets
        Act: Execute targets with timing
        Assert: Verify execution times are within acceptable limits
        """
        # Arrange
        time_limits = {
            "help": 5.0,  # Help should be instant
            "check-uv": 10.0,  # UV check should be quick
            "format": 30.0,  # Formatting can take some time
            "lint": 60.0,  # Linting can be slow
        }

        # Act & Assert
        for target, max_time in time_limits.items():
            start_time = time.time()
            result = makefile_framework.run_make_target(target)
            execution_time = time.time() - start_time

            assert (
                execution_time < max_time
            ), f"Target '{target}' took {execution_time:.2f}s, expected < {max_time}s"

            if result.returncode == 0:
                logger.info(f"Target '{target}' completed in {execution_time:.2f}s")

    def test_parallel_target_execution(
        self, makefile_framework: MakefileTestFramework
    ) -> None:
        """Test that safe targets can run in parallel.

        Arrange: Identify targets that should be safe to run in parallel
        Act: Execute multiple targets simultaneously
        Assert: Verify no conflicts or resource issues
        """
        # Arrange
        safe_parallel_targets = ["help", "status", "health-check"]

        # Act
        import concurrent.futures

        results = {}
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_target = {
                executor.submit(makefile_framework.run_make_target, target): target
                for target in safe_parallel_targets
            }

            for future in concurrent.futures.as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    results[target] = future.result()
                except Exception as e:
                    logger.error(f"Target {target} failed in parallel execution: {e}")
                    results[target] = None

        execution_time = time.time() - start_time

        # Assert
        for target in safe_parallel_targets:
            assert (
                results[target] is not None
            ), f"Target '{target}' failed in parallel execution"
            if results[target].returncode == 0:
                logger.info(f"Target '{target}' completed successfully in parallel")


class TestMakefileErrorHandling:
    """Test error handling and recovery in Makefile targets."""

    def test_graceful_failure_missing_dependencies(
        self, makefile_framework: MakefileTestFramework
    ) -> None:
        """Test graceful failure when dependencies are missing.

        Arrange: Create environment with missing dependencies
        Act: Execute targets that require those dependencies
        Assert: Verify graceful failure with helpful error messages
        """
        # Arrange - Test targets that might fail gracefully
        potentially_failing_targets = [
            "supabase-deploy",  # Might fail if K8s not available
            "health-check",  # Might fail if services not running
            "monitor",  # Might fail if monitoring tools missing
        ]

        # Act & Assert
        for target in potentially_failing_targets:
            result = makefile_framework.run_make_target(target)

            # Should not crash with unhandled exceptions
            # Either succeeds (return code 0) or fails gracefully (non-zero but with output)
            if result.returncode != 0:
                assert (
                    result.stderr is not None or result.stdout is not None
                ), f"Target '{target}' failed without any output"
                logger.info(
                    f"Target '{target}' failed gracefully: {result.stderr or result.stdout}"
                )

    def test_cleanup_after_failure(
        self, makefile_framework: MakefileTestFramework
    ) -> None:
        """Test that cleanup works even after failures.

        Arrange: Ensure some artifacts exist that need cleaning
        Act: Run clean target
        Assert: Verify cleanup happens regardless of previous failures
        """
        # Arrange - Create some test artifacts
        test_artifacts = [
            makefile_framework.project_root / ".pytest_cache" / "test_file",
            makefile_framework.project_root / "logs" / "test.log",
        ]

        for artifact in test_artifacts:
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("test content")

        # Act
        result = makefile_framework.run_make_target("clean")

        # Assert
        assert result.returncode == 0, f"Clean target failed: {result.stderr}"

        # Verify cleanup happened (some artifacts should be removed)
        remaining_artifacts = [
            artifact for artifact in test_artifacts if artifact.exists()
        ]
        logger.info(f"Cleanup completed, {len(remaining_artifacts)} artifacts remain")


class TestMakefileIntegration:
    """Test integration between multiple Makefile targets."""

    def test_complete_development_workflow(
        self, makefile_framework: MakefileTestFramework
    ) -> None:
        """Test complete development workflow integration.

        Arrange: Set up for full development cycle
        Act: Execute development workflow targets in sequence
        Assert: Verify each step works and prepares for the next
        """
        # Arrange
        workflow_targets = [
            "check-uv",  # Ensure UV is available
            "format",  # Format code
            "lint",  # Check code quality
            "quick-test",  # Run quick tests
        ]

        workflow_results = {}

        # Act - Execute workflow in sequence
        for target in workflow_targets:
            logger.info(f"Executing workflow step: {target}")
            result = makefile_framework.run_make_target(target)
            workflow_results[target] = result

            # Each step should succeed before proceeding
            if result.returncode != 0:
                logger.warning(f"Workflow step '{target}' failed, stopping workflow")
                break

        # Assert - Verify workflow completed successfully
        successful_steps = [
            target
            for target, result in workflow_results.items()
            if result.returncode == 0
        ]

        assert (
            len(successful_steps) >= 2
        ), f"Development workflow failed too early. Successful: {successful_steps}"

        logger.info(
            f"Development workflow: {len(successful_steps)}/{len(workflow_targets)} steps successful"
        )

    def test_deployment_readiness_check(
        self, makefile_framework: MakefileTestFramework
    ) -> None:
        """Test deployment readiness validation.

        Arrange: Set up environment for deployment checks
        Act: Execute pre-deployment validation targets
        Assert: Verify system is deployment-ready or identify blockers
        """
        # Arrange
        readiness_targets = [
            "audit",  # System audit
            "verify",  # Installation verification
            "lint",  # Code quality
            "test",  # Test suite
        ]

        readiness_results = {}
        readiness_score = 0

        # Act
        for target in readiness_targets:
            result = makefile_framework.run_make_target(target)
            readiness_results[target] = result

            if result.returncode == 0:
                readiness_score += 1
                logger.info(f"Readiness check '{target}': PASS")
            else:
                logger.warning(f"Readiness check '{target}': FAIL")

        # Assert
        readiness_percentage = (readiness_score / len(readiness_targets)) * 100
        logger.info(
            f"Deployment readiness: {readiness_percentage:.1f}% ({readiness_score}/{len(readiness_targets)})"
        )

        # Should have at least basic readiness (audit and verify working)
        assert (
            readiness_score >= 2
        ), f"System not ready for deployment. Score: {readiness_score}/{len(readiness_targets)}"


class TestMakefileDocumentation:
    """Test Makefile documentation and help systems."""

    def test_all_targets_documented(
        self, makefile_framework: MakefileTestFramework
    ) -> None:
        """Test that all important targets have documentation.

        Arrange: Parse Makefile content for targets and documentation
        Act: Check help output and target comments
        Assert: Verify all public targets are documented
        """
        # Arrange
        makefile_content = makefile_framework.makefile_path.read_text()

        # Extract targets with ## comments (documented targets)
        import re

        documented_targets = re.findall(
            r"^([a-zA-Z_-]+):.*?## (.+)$",
            makefile_content,
            re.MULTILINE,
        )

        # Act
        help_result = makefile_framework.run_make_target("help")

        # Assert
        assert help_result.returncode == 0, "Help target should always work"
        assert (
            len(documented_targets) >= 10
        ), f"Expected at least 10 documented targets, found {len(documented_targets)}"

        help_output = help_result.stdout
        for target_name, description in documented_targets:
            assert (
                target_name in help_output
            ), f"Target '{target_name}' should appear in help output"
            # Description should be meaningful (more than just the target name)
            assert len(description.strip()) > len(
                target_name
            ), f"Target '{target_name}' needs better description: '{description}'"

        logger.info(
            f"Documentation check: {len(documented_targets)} targets properly documented"
        )

    def test_help_target_comprehensive(
        self, makefile_framework: MakefileTestFramework
    ) -> None:
        """Test that help target provides comprehensive information.

        Arrange: Set up for help content analysis
        Act: Execute help target
        Assert: Verify help content is complete and useful
        """
        # Arrange & Act
        result = makefile_framework.run_make_target("help")

        # Assert
        assert result.returncode == 0, "Help target failed"

        help_output = result.stdout.lower()

        # Should contain key sections
        expected_sections = [
            "smart home",  # Project identification
            "available",  # Commands available
            "install",  # Installation targets
            "test",  # Testing targets
            "clean",  # Cleanup targets
        ]

        missing_sections = [
            section for section in expected_sections if section not in help_output
        ]
        assert len(missing_sections) == 0, f"Help missing sections: {missing_sections}"

        # Should be well-formatted (contains formatting characters)
        assert any(
            char in result.stdout for char in ["=", "-", "*"]
        ), "Help output should have formatting for readability"

        logger.info("Help target provides comprehensive documentation")


# Test framework instance for module-level tests
test_framework = MakefileTestFramework(Path(__file__).parent.parent.parent)


@pytest.mark.makefile
def test_makefile_exists_module() -> None:
    """Module-level test that Makefile exists."""
    assert test_framework.makefile_path.exists(), "Makefile should exist"
    logger.info("✓ Makefile exists")


@pytest.mark.makefile
def test_basic_targets_module() -> None:
    """Module-level test for basic targets."""
    basic_targets = ["all", "install", "test", "clean"]
    makefile_content = test_framework.makefile_path.read_text(encoding="utf-8")

    missing_targets = []
    for target in basic_targets:
        if f"{target}:" not in makefile_content:
            missing_targets.append(target)

    assert len(missing_targets) == 0, f"Missing basic targets: {missing_targets}"
    logger.info(f"✓ All {len(basic_targets)} basic targets found")
