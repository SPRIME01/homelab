#!/usr/bin/env python3
"""
Coverage analysis and optimization script for the homelab testing suite.
Analyzes test coverage, identifies gaps, and provides recommendations for 90%+ coverage.
"""

import subprocess
from pathlib import Path
from typing import Any

from loguru import logger


class CoverageAnalyzer:
    """Analyze and optimize test coverage for the homelab project."""

    def __init__(self, project_root: Path):
        """Initialize coverage analyzer.

        Args:
            project_root: Path to project root directory
        """
        self.project_root = project_root
        self.src_dir = project_root / "src"
        self.scripts_dir = project_root / "scripts"
        self.infrastructure_dir = project_root / "infrastructure"
        self.tests_dir = project_root / "tests"

    def run_coverage_analysis(self) -> dict[str, Any]:
        """Run comprehensive coverage analysis.

        Returns:
            Coverage analysis results
        """
        logger.info("Starting comprehensive coverage analysis")

        try:
            # Run pytest with coverage for all modules
            cmd = [
                "uv",
                "run",
                "pytest",
                str(self.tests_dir),
                "--cov=src",
                "--cov=scripts",
                "--cov=infrastructure",
                "--cov-report=term-missing",
                "--cov-report=json:coverage.json",
                "--cov-report=html:htmlcov",
                "-v",
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            logger.info(
                f"Coverage analysis completed with return code: {result.returncode}"
            )

            # Parse coverage results
            coverage_data = self._parse_coverage_output(result.stdout + result.stderr)

            return {
                "success": result.returncode
                in [0, 1],  # Tests may fail but coverage should run
                "output": result.stdout + result.stderr,
                "coverage_data": coverage_data,
                "recommendations": self._generate_recommendations(coverage_data),
            }

        except Exception as e:
            logger.error(f"Coverage analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "coverage_data": {},
                "recommendations": [],
            }

    def _parse_coverage_output(self, output: str) -> dict[str, Any]:
        """Parse coverage output to extract metrics.

        Args:
            output: Coverage command output

        Returns:
            Parsed coverage data
        """
        coverage_data = {
            "total_coverage": 0.0,
            "module_coverage": {},
            "missing_lines": {},
            "total_statements": 0,
            "covered_statements": 0,
        }

        lines = output.split("\n")

        # Look for coverage percentage
        for line in lines:
            if "TOTAL" in line and "%" in line:
                # Extract total coverage percentage
                parts = line.split()
                for part in parts:
                    if part.endswith("%"):
                        try:
                            coverage_data["total_coverage"] = float(
                                part.replace("%", "")
                            )
                        except ValueError:
                            pass
                        break

        # Extract module-specific coverage
        in_coverage_section = False
        for line in lines:
            if "Name" in line and "Stmts" in line and "Miss" in line:
                in_coverage_section = True
                continue

            if in_coverage_section and line.strip():
                if "TOTAL" in line:
                    break

                parts = line.split()
                if len(parts) >= 4:
                    module_name = parts[0]
                    try:
                        statements = int(parts[1])
                        missed = int(parts[2])
                        covered = statements - missed
                        coverage_pct = (
                            (covered / statements * 100) if statements > 0 else 0
                        )

                        coverage_data["module_coverage"][module_name] = {
                            "statements": statements,
                            "covered": covered,
                            "missed": missed,
                            "coverage": coverage_pct,
                        }
                    except (ValueError, IndexError):
                        continue

        return coverage_data

    def _generate_recommendations(self, coverage_data: dict[str, Any]) -> list[str]:
        """Generate recommendations to improve coverage.

        Args:
            coverage_data: Parsed coverage data

        Returns:
            List of recommendations
        """
        recommendations = []

        current_coverage = coverage_data.get("total_coverage", 0.0)

        if current_coverage < 90:
            recommendations.append(
                f"Current coverage is {current_coverage:.1f}% - need {90 - current_coverage:.1f}% more for 90% target"
            )

        # Analyze module-specific recommendations
        for module, data in coverage_data.get("module_coverage", {}).items():
            if data["coverage"] < 80:
                recommendations.append(
                    f"Module '{module}' has low coverage ({data['coverage']:.1f}%) - "
                    f"add {data['missed']} more test cases"
                )

        # General recommendations
        if not recommendations:
            recommendations.append(
                "Coverage target achieved! Consider adding edge case tests."
            )
        else:
            recommendations.extend(
                [
                    "Add unit tests for utility functions",
                    "Add integration tests for component interactions",
                    "Add error handling test cases",
                    "Add configuration validation tests",
                    "Test CLI argument parsing and edge cases",
                    "Add regression tests for bug fixes",
                ]
            )

        return recommendations

    def generate_coverage_report(self) -> str:
        """Generate a comprehensive coverage report.

        Returns:
            Coverage report as formatted string
        """
        analysis = self.run_coverage_analysis()

        report = "# Test Coverage Analysis Report\n\n"

        if analysis["success"]:
            coverage_data = analysis["coverage_data"]
            total_coverage = coverage_data.get("total_coverage", 0.0)

            report += f"## Overall Coverage: {total_coverage:.1f}%\n\n"

            if total_coverage >= 90:
                report += "(OK) **Coverage target achieved!**\n\n"
            else:
                needed = 90 - total_coverage
                report += (
                    f"⚠️ **Need {needed:.1f}% more coverage to reach 90% target**\n\n"
                )

            # Module breakdown
            report += "## Module Coverage Breakdown\n\n"
            for module, data in coverage_data.get("module_coverage", {}).items():
                status_char = "(OK)"
                if data["coverage"] < 90:
                    status_char = "⚠️"
                if data["coverage"] < 70:
                    status_char = "❌"
                report += f"{status_char} {module}: {data['coverage']:.1f}% ({data['covered']}/{data['statements']} statements)\n"

            # Recommendations
            report += "\n## Recommendations\n\n"
            for rec in analysis["recommendations"]:
                report += f"- {rec}\n"

        else:
            report += "❌ **Coverage analysis failed**\n\n"
            if "error" in analysis:
                report += f"Error: {analysis['error']}\n"

        report += "\n## Test Suite Summary\n\n"
        report += self._generate_test_suite_summary()

        return report

    def _generate_test_suite_summary(self) -> str:
        """Generate summary of test suite structure.

        Returns:
            Test suite summary
        """
        summary = ""

        # Count test files
        test_files = list(self.tests_dir.rglob("test_*.py"))
        summary += f"**Total test files**: {len(test_files)}\n\n"

        # Categorize tests
        categories = {
            "Unit Tests": list((self.tests_dir / "unit").glob("test_*.py"))
            if (self.tests_dir / "unit").exists()
            else [],
            "Integration Tests": list(
                (self.tests_dir / "integration").glob("test_*.py")
            )
            if (self.tests_dir / "integration").exists()
            else [],
            "Makefile Tests": list((self.tests_dir / "makefile").glob("test_*.py"))
            if (self.tests_dir / "makefile").exists()
            else [],
        }

        for category, files in categories.items():
            summary += f"**{category}**: {len(files)} files\n"

        summary += "\n**Test Infrastructure**:\n"
        summary += f"- Fixtures: {'(OK)' if (self.tests_dir / 'fixtures').exists() else '❌'}\n"
        summary += f"- Test helpers: {'(OK)' if (self.tests_dir / 'test_helpers.py').exists() else '❌'}\n"
        summary += f"- Conftest: {'(OK)' if (self.tests_dir / 'conftest.py').exists() else '❌'}\n"
        summary += f"- pytest.ini: {'(OK)' if (self.project_root / 'pytest.ini').exists() else '❌'}\n"

        return summary

    def optimize_coverage(self) -> dict[str, Any]:
        """Provide specific optimization suggestions.

        Returns:
            Coverage optimization suggestions
        """
        logger.info("Analyzing coverage optimization opportunities")

        # Analyze source files without tests
        untested_files = self._find_untested_files()

        # Analyze test distribution
        test_distribution = self._analyze_test_distribution()

        return {
            "untested_files": untested_files,
            "test_distribution": test_distribution,
            "priority_areas": self._identify_priority_areas(),
            "quick_wins": self._identify_quick_wins(),
        }

    def _find_untested_files(self) -> list[str]:
        """Find source files that may not have corresponding tests.

        Returns:
            List of potentially untested files
        """
        untested = []

        # Check src directory
        if self.src_dir.exists():
            for py_file in self.src_dir.rglob("*.py"):
                if py_file.name != "__init__.py":
                    # Look for corresponding test file
                    relative_path = py_file.relative_to(self.src_dir)
                    test_name = f"test_{py_file.stem}.py"

                    test_locations = [
                        self.tests_dir / "unit" / test_name,
                        self.tests_dir / "integration" / test_name,
                        self.tests_dir / test_name,
                    ]

                    if not any(loc.exists() for loc in test_locations):
                        untested.append(str(relative_path))

        # Check scripts directory
        if self.scripts_dir.exists():
            for py_file in self.scripts_dir.glob("*.py"):
                if not py_file.name.startswith("_"):
                    test_name = f"test_{py_file.stem}.py"
                    test_path = self.tests_dir / "unit" / test_name

                    if not test_path.exists():
                        untested.append(f"scripts/{py_file.name}")

        return untested

    def _analyze_test_distribution(self) -> dict[str, int]:
        """Analyze distribution of tests across categories.

        Returns:
            Test distribution statistics
        """
        distribution = {
            "unit_tests": 0,
            "integration_tests": 0,
            "makefile_tests": 0,
            "other_tests": 0,
        }

        for test_file in self.tests_dir.rglob("test_*.py"):
            if "unit" in str(test_file):
                distribution["unit_tests"] += 1
            elif "integration" in str(test_file):
                distribution["integration_tests"] += 1
            elif "makefile" in str(test_file):
                distribution["makefile_tests"] += 1
            else:
                distribution["other_tests"] += 1

        return distribution

    def _identify_priority_areas(self) -> list[str]:
        """Identify priority areas for test coverage improvement.

        Returns:
            List of priority areas
        """
        priorities = [
            "Core CLI functionality (src/homelab/cli/)",
            "System audit and validation (scripts/00-system-audit.py)",
            "Component installation (scripts/01-install-components.py)",
            "SSH key management (scripts/ssh-key-manager.py)",
            "Infrastructure deployment (infrastructure/)",
            "Error handling and edge cases",
            "Configuration validation",
        ]

        return priorities

    def _identify_quick_wins(self) -> list[str]:
        """Identify quick wins for improving coverage.

        Returns:
            List of quick win opportunities
        """
        quick_wins = [
            "Add simple unit tests for utility functions",
            "Test configuration parsing and validation",
            "Add error case tests for existing functions",
            "Test CLI argument parsing edge cases",
            "Add mock-based tests for external dependencies",
            "Test file I/O operations with temporary files",
            "Add property-based tests for data validation",
        ]

        return quick_wins


def main() -> None:
    """Main function to run coverage analysis."""
    project_root = Path(__file__).parent.parent
    analyzer = CoverageAnalyzer(project_root)

    logger.info("Generating comprehensive coverage report")

    # Generate coverage report
    report = analyzer.generate_coverage_report()

    # Save report to file
    report_file = project_root / "coverage_report.md"
    report_file.write_text(report)

    print(report)
    print(f"\n📊 Full report saved to: {report_file}")

    # Generate optimization suggestions
    optimization = analyzer.optimize_coverage()

    print("\n🎯 Coverage Optimization Suggestions:")
    print(f"- Untested files: {len(optimization['untested_files'])}")
    print(f"- Priority areas: {len(optimization['priority_areas'])}")
    print(f"- Quick wins: {len(optimization['quick_wins'])}")

    logger.info("Coverage analysis completed")


if __name__ == "__main__":
    main()
