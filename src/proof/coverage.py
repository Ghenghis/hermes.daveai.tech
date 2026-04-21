"""
Coverage Tracker - Code coverage analysis and reporting.
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CoverageTracker:
    """
    Tracks and reports code coverage metrics for contract testing.
    
    Provides line-level, branch-level, and function-level coverage tracking
    with support for generating detailed HTML and JSON reports.
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize coverage tracker with configuration.
        
        Args:
            config: Configuration dictionary containing:
                - source_package: package/module to track coverage for
                - output_dir: directory for coverage reports
                - report_format: format for reports (html, json, lcov)
                - branch_coverage: whether to track branch coverage
                - min_coverage: minimum required coverage percentage
        """
        self.config = config
        self.source_package = config.get("source_package", "src")
        self.output_dir = Path(config.get("output_dir", tempfile.gettempdir()))
        self.report_format = config.get("report_format", "html")
        self.branch_coverage = config.get("branch_coverage", True)
        self.min_coverage = config.get("min_coverage", 80.0)
        
        self._tracking = False
        self._coverage_data: Optional[Dict[str, Any]] = None
        self._start_time: Optional[datetime] = None
        self._coverage_file = self.output_dir / ".coverage"
    
    def start_tracking(self) -> None:
        """
        Begin coverage tracking for subsequent test execution.
        
        Sets up coverage collection by running tests with coverage enabled.
        """
        self._tracking = True
        self._start_time = datetime.now()
        self._coverage_data = None
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if self._coverage_file.exists():
            self._coverage_file.unlink()
    
    def stop_tracking(self) -> Dict[str, Any]:
        """
        Stop coverage tracking and retrieve collected data.
        
        Returns:
            Dictionary containing coverage metrics including:
                - line_coverage: percentage of lines covered
                - branch_coverage: percentage of branches covered
                - uncovered_lines: list of line numbers not covered
                - covered_lines: total lines covered
                - total_lines: total executable lines
        """
        if not self._tracking:
            return {"error": "Tracking not started"}
        
        self._tracking = False
        
        coverage_info = self._run_coverage_report()
        self._coverage_data = coverage_info
        
        return coverage_info
    
    def get_line_coverage(self) -> float:
        """
        Calculate line coverage percentage.
        
        Returns:
            Float representing percentage of lines covered (0-100)
        """
        if self._coverage_data is None:
            coverage_info = self._get_coverage_info()
            self._coverage_data = coverage_info
        
        total = self._coverage_data.get("total_lines", 0)
        covered = self._coverage_data.get("covered_lines", 0)
        
        if total == 0:
            return 0.0
        
        return round((covered / total) * 100, 2)
    
    def get_branch_coverage(self) -> float:
        """
        Calculate branch coverage percentage.
        
        Returns:
            Float representing percentage of branches covered (0-100)
        """
        if self._coverage_data is None:
            coverage_info = self._get_coverage_info()
            self._coverage_data = coverage_info
        
        total = self._coverage_data.get("total_branches", 0)
        covered = self._coverage_data.get("covered_branches", 0)
        
        if total == 0:
            return 0.0
        
        return round((covered / total) * 100, 2)
    
    def get_uncovered_lines(self) -> List[int]:
        """
        Identify lines that were not executed during tests.
        
        Returns:
            List of line numbers that have no coverage
        """
        if self._coverage_data is None:
            coverage_info = self._get_coverage_info()
            self._coverage_data = coverage_info
        
        return self._coverage_data.get("uncovered_lines", [])
    
    def generate_report(self, output_path: str) -> None:
        """
        Generate coverage report at the specified path.
        
        Args:
            output_path: Path for the generated report file
        """
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        if self._coverage_data is None:
            self._coverage_data = self._get_coverage_info()
        
        if self.report_format == "html" or output_path_obj.suffix == ".html":
            self._generate_html_report(output_path_obj)
        elif self.report_format == "json" or output_path_obj.suffix == ".json":
            self._generate_json_report(output_path_obj)
        elif self.report_format == "lcov":
            self._generate_lcov_report(output_path_obj)
        elif self.report_format == "xml":
            self._generate_cobertura_xml(output_path_obj)
        else:
            raise ValueError(f"Unsupported report format: {self.report_format}")
    
    def _run_coverage_report(self) -> Dict[str, Any]:
        """Execute coverage.py to generate coverage data."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "coverage", "json", "-o", str(self.output_dir / "coverage.json")],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            json_report = self.output_dir / "coverage.json"
            if json_report.exists():
                with open(json_report, encoding="utf-8") as f:
                    return json.load(f)
            
        except Exception as e:
            return self._get_fallback_coverage_data()
        
        return self._get_fallback_coverage_data()
    
    def _get_coverage_info(self) -> Dict[str, Any]:
        """Retrieve coverage information from coverage.py."""
        try:
            import coverage
            
            cov = coverage.Coverage()
            cov.load()
            
            data = cov.get_data()
            measured_files = data.measured_files()
            
            total_lines = 0
            covered_lines = 0
            uncovered_lines = []
            total_branches = 0
            covered_branches = 0
            
            for file_path in measured_files:
                lines = data.lines(file_path)
                if lines:
                    total_lines += len(lines)
                    covered_lines += len(lines)
                    uncovered_lines.extend([f"{file_path}:{line}" for line in lines if line not in lines])
            
            return {
                "total_lines": total_lines,
                "covered_lines": covered_lines,
                "uncovered_lines": uncovered_lines,
                "total_branches": total_branches,
                "covered_branches": covered_branches,
                "files": list(measured_files)
            }
            
        except ImportError:
            return self._get_fallback_coverage_data()
        except Exception:
            return self._get_fallback_coverage_data()
    
    def _get_fallback_coverage_data(self) -> Dict[str, Any]:
        """Provide fallback coverage data when coverage.py unavailable."""
        return {
            "total_lines": 0,
            "covered_lines": 0,
            "uncovered_lines": [],
            "total_branches": 0,
            "covered_branches": 0,
            "files": [],
            "error": "Coverage data unavailable"
        }
    
    def _generate_html_report(self, output_path: Path) -> None:
        """Generate HTML coverage report."""
        line_cov = self.get_line_coverage()
        branch_cov = self.get_branch_coverage()
        uncovered = self.get_uncovered_lines()
        
        coverage_status = "success" if line_cov >= self.min_coverage else "danger"
        
        cov_data = self._coverage_data or {}
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Coverage Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; }}
        .metrics {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric-card {{ flex: 1; padding: 20px; border-radius: 8px; text-align: center; }}
        .metric-card.success {{ background: #d4edda; }}
        .metric-card.danger {{ background: #f8d7da; }}
        .metric-card.info {{ background: #d1ecf1; }}
        .metric-value {{ font-size: 2.5em; font-weight: bold; }}
        .metric-label {{ font-size: 0.9em; color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #34495e; color: white; }}
        .uncovered {{ background: #fff3cd; }}
        .progress-bar {{ background: #e9ecef; border-radius: 4px; height: 20px; overflow: hidden; }}
        .progress-fill {{ height: 100%; transition: width 0.3s ease; }}
        .progress-fill.success {{ background: #28a745; }}
        .progress-fill.danger {{ background: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Contract Kit Coverage Report</h1>
        <p>Generated: {datetime.now().isoformat()}</p>
        
        <div class="metrics">
            <div class="metric-card {coverage_status}">
                <div class="metric-value">{line_cov}%</div>
                <div class="metric-label">Line Coverage</div>
            </div>
            <div class="metric-card info">
                <div class="metric-value">{branch_cov}%</div>
                <div class="metric-label">Branch Coverage</div>
            </div>
            <div class="metric-card info">
                <div class="metric-value">{len(uncovered)}</div>
                <div class="metric-label">Uncovered Lines</div>
            </div>
        </div>
        
        <h2>Coverage Progress</h2>
        <div class="progress-bar">
            <div class="progress-fill {coverage_status}" style="width: {line_cov}%"></div>
        </div>
        <p>Minimum required: {self.min_coverage}%</p>
        
        <h2>Coverage Details</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Source Package</td>
                    <td>{self.source_package}</td>
                </tr>
                <tr>
                    <td>Total Lines</td>
                    <td>{cov_data.get('total_lines', 0)}</td>
                </tr>
                <tr>
                    <td>Covered Lines</td>
                    <td>{cov_data.get('covered_lines', 0)}</td>
                </tr>
                <tr>
                    <td>Total Branches</td>
                    <td>{cov_data.get('total_branches', 0)}</td>
                </tr>
                <tr>
                    <td>Covered Branches</td>
                    <td>{cov_data.get('covered_branches', 0)}</td>
                </tr>
            </tbody>
        </table>
        
        <h2>Uncovered Lines</h2>
        <pre>{json.dumps(uncovered, indent=2)}</pre>
    </div>
</body>
</html>"""
        
        output_path.write_text(html_content, encoding="utf-8")
    
    def _generate_json_report(self, output_path: Path) -> None:
        """Generate JSON coverage report."""
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "line_coverage": self.get_line_coverage(),
            "branch_coverage": self.get_branch_coverage(),
            "uncovered_lines": self.get_uncovered_lines(),
            "coverage_data": self._coverage_data,
            "config": {
                "source_package": self.source_package,
                "min_coverage": self.min_coverage,
                "branch_coverage_enabled": self.branch_coverage
            }
        }
        output_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    
    def _generate_lcov_report(self, output_path: Path) -> None:
        """Generate LCOV format coverage report."""
        lcov_lines = ["TN:", f"SF:{self.source_package}"]
        
        uncovered = self.get_uncovered_lines()
        for line in uncovered:
            lcov_lines.append(f"DA:{line},0")
        
        lcov_lines.extend([
            "end_of_record",
            "SF:",
            "end_of_record"
        ])
        
        output_path.write_text("\n".join(lcov_lines), encoding="utf-8")
    
    def _generate_cobertura_xml(self, output_path: Path) -> None:
        """Generate Cobertura XML format coverage report."""
        line_cov = self.get_line_coverage()
        
        xml_lines = [
            '<?xml version="1.0" ?>',
            '<!DOCTYPE coverage SYSTEM "http://cobertura.sourceforge.net/xml/coverage-04.dtd">',
            '<coverage coverage-rate="0.0">',
            f'  <sources><source>{self.source_package}</source></sources>',
            '  <packages><package>',
            '    <classes><class>',
            f'      <lines><line number="1" hits="{int(line_cov)}"/></lines>',
            '    </class></classes>',
            '  </package></packages>',
            '</coverage>'
        ]
        
        output_path.write_text("\n".join(xml_lines), encoding="utf-8")
