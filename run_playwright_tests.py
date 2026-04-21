#!/usr/bin/env python3
"""
Comprehensive Playwright Test Runner for Contract Kit V17

Runs all Playwright E2E tests including:
- WebUI basic functionality (test_webui.py)
- Auto-fill features (test_webui_autofill.py)
- Visual regression tests
- Integration workflows

Usage:
    python run_playwright_tests.py --all
    python run_playwright_tests.py --autofill-only
    python run_playwright_tests.py --visual-only
    python run_playwright_tests.py --headed
"""

import argparse
import asyncio
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


class PlaywrightTestRunner:
    """Orchestrates Playwright test execution with reporting."""
    
    def __init__(self, headed: bool = False, debug: bool = False):
        self.headed = headed
        self.debug = debug
        self.results: Dict[str, Any] = {}
        self.start_time: datetime = None
        
    async def check_dependencies(self) -> bool:
        """Verify all dependencies are installed."""
        print("🔍 Checking dependencies...")
        
        # Check Node.js
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"  ✓ Node.js: {result.stdout.strip()}")
            else:
                print("  ✗ Node.js not found")
                return False
        except Exception as e:
            print(f"  ✗ Node.js check failed: {e}")
            return False
        
        # Check Playwright browsers
        try:
            result = subprocess.run(
                ["npx", "playwright", "install", "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print("  ✓ Playwright CLI available")
            else:
                print("  ⚠ Playwright browsers may need installation")
                print("    Run: npx playwright install")
        except Exception as e:
            print(f"  ⚠ Playwright check: {e}")
        
        # Check Python playwright
        try:
            from playwright.async_api import async_playwright
            print("  ✓ Python Playwright installed")
        except ImportError:
            print("  ✗ Python Playwright not installed")
            print("    Run: pip install pytest-playwright playwright")
            return False
        
        return True
    
    async def install_browsers(self) -> bool:
        """Install Playwright browsers if needed."""
        print("\n📦 Installing Playwright browsers...")
        
        try:
            result = subprocess.run(
                ["npx", "playwright", "install", "chromium"],
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                print("  ✓ Chromium browser installed")
                return True
            else:
                print(f"  ✗ Browser installation failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"  ✗ Browser installation error: {e}")
            return False
    
    async def run_test_suite(self, test_pattern: str, suite_name: str) -> Dict[str, Any]:
        """Run a specific test suite."""
        print(f"\n🧪 Running {suite_name}...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            test_pattern,
            "-v",
            "--tb=short",
            f"--html=test-results/{suite_name.lower().replace(' ', '_')}_report.html",
            "--self-contained-html",
            "-W", "ignore::DeprecationWarning"
        ]
        
        if self.headed:
            cmd.append("--headed")
        
        if self.debug:
            cmd.append("--pdb")
        
        start = datetime.now()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                cwd=Path(__file__).parent
            )
            
            duration = (datetime.now() - start).total_seconds()
            
            # Parse results
            passed = result.stdout.count("PASSED")
            failed = result.stdout.count("FAILED")
            error = result.stdout.count("ERROR")
            
            suite_result = {
                "name": suite_name,
                "passed": passed,
                "failed": failed,
                "error": error,
                "duration": duration,
                "returncode": result.returncode,
                "stdout": result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout,
                "stderr": result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr
            }
            
            status = "✅" if result.returncode == 0 else "❌"
            print(f"  {status} {suite_name}: {passed} passed, {failed} failed ({duration:.1f}s)")
            
            return suite_result
            
        except subprocess.TimeoutExpired:
            print(f"  ⏱️ {suite_name}: Timeout after 600s")
            return {
                "name": suite_name,
                "passed": 0,
                "failed": 0,
                "error": 1,
                "duration": 600,
                "returncode": -1,
                "stdout": "",
                "stderr": "Timeout"
            }
        except Exception as e:
            print(f"  💥 {suite_name}: Exception - {e}")
            return {
                "name": suite_name,
                "passed": 0,
                "failed": 0,
                "error": 1,
                "duration": 0,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e)
            }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all Playwright test suites."""
        self.start_time = datetime.now()
        
        # Create test results directory
        results_dir = Path("test-results")
        results_dir.mkdir(exist_ok=True)
        
        suites = [
            ("tests/e2e/test_webui.py", "WebUI Basic"),
            ("tests/e2e/test_webui_autofill.py", "Auto-Fill Features"),
            ("tests/e2e/test_kilocode.py", "KiloCode Integration"),
            ("tests/e2e/test_runtime.py", "Runtime API"),
            ("tests/e2e/test_hermes.py", "Hermes Orchestrator"),
        ]
        
        all_results = []
        for pattern, name in suites:
            if Path(pattern).exists():
                result = await self.run_test_suite(pattern, name)
                all_results.append(result)
            else:
                print(f"  ⚠️ Skipping {name}: {pattern} not found")
        
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        # Calculate summary
        total_passed = sum(r["passed"] for r in all_results)
        total_failed = sum(r["failed"] for r in all_results)
        total_error = sum(r["error"] for r in all_results)
        
        summary = {
            "total_suites": len(all_results),
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_error": total_error,
            "total_duration": total_duration,
            "all_passed": all(r["returncode"] == 0 for r in all_results),
            "suites": all_results
        }
        
        return summary
    
    async def run_autofill_only(self) -> Dict[str, Any]:
        """Run only auto-fill tests."""
        self.start_time = datetime.now()
        
        results_dir = Path("test-results")
        results_dir.mkdir(exist_ok=True)
        
        result = await self.run_test_suite(
            "tests/e2e/test_webui_autofill.py",
            "Auto-Fill Features"
        )
        
        return {
            "total_suites": 1,
            "total_passed": result["passed"],
            "total_failed": result["failed"],
            "total_error": result["error"],
            "total_duration": result["duration"],
            "all_passed": result["returncode"] == 0,
            "suites": [result]
        }
    
    def print_report(self, summary: Dict[str, Any]):
        """Print formatted test report."""
        print("\n" + "=" * 60)
        print("📊 PLAYWRIGHT TEST REPORT")
        print("=" * 60)
        
        print(f"\nTotal Suites: {summary['total_suites']}")
        print(f"Total Tests: {summary['total_passed'] + summary['total_failed'] + summary['total_error']}")
        print(f"  ✅ Passed: {summary['total_passed']}")
        print(f"  ❌ Failed: {summary['total_failed']}")
        print(f"  💥 Errors: {summary['total_error']}")
        print(f"\n⏱️  Total Duration: {summary['total_duration']:.1f}s")
        
        if summary['all_passed']:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print("\n⚠️  SOME TESTS FAILED")
            print("\nFailed Suites:")
            for suite in summary['suites']:
                if suite['returncode'] != 0:
                    print(f"  - {suite['name']}: {suite['failed']} failed, {suite['error']} errors")
        
        print("\n📁 Reports generated:")
        print("  - test-results/*_report.html")
        print("=" * 60)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Playwright E2E tests for Contract Kit V17"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all test suites"
    )
    parser.add_argument(
        "--autofill-only",
        action="store_true",
        help="Run only auto-fill tests"
    )
    parser.add_argument(
        "--visual-only",
        action="store_true",
        help="Run only visual regression tests"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run tests in headed mode (visible browser)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (pdb on failure)"
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install Playwright browsers only"
    )
    
    args = parser.parse_args()
    
    runner = PlaywrightTestRunner(headed=args.headed, debug=args.debug)
    
    # Check dependencies
    if not await runner.check_dependencies():
        print("\n❌ Dependency check failed. Please install missing dependencies.")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)
    
    # Install browsers if requested
    if args.install:
        success = await runner.install_browsers()
        sys.exit(0 if success else 1)
    
    # Default to --all if no specific option given
    if not any([args.all, args.autofill_only, args.visual_only]):
        args.all = True
    
    # Run tests
    if args.autofill_only:
        summary = await runner.run_autofill_only()
    elif args.visual_only:
        # For visual tests, filter by test name
        summary = await runner.run_test_suite(
            "tests/e2e/test_webui_autofill.py -k 'visual'",
            "Visual Regression"
        )
        summary = {
            "total_suites": 1,
            "total_passed": summary["passed"],
            "total_failed": summary["failed"],
            "total_error": summary["error"],
            "total_duration": summary["duration"],
            "all_passed": summary["returncode"] == 0,
            "suites": [summary]
        }
    else:
        summary = await runner.run_all_tests()
    
    # Print report
    runner.print_report(summary)
    
    # Exit with appropriate code
    sys.exit(0 if summary['all_passed'] else 1)


if __name__ == "__main__":
    asyncio.run(main())
