#!/usr/bin/env python3
"""
Coverage optimization and gap analysis for the homelab testing suite.
Identifies specific areas for improvement to achieve 90%+ coverage.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger


class CoverageOptimizer:
    """Optimize test coverage to achieve 90%+ target."""

    def __init__(self, project_root: Path):
        """Initialize coverage optimizer.

        Args:
            project_root: Path to project root directory
        """
        self.project_root = project_root
        self.coverage_target = 90.0
        self.coverage_data: dict[str, Any] = {}
        self.optimization_plan: list[dict[str, Any]] = []

    def analyze_current_coverage(self) -> dict[str, Any]:
        """Analyze current test coverage across all modules.

        Returns:
            Coverage analysis results
        """
        logger.info("Analyzing current test coverage")

        try:
            # Run pytest with coverage
            cmd = [
                "uv",
                "run",
                "pytest",
                "tests/",
                "--cov=src",
                "--cov=scripts",
                "--cov=infrastructure",
                "--cov-report=json:coverage.json",
                "--cov-report=term",
                "-q",
            ]

            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True
            )

            if result.returncode != 0:
                logger.warning(
                    "Some tests failed, but continuing with coverage analysis"
                )
                logger.debug(f"Test output: {result.stdout}")

            # Load coverage data
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    self.coverage_data = json.load(f)

                return self._parse_coverage_data()
            else:
                logger.error("Coverage data file not found")
                return {"error": "Coverage data not available"}

        except Exception as e:
            logger.error(f"Coverage analysis failed: {e}")
            return {"error": str(e)}

    def _parse_coverage_data(self) -> dict[str, Any]:
        """Parse coverage data and identify gaps.

        Returns:
            Parsed coverage analysis
        """
        if not self.coverage_data:
            return {"error": "No coverage data available"}

        files = self.coverage_data.get("files", {})
        totals = self.coverage_data.get("totals", {})

        overall_coverage = totals.get("percent_covered", 0)

        # Categorize files by coverage level
        high_coverage = {}  # >= 90%
        medium_coverage = {}  # 70-89%
        low_coverage = {}  # 50-69%
        very_low_coverage = {}  # < 50%
        untested = {}  # 0%

        for filepath, data in files.items():
            coverage_percent = data.get("summary", {}).get("percent_covered", 0)

            if coverage_percent >= 90:
                high_coverage[filepath] = coverage_percent
            elif coverage_percent >= 70:
                medium_coverage[filepath] = coverage_percent
            elif coverage_percent >= 50:
                low_coverage[filepath] = coverage_percent
            elif coverage_percent > 0:
                very_low_coverage[filepath] = coverage_percent
            else:
                untested[filepath] = coverage_percent

        analysis = {
            "overall_coverage": overall_coverage,
            "target_coverage": self.coverage_target,
            "gap_to_target": max(0, self.coverage_target - overall_coverage),
            "file_categories": {
                "high_coverage": high_coverage,
                "medium_coverage": medium_coverage,
                "low_coverage": low_coverage,
                "very_low_coverage": very_low_coverage,
                "untested": untested,
            },
            "statistics": {
                "total_files": len(files),
                "high_coverage_files": len(high_coverage),
                "medium_coverage_files": len(medium_coverage),
                "low_coverage_files": len(low_coverage),
                "very_low_coverage_files": len(very_low_coverage),
                "untested_files": len(untested),
            },
        }

        logger.info(f"Overall coverage: {overall_coverage:.1f}%")
        logger.info(f"Gap to target: {analysis['gap_to_target']:.1f}%")

        return analysis

    def generate_optimization_plan(
        self, analysis: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate specific optimization recommendations.

        Args:
            analysis: Coverage analysis results

        Returns:
            List of optimization actions
        """
        logger.info("Generating coverage optimization plan")

        plan = []
        categories = analysis.get("file_categories", {})

        # Priority 1: Add tests for completely untested files
        untested = categories.get("untested", {})
        if untested:
            plan.append(
                {
                    "priority": 1,
                    "action": "Add unit tests for untested files",
                    "files": list(untested.keys()),
                    "impact": "High - Major coverage increase",
                    "effort": "Medium - New test files needed",
                    "estimated_coverage_gain": len(untested)
                    * 15,  # Estimate 15% per file
                }
            )

        # Priority 2: Improve very low coverage files
        very_low = categories.get("very_low_coverage", {})
        if very_low:
            plan.append(
                {
                    "priority": 2,
                    "action": "Enhance tests for very low coverage files",
                    "files": list(very_low.keys()),
                    "impact": "Medium-High - Significant improvement",
                    "effort": "Medium - Expand existing tests",
                    "estimated_coverage_gain": len(very_low)
                    * 8,  # Estimate 8% per file
                }
            )

        # Priority 3: Improve low coverage files
        low = categories.get("low_coverage", {})
        if low:
            plan.append(
                {
                    "priority": 3,
                    "action": "Add edge case tests for low coverage files",
                    "files": list(low.keys()),
                    "impact": "Medium - Moderate improvement",
                    "effort": "Low-Medium - Add specific test cases",
                    "estimated_coverage_gain": len(low) * 5,  # Estimate 5% per file
                }
            )

        # Priority 4: Error handling and edge cases
        plan.append(
            {
                "priority": 4,
                "action": "Add comprehensive error handling tests",
                "files": "All modules",
                "impact": "Medium - Better error coverage",
                "effort": "Medium - Add exception test cases",
                "estimated_coverage_gain": 3,
            }
        )

        # Priority 5: Integration test improvements
        plan.append(
            {
                "priority": 5,
                "action": "Enhance integration test coverage",
                "files": "Cross-module interactions",
                "impact": "Low-Medium - Better integration coverage",
                "effort": "High - Complex test scenarios",
                "estimated_coverage_gain": 2,
            }
        )

        self.optimization_plan = plan
        return plan

    def identify_specific_gaps(self, analysis: dict[str, Any]) -> dict[str, list[str]]:
        """Identify specific uncovered lines and functions.

        Args:
            analysis: Coverage analysis results

        Returns:
            Specific gaps by file
        """
        logger.info("Identifying specific coverage gaps")

        gaps = {}
        files = self.coverage_data.get("files", {})

        for filepath, data in files.items():
            if data.get("summary", {}).get("percent_covered", 0) < self.coverage_target:
                missing_lines = data.get("missing_lines", [])
                excluded_lines = data.get("excluded_lines", [])

                if missing_lines:
                    gaps[filepath] = {
                        "missing_lines": missing_lines,
                        "excluded_lines": excluded_lines,
                        "coverage_percent": data.get("summary", {}).get(
                            "percent_covered", 0
                        ),
                        "suggestions": self._generate_line_suggestions(
                            filepath, missing_lines
                        ),
                    }

        return gaps

    def _generate_line_suggestions(
        self, filepath: str, missing_lines: list[int]
    ) -> list[str]:
        """Generate suggestions for covering specific lines.

        Args:
            filepath: File path with missing coverage
            missing_lines: List of uncovered line numbers

        Returns:
            List of suggestions for covering those lines
        """
        suggestions = []

        # Try to read the file and analyze missing lines
        try:
            file_path = self.project_root / filepath
            if file_path.exists():
                with open(file_path, encoding="utf-8") as f:
                    lines = f.readlines()

                for line_num in missing_lines[:5]:  # Limit to first 5 for brevity
                    if line_num <= len(lines):
                        line_content = lines[line_num - 1].strip()
                        suggestion = self._analyze_line_for_suggestion(
                            line_content, line_num
                        )
                        if suggestion:
                            suggestions.append(f"Line {line_num}: {suggestion}")

        except Exception as e:
            logger.debug(f"Could not analyze {filepath}: {e}")
            suggestions.append("Review file manually for coverage opportunities")

        return suggestions

    def _analyze_line_for_suggestion(self, line_content: str, line_num: int) -> str:
        """Analyze a specific line and suggest how to cover it.

        Args:
            line_content: Content of the uncovered line
            line_num: Line number

        Returns:
            Suggestion for covering this line
        """
        line = line_content.lower()

        if "except" in line or "raise" in line:
            return "Add test case that triggers this exception"
        elif "if" in line and ("not" in line or "==" in line):
            return "Add test for this conditional branch"
        elif "else:" in line:
            return "Add test that reaches this else clause"
        elif "return" in line:
            return "Add test that exercises this return path"
        elif "logger" in line or "print" in line:
            return "Add test that verifies logging/output"
        elif "def " in line:
            return "Add test that calls this function"
        elif "class " in line:
            return "Add test that instantiates this class"
        else:
            return "Add test that executes this code path"

    def generate_coverage_report(self) -> str:
        """Generate comprehensive coverage optimization report.

        Returns:
            Formatted coverage report
        """
        logger.info("Generating comprehensive coverage report")

        analysis = self.analyze_current_coverage()
        if "error" in analysis:
            return f"Coverage analysis failed: {analysis['error']}"

        plan = self.generate_optimization_plan(analysis)
        gaps = self.identify_specific_gaps(analysis)

        report = []
        report.append("# Smart Home K3s Laboratory - Coverage Optimization Report")
        report.append("=" * 60)
        report.append("")

        # Current Status
        report.append("## Current Coverage Status")
        report.append(f"- **Overall Coverage**: {analysis['overall_coverage']:.1f}%")
        report.append(f"- **Target Coverage**: {analysis['target_coverage']:.1f}%")
        report.append(f"- **Gap to Target**: {analysis['gap_to_target']:.1f}%")
        report.append("")

        # Statistics
        stats = analysis["statistics"]
        report.append("## File Coverage Distribution")
        report.append(f"- **Total Files**: {stats['total_files']}")
        report.append(f"- **High Coverage (≥90%)**: {stats['high_coverage_files']}")
        report.append(
            f"- **Medium Coverage (70-89%)**: {stats['medium_coverage_files']}"
        )
        report.append(f"- **Low Coverage (50-69%)**: {stats['low_coverage_files']}")
        report.append(
            f"- **Very Low Coverage (<50%)**: {stats['very_low_coverage_files']}"
        )
        report.append(f"- **Untested Files**: {stats['untested_files']}")
        report.append("")

        # Optimization Plan
        report.append("## Coverage Optimization Plan")
        for item in plan:
            report.append(f"### Priority {item['priority']}: {item['action']}")
            report.append(f"- **Impact**: {item['impact']}")
            report.append(f"- **Effort**: {item['effort']}")
            report.append(f"- **Estimated Gain**: +{item['estimated_coverage_gain']}%")

            if isinstance(item["files"], list) and len(item["files"]) <= 10:
                report.append(f"- **Files**: {', '.join(item['files'])}")
            elif isinstance(item["files"], list):
                report.append(
                    f"- **Files**: {len(item['files'])} files (see detailed list)"
                )
            else:
                report.append(f"- **Target**: {item['files']}")
            report.append("")

        # Specific Gaps
        if gaps:
            report.append("## Specific Coverage Gaps")
            for filepath, gap_info in list(gaps.items())[:10]:  # Limit to top 10
                report.append(f"### {filepath}")
                report.append(
                    f"- **Current Coverage**: {gap_info['coverage_percent']:.1f}%"
                )
                report.append(
                    f"- **Missing Lines**: {len(gap_info['missing_lines'])} lines"
                )

                if gap_info["suggestions"]:
                    report.append("- **Suggestions**:")
                    for suggestion in gap_info["suggestions"][:3]:  # Top 3 suggestions
                        report.append(f"  - {suggestion}")
                report.append("")

        # Quick Wins
        report.append("## Quick Wins for Coverage Improvement")
        report.append("1. **Add exception tests**: Test error handling paths")
        report.append("2. **Test edge cases**: Boundary conditions and invalid inputs")
        report.append(
            "3. **Mock external calls**: Cover external dependency interactions"
        )
        report.append("4. **Add integration tests**: Test component interactions")
        report.append("5. **Test configuration loading**: Cover all config scenarios")
        report.append("")

        # Implementation Guide
        report.append("## Implementation Guide")
        report.append("```bash")
        report.append("# Run coverage analysis")
        report.append(
            "uv run pytest --cov=src --cov=scripts --cov=infrastructure --cov-report=html"
        )
        report.append("")
        report.append("# View detailed coverage report")
        report.append("open htmlcov/index.html  # View in browser")
        report.append("")
        report.append("# Run specific test categories")
        report.append("uv run pytest tests/unit/ -v")
        report.append("uv run pytest tests/integration/ -v")
        report.append("```")

        return "\n".join(report)

    def save_optimization_report(self, report: str) -> Path:
        """Save optimization report to file.

        Args:
            report: Coverage optimization report content

        Returns:
            Path to saved report file
        """
        report_file = self.project_root / "COVERAGE_OPTIMIZATION.md"

        try:
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(report)

            logger.info(f"Coverage optimization report saved to: {report_file}")
            return report_file

        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            raise


def main() -> None:
    """Generate coverage optimization analysis and report."""
    project_root = Path(__file__).parent.parent

    logger.info("Starting coverage optimization analysis")

    optimizer = CoverageOptimizer(project_root)
    report = optimizer.generate_coverage_report()

    # Save report
    report_file = optimizer.save_optimization_report(report)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 Coverage Optimization Analysis Complete")
    print("=" * 60)
    print(f"📄 Report saved to: {report_file}")
    print("\n🎯 Next Steps:")
    print("1. Review the optimization plan priorities")
    print("2. Implement high-impact, low-effort improvements first")
    print("3. Focus on untested files for maximum coverage gain")
    print("4. Add comprehensive error handling tests")
    print("5. Re-run analysis after improvements")

    logger.info("Coverage optimization analysis completed")


if __name__ == "__main__":
    main()
