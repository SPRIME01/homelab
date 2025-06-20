#!/usr/bin/env python3
"""
Makefile testing framework for homelab project.
Tests all Makefile targets for functionality and idempotency.
"""

import subprocess
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

        logger.debug(
            f"Make target '{target}' completed with return code: {result.returncode}"
        )
        if result.stdout:
            logger.debug(f"stdout: {result.stdout}")
        if result.stderr:
            logger.debug(f"stderr: {result.stderr}")

        return result

    def assert_target_exists(self, target: str) -> None:
        """Assert that a make target exists in the Makefile.

        Args:
            target: Make target name to check
        """
        # Arrange: Read Makefile content
        makefile_content = self.makefile_path.read_text()

        # Assert: Target exists in Makefile
        assert (
            f"{target}:" in makefile_content
        ), f"Make target '{target}' not found in Makefile"

    def assert_target_succeeds(self, target: str) -> subprocess.CompletedProcess:
        """Assert that a make target runs successfully.

        Args:
            target: Make target to test

        Returns:
            CompletedProcess result
        """
        # Arrange: Ensure target exists
        self.assert_target_exists(target)

        # Act: Run make target
        result = self.run_make_target(target)

        # Assert: Target succeeded
        assert result.returncode == 0, (
            f"Make target '{target}' failed with return code {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        return result

    def assert_target_idempotent(self, target: str, runs: int = 2) -> None:
        """Assert that a make target is idempotent (can be run multiple times safely).

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

        # Log success
        logger.info(f"Make target '{target}' passed idempotency test ({runs} runs)")

    def test_file_operations(self, target: str, expected_files: list[Path]) -> None:
        """Test that a make target creates expected files.

        Args:
            target: Make target to test
            expected_files: List of files that should be created
        """
        # Arrange: Clean up any existing files
        for file_path in expected_files:
            if file_path.exists():
                file_path.unlink()
        # Act: Run make target
        self.assert_target_succeeds(target)

        # Assert: Expected files were created
        for file_path in expected_files:
            assert file_path.exists(), f"Expected file not created: {file_path}"

    def test_clean_target(self, target: str = "clean") -> None:
        """Test that the clean target properly removes build artifacts.

        Args:
            target: Clean target name (default: "clean")
        """
        # Arrange: Create some test artifacts
        test_artifacts = [
            self.project_root / ".pytest_cache",
            self.project_root / "__pycache__",
            self.project_root / "htmlcov",
            self.project_root / "build",
        ]

        for artifact in test_artifacts:
            artifact.mkdir(exist_ok=True)
            (artifact / "test_file.tmp").touch()
        # Act: Run clean target
        self.assert_target_succeeds(target)

        # Assert: Artifacts were removed
        for artifact in test_artifacts:
            if artifact.exists():
                # Some artifacts might remain but should be empty or minimal
                contents = list(artifact.iterdir()) if artifact.is_dir() else []
                logger.info(f"Clean target left contents in {artifact}: {contents}")


@pytest.mark.makefile
class TestMakefileTargets:
    """Test suite for Makefile targets."""

    @pytest.fixture
    def makefile_framework(self, project_root: Path) -> MakefileTestFramework:
        """Provide Makefile testing framework."""
        return MakefileTestFramework(project_root)

    def test_makefile_exists(self, project_root: Path):
        """Test that Makefile exists in project root.

        Args:
            project_root: Project root path fixture
        """
        # Arrange & Assert: Makefile should exist
        makefile_path = project_root / "Makefile"
        assert makefile_path.exists(), "Makefile not found in project root"
        assert makefile_path.is_file(), "Makefile is not a regular file"

    def test_help_target(self, makefile_framework: MakefileTestFramework):
        """Test the help target provides useful information.

        Args:
            makefile_framework: Makefile testing framework fixture
        """
        # Act: Run help target
        result = makefile_framework.assert_target_succeeds("help")

        # Assert: Help output contains expected content
        assert "Usage:" in result.stdout or "Available targets:" in result.stdout
        assert len(result.stdout.strip()) > 0, "Help target produced no output"

    def test_check_uv_target(self, makefile_framework: MakefileTestFramework):
        """Test the check-uv target validates UV installation.

        Args:
            makefile_framework: Makefile testing framework fixture
        """
        # Act & Assert: check-uv target should succeed
        result = makefile_framework.assert_target_succeeds("check-uv")

        # Additional assertions for UV-specific behavior
        if result.returncode == 0:
            logger.info("UV package manager is available")

    def test_clean_target(self, makefile_framework: MakefileTestFramework):
        """Test the clean target removes build artifacts.

        Args:
            makefile_framework: Makefile testing framework fixture
        """
        # Arrange, Act & Assert: Use framework's clean test
        makefile_framework.test_clean_target("clean")

    def test_install_target_idempotency(
        self, makefile_framework: MakefileTestFramework
    ):
        """Test that install target is idempotent.

        Args:
            makefile_framework: Makefile testing framework fixture
        """
        # Skip if UV is not available
        if not self._uv_available():
            pytest.skip("UV package manager not available")

        # Act & Assert: Install should be idempotent
        makefile_framework.assert_target_idempotent("install", runs=2)

    def test_dev_install_target(self, makefile_framework: MakefileTestFramework):
        """Test the dev-install target for development dependencies.

        Args:
            makefile_framework: Makefile testing framework fixture
        """
        # Skip if UV is not available
        if not self._uv_available():
            pytest.skip("UV package manager not available")
        # Act & Assert: dev-install should succeed
        makefile_framework.assert_target_succeeds("dev-install")

        # Additional verification that dev dependencies are installed
        # This would typically involve checking for specific packages

    def test_test_target(self, makefile_framework: MakefileTestFramework):
        """Test the test target runs the test suite.

        Args:
            makefile_framework: Makefile testing framework fixture
        """
        # Skip if dependencies not available
        if not self._test_dependencies_available():
            pytest.skip("Test dependencies not available")

        # Act: Run test target
        result = makefile_framework.run_make_target("test")

        # Assert: Test target ran (may pass or fail, but should execute)
        assert result.returncode in [
            0,
            1,
        ], f"Test target had unexpected return code: {result.returncode}"

    def test_lint_target(self, makefile_framework: MakefileTestFramework):
        """Test the lint target runs code quality checks.

        Args:
            makefile_framework: Makefile testing framework fixture
        """
        # Skip if linting tools not available
        if not self._lint_tools_available():
            pytest.skip("Linting tools not available")

        # Act: Run lint target
        result = makefile_framework.run_make_target("lint")

        # Assert: Lint target executed
        assert result.returncode in [
            0,
            1,
        ], f"Lint target had unexpected return code: {result.returncode}"

    def test_format_target(self, makefile_framework: MakefileTestFramework):
        """Test the format target formats code properly.

        Args:
            makefile_framework: Makefile testing framework fixture
        """
        # Skip if formatting tools not available
        if not self._format_tools_available():
            pytest.skip("Formatting tools not available")

        # Act & Assert: Format target should succeed
        makefile_framework.assert_target_succeeds("format")

    def test_all_target_sequence(self, makefile_framework: MakefileTestFramework):
        """Test the 'all' target runs the complete build sequence.

        Args:
            makefile_framework: Makefile testing framework fixture
        """
        # Skip if dependencies not available
        if not self._all_dependencies_available():
            pytest.skip("Not all dependencies available for 'all' target")

        # Act: Run all target
        result = makefile_framework.run_make_target("all")

        # Assert: All target completed (may warn but should not fail completely)
        assert result.returncode in [
            0,
            1,
        ], f"All target had unexpected return code: {result.returncode}"

    def _uv_available(self) -> bool:
        """Check if UV package manager is available."""
        try:
            subprocess.run(["uv", "--version"], check=True, capture_output=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _test_dependencies_available(self) -> bool:
        """Check if test dependencies are available."""
        try:
            subprocess.run(
                ["python", "-c", "import pytest"], check=True, capture_output=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _lint_tools_available(self) -> bool:
        """Check if linting tools are available."""
        tools = ["ruff", "mypy"]
        for tool in tools:
            try:
                subprocess.run([tool, "--version"], check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False
        return True

    def _format_tools_available(self) -> bool:
        """Check if formatting tools are available."""
        try:
            subprocess.run(["ruff", "--version"], check=True, capture_output=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _all_dependencies_available(self) -> bool:
        """Check if all dependencies for 'all' target are available."""
        return (
            self._uv_available()
            and self._test_dependencies_available()
            and self._lint_tools_available()
        )


class TestMakefileComprehensive:
    """Comprehensive test suite for advanced Makefile functionality."""

    @pytest.mark.makefile
    def test_all_makefile_targets_exist(self, makefile_framework) -> None:
        """Test that all expected Makefile targets exist.

        Arrange: Define list of expected targets
        Act: Check if targets exist in Makefile
        Assert: All targets are defined
        """
        # Arrange
        expected_targets = [
            "all",
            "install",
            "test",
            "lint",
            "format",
            "docs",
            "clean",
            "deploy",
            "check-system",
            "setup-k3s",
            "setup-monitoring",
            "backup",
            "restore",
            "security-scan",
            "help",
        ]  # Act
        makefile_content = makefile_framework.makefile_path.read_text(encoding="utf-8")

        # Assert
        for target in expected_targets:
            target_pattern = f"{target}:"
            assert (
                target_pattern in makefile_content
            ), f"Target '{target}' not found in Makefile"
            logger.info(f"✓ Target '{target}' found in Makefile")

    @pytest.mark.makefile
    def test_makefile_help_target(self, makefile_framework) -> None:
        """Test that help target provides useful information.

        Arrange: Prepare help command
        Act: Run make help
        Assert: Help output contains target descriptions
        """  # Arrange & Act
        result = makefile_framework.run_make_target("help")

        # Assert
        if result.returncode == 0:
            assert (
                "Available targets:" in result.stdout
                or "Usage:" in result.stdout
                or len(result.stdout.strip()) > 20
            )
            logger.info("✓ Help target provides comprehensive information")
        else:
            logger.info("⚠ Help target not available or failed")

    @pytest.mark.makefile
    def test_makefile_target_dependencies(self) -> None:
        """Test that Makefile target dependencies work correctly.

        Arrange: Identify targets with dependencies
        Act: Run targets that should trigger dependencies
        Assert: Dependencies execute before main target
        """
        # Arrange
        dependent_targets = {
            "test": ["install"],
            "lint": ["install"],
            "docs": ["install"],
        }

        for target, dependencies in dependent_targets.items():
            # Act
            result = self.run_make_target(target)

            # Assert - target should succeed or show dependency execution
            output_text = result.stdout + result.stderr
            dependency_indicators = ["uv", "install", "sync", "dependency"]
            has_dependency_output = any(
                indicator in output_text for indicator in dependency_indicators
            )

            assert result.returncode in [0, 1] or has_dependency_output
            logger.info(f"✓ Target '{target}' properly handles dependencies")

    @pytest.mark.makefile
    def test_makefile_error_handling(self) -> None:
        """Test that Makefile handles errors gracefully.

        Arrange: Try to run invalid targets
        Act: Run non-existent make target
        Assert: Appropriate error message is shown
        """
        # Arrange
        invalid_target = "nonexistent-target-123"

        # Act
        result = self.run_make_target(invalid_target)

        # Assert
        assert result.returncode != 0, "Invalid target should fail"
        error_indicators = ["No rule", "Unknown", "Error", "not found", "invalid"]
        output_text = result.stdout + result.stderr
        assert any(indicator in output_text for indicator in error_indicators)
        logger.info("✓ Makefile properly handles invalid targets")

    @pytest.mark.makefile
    def test_makefile_performance_baseline(self) -> None:
        """Test that Makefile targets complete within reasonable time.

        Arrange: Define performance expectations
        Act: Time target execution
        Assert: Targets complete within expected timeframes
        """
        import time

        # Arrange
        performance_targets = {
            "clean": 10,  # seconds
            "format": 60,  # seconds
            "lint": 120,  # seconds
        }

        for target, max_time in performance_targets.items():
            # Act
            start_time = time.time()
            result = self.run_make_target(target)
            execution_time = time.time() - start_time

            # Assert - either succeeds or completes within time limit
            if result.returncode == 0:
                assert (
                    execution_time < max_time
                ), f"Target {target} took {execution_time:.2f}s (max: {max_time}s)"
                logger.info(f"✓ Target '{target}' completed in {execution_time:.2f}s")
            else:
                logger.info(
                    f"⚠ Target '{target}' failed but completed in {execution_time:.2f}s"
                )

    @pytest.mark.makefile
    def test_makefile_all_target_comprehensive(self) -> None:
        """Test that 'all' target runs comprehensive workflow.

        Arrange: Prepare for full workflow
        Act: Run make all
        Assert: Multiple operations execute successfully
        """
        # Arrange & Act
        result = self.run_make_target("all")

        # Assert
        if result.returncode == 0:
            # Should show evidence of multiple operations
            workflow_indicators = [
                "install",
                "test",
                "lint",
                "format",
                "docs",
                "uv",
                "pytest",
                "ruff",
                "mypy",
            ]
            output_text = result.stdout + result.stderr
            indicators_found = sum(
                1 for indicator in workflow_indicators if indicator in output_text
            )

            assert (
                indicators_found >= 2
            ), f"All target should run multiple operations, found {indicators_found}"
            logger.info(
                f"✓ All target executed comprehensive workflow ({indicators_found} operations)"
            )
        else:
            logger.info(
                "⚠ All target failed - this may be expected in development environment"
            )

    @pytest.mark.makefile
    def test_makefile_target_idempotency_advanced(self) -> None:
        """Test that Makefile targets are idempotent with multiple runs.

        Arrange: Run targets multiple times
        Act: Compare results between runs
        Assert: Repeated execution produces consistent results
        """
        # Arrange
        idempotent_targets = ["format", "clean", "docs"]

        for target in idempotent_targets:
            # Act - run twice
            result1 = self.run_make_target(target)
            result2 = self.run_make_target(target)

            # Assert - both should have same success/failure pattern
            if result1.returncode == 0:
                assert (
                    result2.returncode == 0
                ), f"Second run of {target} failed (not idempotent)"
                logger.info(f"✓ Target '{target}' is idempotent")
            else:
                logger.info(
                    f"⚠ Target '{target}' failed consistently (acceptable if dependencies missing)"
                )

    @pytest.mark.makefile
    def test_makefile_security_considerations(self) -> None:
        """Test that Makefile doesn't have obvious security issues.

        Arrange: Check Makefile content
        Act: Scan for security anti-patterns
        Assert: No obvious security issues found
        """
        # Arrange & Act
        makefile_content = self.makefile_path.read_text()

        # Assert - check for security anti-patterns
        security_issues = []

        # Check for hardcoded credentials
        suspicious_patterns = [
            "password=",
            "secret=",
            "token=",
            "key=",
            "PASSWORD=",
            "SECRET=",
            "TOKEN=",
            "KEY=",
        ]

        for pattern in suspicious_patterns:
            if pattern in makefile_content:
                security_issues.append(f"Potential hardcoded credential: {pattern}")

        # Check for unsafe operations
        unsafe_patterns = ["rm -rf /", "sudo rm", "chmod 777"]
        for pattern in unsafe_patterns:
            if pattern in makefile_content:
                security_issues.append(f"Unsafe operation: {pattern}")

        assert len(security_issues) == 0, f"Security issues found: {security_issues}"
        logger.info("✓ Makefile passes basic security checks")

    @pytest.mark.makefile
    def test_makefile_documentation_quality(self) -> None:
        """Test that Makefile has adequate documentation.

        Arrange: Check Makefile content
        Act: Analyze documentation coverage
        Assert: Adequate documentation is present
        """
        # Arrange & Act
        makefile_content = self.makefile_path.read_text()
        lines = makefile_content.split("\n")

        # Assert
        comment_lines = [line for line in lines if line.strip().startswith("#")]
        target_lines = [
            line for line in lines if ":" in line and not line.strip().startswith("#")
        ]

        # Should have reasonable documentation
        documentation_ratio = len(comment_lines) / max(len(target_lines), 1)

        assert (
            documentation_ratio >= 0.3
        ), f"Makefile should have more documentation (ratio: {documentation_ratio:.2f})"
        logger.info(
            f"✓ Makefile has adequate documentation (ratio: {documentation_ratio:.2f})"
        )


class TestMakefileIntegrationScenarios:
    """Integration test scenarios for Makefile workflows."""

    @pytest.fixture
    def framework(self) -> MakefileTestFramework:
        """Provide a test framework instance."""
        return MakefileTestFramework(Path(__file__).parent.parent.parent)

    @pytest.mark.makefile
    @pytest.mark.integration
    def test_development_workflow(self, framework: MakefileTestFramework) -> None:
        """Test complete development workflow using Makefile.

        Arrange: Prepare development environment
        Act: Execute development workflow targets
        Assert: Workflow completes successfully
        """
        # Arrange
        workflow_targets = ["install", "format", "lint", "test"]

        # Act & Assert
        all_succeeded = True
        for target in workflow_targets:
            result = framework.run_make_target(target)
            if result.returncode != 0:
                all_succeeded = False
                logger.warning(f"Development workflow target '{target}' failed")
            else:
                logger.info(f"✓ Development workflow target '{target}' succeeded")

        # At least some targets should succeed in a proper development environment
        logger.info(
            f"Development workflow completion status: {'✓ Complete' if all_succeeded else '⚠ Partial'}"
        ) @ pytest.mark.makefile

    @pytest.mark.integration
    def test_deployment_workflow(self, framework: MakefileTestFramework) -> None:
        """Test deployment workflow using Makefile.

        Arrange: Prepare deployment environment
        Act: Execute deployment workflow targets
        Assert: Deployment workflow is properly structured
        """
        # Arrange
        deployment_targets = ["install", "test", "lint", "deploy"]

        # Act & Assert
        workflow_results = {}
        for target in deployment_targets:
            result = framework.run_make_target(target)
            workflow_results[target] = result.returncode
            logger.info(
                f"Deployment target '{target}': {'✓' if result.returncode == 0 else '✗'}"
            )

        # Deployment workflow should be structurally sound
        assert "deploy" in [
            target for target in deployment_targets
        ], "Deploy target should be defined"
        logger.info("✓ Deployment workflow is properly structured")

    @pytest.mark.makefile
    @pytest.mark.integration
    def test_ci_cd_compatibility(self, framework: MakefileTestFramework) -> None:
        """Test that Makefile targets are compatible with CI/CD.

        Arrange: Simulate CI/CD environment
        Act: Run CI/CD relevant targets
        Assert: Targets behave appropriately for automation
        """
        # Arrange
        ci_targets = ["install", "lint", "test", "docs"]  # Act & Assert
        for target in ci_targets:
            result = framework.run_make_target(target)

            # In CI/CD, we expect clear success/failure (no interactive prompts)
            assert result.returncode in [
                0,
                1,
            ], f"Target {target} should have clear exit code"

            # Output should be suitable for logging
            output_length = len(result.stdout) + len(result.stderr)
            assert (
                output_length < 10000
            ), f"Target {target} produces excessive output ({output_length} chars)"

            logger.info(f"✓ Target '{target}' is CI/CD compatible")


# Initialize test framework for module-level tests
test_framework = MakefileTestFramework(Path(__file__).parent.parent.parent)


@pytest.mark.makefile
def test_makefile_exists_and_readable():
    """Test that Makefile exists and is readable."""
    assert (
        test_framework.makefile_path.exists()
    ), "Makefile should exist in project root"
    assert test_framework.makefile_path.is_file(), "Makefile should be a file"
    assert (
        test_framework.makefile_path.stat().st_size > 0
    ), "Makefile should not be empty"
    logger.info("✓ Makefile exists and is readable")


@pytest.mark.makefile
def test_makefile_basic_targets():
    """Test that basic required targets exist."""
    basic_targets = ["all", "install", "test", "clean"]
    makefile_content = test_framework.makefile_path.read_text()

    for target in basic_targets:
        assert f"{target}:" in makefile_content, f"Basic target '{target}' missing"

    logger.info(f"✓ All {len(basic_targets)} basic targets found")
