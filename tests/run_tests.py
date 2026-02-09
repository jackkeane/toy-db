#!/usr/bin/env python3
"""
ToyDB Test Runner

Runs all tests and generates detailed reports in JSON and Markdown formats.
"""
import sys
import os
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRunner:
    """Runs tests and collects results"""
    
    def __init__(self, output_dir="test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "test_suites": []
        }
    
    def run_pytest(self, test_path, suite_name):
        """Run pytest on a specific path and collect results"""
        print(f"\n{'='*60}")
        print(f"Running {suite_name}...")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        # Run pytest with JSON report
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_path),
            "-v",
            "--tb=short",
            "--json-report",
            f"--json-report-file={self.output_dir / f'{suite_name}.json'}"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        duration = time.time() - start_time
        
        # Parse output for basic stats
        output = result.stdout + result.stderr
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        skipped = output.count(" SKIPPED")
        
        suite_result = {
            "name": suite_name,
            "path": str(test_path),
            "duration": round(duration, 2),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total": passed + failed + skipped,
            "exit_code": result.returncode,
            "output": output[:5000]  # Truncate long output
        }
        
        self.results["test_suites"].append(suite_result)
        
        # Print summary
        print(f"\n{suite_name} Results:")
        print(f"  ✓ Passed:  {passed}")
        print(f"  ✗ Failed:  {failed}")
        print(f"  ⊘ Skipped: {skipped}")
        print(f"  Duration:  {duration:.2f}s")
        
        return suite_result
    
    def run_all_tests(self):
        """Run all test suites"""
        tests_dir = Path(__file__).parent
        
        # Define test suites
        suites = [
            (tests_dir / "unit", "Unit Tests"),
            (tests_dir / "integration", "Integration Tests"),
            (tests_dir / "performance", "Performance Tests"),
        ]
        
        for test_path, suite_name in suites:
            if test_path.exists():
                self.run_pytest(test_path, suite_name.lower().replace(" ", "_"))
        
        # Calculate summary
        total_passed = sum(s["passed"] for s in self.results["test_suites"])
        total_failed = sum(s["failed"] for s in self.results["test_suites"])
        total_skipped = sum(s["skipped"] for s in self.results["test_suites"])
        total_duration = sum(s["duration"] for s in self.results["test_suites"])
        
        self.results["summary"] = {
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "total_tests": total_passed + total_failed + total_skipped,
            "total_duration": round(total_duration, 2),
            "success_rate": round(100 * total_passed / max(1, total_passed + total_failed), 2)
        }
    
    def save_json_report(self):
        """Save results as JSON"""
        output_file = self.output_dir / "test_report.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n✓ JSON report saved to: {output_file}")
    
    def save_markdown_report(self):
        """Save results as Markdown"""
        output_file = self.output_dir / "test_report.md"
        
        md = []
        md.append("# ToyDB Test Report\n")
        md.append(f"**Generated:** {self.results['timestamp']}\n")
        md.append("---\n")
        
        # Summary
        summary = self.results["summary"]
        md.append("## Summary\n")
        md.append(f"- **Total Tests:** {summary['total_tests']}")
        md.append(f"- **Passed:** ✓ {summary['total_passed']}")
        md.append(f"- **Failed:** ✗ {summary['total_failed']}")
        md.append(f"- **Skipped:** ⊘ {summary['total_skipped']}")
        md.append(f"- **Success Rate:** {summary['success_rate']}%")
        md.append(f"- **Total Duration:** {summary['total_duration']}s\n")
        
        # Suite results
        md.append("## Test Suites\n")
        for suite in self.results["test_suites"]:
            status = "✓ PASS" if suite["exit_code"] == 0 else "✗ FAIL"
            md.append(f"### {suite['name']} {status}\n")
            md.append(f"- **Path:** `{suite['path']}`")
            md.append(f"- **Duration:** {suite['duration']}s")
            md.append(f"- **Tests:** {suite['total']} (✓{suite['passed']} ✗{suite['failed']} ⊘{suite['skipped']})\n")
            
            if suite["failed"] > 0 and suite["output"]:
                md.append("<details>")
                md.append(f"<summary>Output (truncated)</summary>\n")
                md.append("```")
                md.append(suite["output"])
                md.append("```")
                md.append("</details>\n")
        
        # System info
        md.append("## Environment\n")
        md.append(f"- **Python:** {sys.version.split()[0]}")
        md.append(f"- **Platform:** {sys.platform}")
        md.append(f"- **Working Directory:** `{os.getcwd()}`\n")
        
        with open(output_file, "w") as f:
            f.write("\n".join(md))
        
        print(f"✓ Markdown report saved to: {output_file}")
    
    def print_summary(self):
        """Print final summary"""
        print("\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)
        
        summary = self.results["summary"]
        print(f"\nTotal Tests:   {summary['total_tests']}")
        print(f"Passed:        ✓ {summary['total_passed']}")
        print(f"Failed:        ✗ {summary['total_failed']}")
        print(f"Skipped:       ⊘ {summary['total_skipped']}")
        print(f"Success Rate:  {summary['success_rate']}%")
        print(f"Duration:      {summary['total_duration']}s")
        print()


def main():
    """Main entry point"""
    runner = TestRunner()
    
    try:
        runner.run_all_tests()
        runner.save_json_report()
        runner.save_markdown_report()
        runner.print_summary()
        
        # Exit with error if tests failed
        if runner.results["summary"]["total_failed"] > 0:
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
