"""
Test Runner - Orchestrates various testing paradigms for contract validation.
"""
import json
import os
import subprocess
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProofTestRunner:
    """
    Comprehensive test runner supporting unit, integration, and E2E tests.
    
    Provides unified interface for running pytest, Playwright, and custom test
    suites with result aggregation and reporting capabilities.
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the test runner with configuration.
        
        Args:
            config: Configuration dictionary containing:
                - pytest_args: list of arguments for pytest
                - playwright_timeout: timeout for Playwright tests
                - report_format: format for reports (html, json, xml)
                - coverage_enabled: whether to enable coverage tracking
                - temp_dir: temporary directory for test artifacts
        """
        self.config = config
        self.pytest_args = config.get("pytest_args", ["-v", "--tb=short"])
        self.playwright_timeout = config.get("playwright_timeout", 30000)
        self.report_format = config.get("report_format", "html")
        self.coverage_enabled = config.get("coverage_enabled", True)
        self.temp_dir = config.get("temp_dir", tempfile.gettempdir())
        self.results: Dict[str, Any] = {
            "unit": {},
            "integration": {},
            "e2e": {},
            "summary": {}
        }
        self._artifacts: List[str] = []
        self._start_time: Optional[datetime] = None
        self._coverage_data: Optional[Dict] = None
    
    def run_tests(self, test_path: str) -> Dict[str, Any]:
        """
        Run all tests found at the specified path.
        
        Automatically detects test type based on file structure and runs
        appropriate test suites.
        
        Args:
            test_path: Path to test file or directory
            
        Returns:
            Dictionary containing test results with keys:
                - passed: number of passed tests
                - failed: number of failed tests
                - skipped: number of skipped tests
                - errors: number of errors
                - duration: total execution time in seconds
                - details: detailed result information
        """
        self._start_time = datetime.now()
        test_path_obj = Path(test_path)
        
        if not test_path_obj.exists():
            return self._error_result(f"Test path does not exist: {test_path}")
        
        results = {
            "path": str(test_path),
            "timestamp": self._start_time.isoformat(),
            "tests": []
        }
        
        if test_path_obj.is_file():
            if test_path_obj.suffix in [".py"]:
                if "e2e" in test_path.lower() or "playwright" in test_path.lower():
                    results["tests"].append(self.run_e2e(test_path))
                else:
                    results["tests"].append(self.run_unit(test_path))
            elif test_path_obj.suffix in [".spec.ts", ".test.ts"]:
                results["tests"].append(self.run_e2e(test_path))
        else:
            results["tests"].append(self.run_unit(test_path))
            results["tests"].append(self.run_integration(test_path))
        
        results["summary"] = self._aggregate_results(results["tests"])
        return results
    
    def run_unit(self, test_path: str) -> Dict[str, Any]:
        """
        Run unit tests using pytest.
        
        Args:
            test_path: Path to unit test file or directory
            
        Returns:
            Dictionary with test results and metadata
        """
        start_time = datetime.now()
        test_path_obj = Path(test_path)
        
        if not test_path_obj.exists():
            return self._error_result(f"Unit test path not found: {test_path}")
        
        cmd = [sys.executable, "-m", "pytest", str(test_path)]
        cmd.extend(self.pytest_args)
        
        if self.coverage_enabled:
            cmd.extend(["--cov", "--cov-report=term-missing"])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.get("timeout", 300)
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            unit_results = {
                "type": "unit",
                "path": str(test_path),
                "passed": result.returncode == 0,
                "exit_code": result.returncode,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timestamp": start_time.isoformat()
            }
            
            self._parse_pytest_output(unit_results, result.stdout)
            self.results["unit"] = unit_results
            
            return unit_results
            
        except subprocess.TimeoutExpired:
            return self._error_result(f"Unit tests timed out after {self.config.get('timeout', 300)}s")
        except Exception as e:
            return self._error_result(f"Unit test execution failed: {str(e)}")
    
    def run_integration(self, test_path: str) -> Dict[str, Any]:
        """
        Run integration tests.
        
        Integration tests verify that multiple components work together correctly.
        
        Args:
            test_path: Path to integration test directory
            
        Returns:
            Dictionary with integration test results
        """
        start_time = datetime.now()
        
        integration_path = Path(test_path) / "integration"
        if not integration_path.exists():
            integration_path = Path(test_path)
        
        cmd = [sys.executable, "-m", "pytest", str(integration_path)]
        cmd.extend(self.pytest_args)
        cmd.extend(["-m", "integration"])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.get("timeout", 600)
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            integration_results = {
                "type": "integration",
                "path": str(integration_path),
                "passed": result.returncode == 0,
                "exit_code": result.returncode,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timestamp": start_time.isoformat()
            }
            
            self._parse_pytest_output(integration_results, result.stdout)
            self.results["integration"] = integration_results
            
            return integration_results
            
        except subprocess.TimeoutExpired:
            return self._error_result("Integration tests timed out")
        except Exception as e:
            return self._error_result(f"Integration test execution failed: {str(e)}")
    
    def run_e2e(self, test_path: str) -> Dict[str, Any]:
        """
        Run end-to-end tests using Playwright.
        
        Args:
            test_path: Path to E2E test file or directory
            
        Returns:
            Dictionary with E2E test results
        """
        start_time = datetime.now()
        
        playwright_cmd = self.config.get("playwright_cmd", "playwright")
        cmd = [playwright_cmd, "test", str(test_path)]
        
        if self.playwright_timeout:
            cmd.extend(["--timeout", str(self.playwright_timeout)])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.get("e2e_timeout", 600)
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            e2e_results = {
                "type": "e2e",
                "path": str(test_path),
                "passed": result.returncode == 0,
                "exit_code": result.returncode,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timestamp": start_time.isoformat()
            }
            
            self._parse_playwright_output(e2e_results, result.stdout)
            self.results["e2e"] = e2e_results
            
            return e2e_results
            
        except subprocess.TimeoutExpired:
            return self._error_result("E2E tests timed out")
        except FileNotFoundError:
            return self._error_result("Playwright not found. Install with: pip install playwright")
        except Exception as e:
            return self._error_result(f"E2E test execution failed: {str(e)}")
    
    def get_results(self) -> Dict[str, Any]:
        """
        Retrieve accumulated test results.
        
        Returns:
            Dictionary containing all test results collected so far
        """
        return self.results
    
    def generate_report(self, output_path: str) -> None:
        """
        Generate HTML report of test results.
        
        Args:
            output_path: Path where the HTML report should be saved
        """
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        if self.report_format == "html":
            self._generate_html_report(output_path_obj)
        elif self.report_format == "json":
            self._generate_json_report(output_path_obj)
        elif self.report_format == "xml":
            self._generate_junit_xml_report(output_path_obj)
        else:
            raise ValueError(f"Unsupported report format: {self.report_format}")
    
    def cleanup(self) -> None:
        """
        Remove temporary test artifacts and clean up resources.
        """
        for artifact in self._artifacts:
            try:
                artifact_path = Path(artifact)
                if artifact_path.is_file():
                    artifact_path.unlink()
                elif artifact_path.is_dir():
                    shutil.rmtree(artifact_path)
            except Exception:
                pass
        
        self._artifacts.clear()
        
        cache_dirs = ["__pycache__", ".pytest_cache", ".coverage"]
        for cache_dir in cache_dirs:
            try:
                path = Path(self.temp_dir) / cache_dir
                if path.exists():
                    shutil.rmtree(path)
            except Exception:
                pass
    
    def _parse_pytest_output(self, results: Dict, output: str) -> None:
        """Parse pytest stdout to extract test counts."""
        lines = output.split("\n")
        for line in lines:
            if "passed" in line.lower() or "failed" in line.lower():
                parts = line.split()
                for i, part in enumerate(parts):
                    if "passed" in part.lower():
                        try:
                            results["passed_count"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
                    if "failed" in part.lower():
                        try:
                            results["failed_count"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
    
    def _parse_playwright_output(self, results: Dict, output: str) -> None:
        """Parse Playwright stdout to extract test counts."""
        lines = output.split("\n")
        for line in lines:
            if "passed" in line.lower():
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        results["passed_count"] = int(part)
                        break
    
    def _aggregate_results(self, test_results: List[Dict]) -> Dict:
        """Aggregate multiple test results into summary."""
        summary = {
            "total": len(test_results),
            "passed": sum(1 for r in test_results if r.get("passed", False)),
            "failed": sum(1 for r in test_results if not r.get("passed", True)),
            "duration": sum(r.get("duration", 0) for r in test_results)
        }
        self.results["summary"] = summary
        return summary
    
    def _error_result(self, message: str) -> Dict[str, Any]:
        """Create an error result dictionary."""
        return {
            "passed": False,
            "error": message,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_html_report(self, output_path: Path) -> None:
        """Generate HTML report file."""
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .card {{ background: #ecf0f1; padding: 15px; border-radius: 5px; flex: 1; }}
        .passed {{ color: #27ae60; }}
        .failed {{ color: #e74c3c; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #34495e; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Contract Kit Test Report</h1>
        <p>Generated: {datetime.now().isoformat()}</p>
    </div>
    <div class="summary">
        <div class="card">
            <h3>Total Tests</h3>
            <p>{self.results.get('summary', {}).get('total', 0)}</p>
        </div>
        <div class="card">
            <h3>Passed</h3>
            <p class="passed">{self.results.get('summary', {}).get('passed', 0)}</p>
        </div>
        <div class="card">
            <h3>Failed</h3>
            <p class="failed">{self.results.get('summary', {}).get('failed', 0)}</p>
        </div>
    </div>
    <h2>Test Details</h2>
    <pre>{json.dumps(self.results, indent=2)}</pre>
</body>
</html>"""
        output_path.write_text(html_content, encoding="utf-8")
    
    def _generate_json_report(self, output_path: Path) -> None:
        """Generate JSON report file."""
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "results": self.results
        }
        output_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    
    def _generate_junit_xml_report(self, output_path: Path) -> None:
        """Generate JUnit XML report file."""
        xml_lines = ['<?xml version="1.0" encoding="utf-8"?>']
        xml_lines.append('<testsuite>')
        
        for test_type, result in self.results.items():
            if isinstance(result, dict):
                xml_lines.append(f'  <testcase classname="{test_type}" ')
                xml_lines.append(f'    passed="{result.get("passed", False)}" ')
                xml_lines.append(f'    duration="{result.get("duration", 0)}"/>')
        
        xml_lines.append('</testsuite>')
        output_path.write_text("\n".join(xml_lines), encoding="utf-8")
