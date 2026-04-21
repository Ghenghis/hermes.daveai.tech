"""
Security Validator - Security scanning and vulnerability detection.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern


class SecurityValidator:
    """
    Security validation and vulnerability scanning for contracts.
    
    Provides input validation, injection detection, authentication
    verification, and dependency vulnerability scanning.
    """
    
    SQL_INJECTION_PATTERNS: List[Pattern] = [
        re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)", re.IGNORECASE),
        re.compile(r"(--|;|/\*|\*/|@@|@)"),
        re.compile(r"('|\"|;|=)"),
        re.compile(r"\bOR\b.*(=).*\bOR\b", re.IGNORECASE),
        re.compile(r"\bAND\b.*(=).*\bAND\b", re.IGNORECASE),
    ]
    
    XSS_PATTERNS: List[Pattern] = [
        re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),
        re.compile(r"<iframe[^>]*>.*?</iframe>", re.IGNORECASE | re.DOTALL),
        re.compile(r"<embed[^>]*>"),
        re.compile(r"<object[^>]*>.*?</object>", re.IGNORECASE | re.DOTALL),
    ]
    
    AUTH_TOKEN_PATTERNS: List[Pattern] = [
        re.compile(r"Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+"),
        re.compile(r"Bearer\s+[A-Za-z0-9\-_]{32,}"),
        re.compile(r"Bearer\s+[A-Za-z0-9\-_]{16,31}"),
    ]
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize security validator with configuration.
        
        Args:
            config: Configuration dictionary containing:
                - strict_mode: enable strict validation rules
                - check_dependencies: scan for vulnerable dependencies
                - report_format: format for reports (json, html, txt)
                - allowed_domains: list of allowed domains for validation
                - blocked_patterns: additional patterns to block
        """
        self.config = config
        self.strict_mode = config.get("strict_mode", True)
        self.check_dependencies = config.get("check_dependencies", True)
        self.report_format = config.get("report_format", "json")
        self.allowed_domains = config.get("allowed_domains", [])
        self.blocked_patterns = config.get("blocked_patterns", [])
        
        self._validation_history: List[Dict] = []
        self._vulnerabilities: List[Dict] = []
    
    def validate_input(self, data: Any, schema: Dict) -> bool:
        """
        Validate input data against a schema.
        
        Args:
            data: Input data to validate
            schema: Schema dictionary with validation rules:
                - type: expected type (str, int, float, bool, list, dict)
                - required: whether field is required
                - min_length: minimum length for strings
                - max_length: maximum length for strings
                - pattern: regex pattern for strings
                - min: minimum value for numbers
                - max: maximum value for numbers
                
        Returns:
            True if validation passes, False otherwise
        """
        if schema.get("required", False) and data is None:
            self._add_validation_result("validate_input", False, "Required field is missing")
            return False
        
        if data is None:
            return True
        
        expected_type = schema.get("type")
        if expected_type and not isinstance(data, eval(expected_type) if isinstance(expected_type, str) else expected_type):
            self._add_validation_result("validate_input", False, f"Type mismatch: expected {expected_type}")
            return False
        
        if isinstance(data, str):
            min_length = schema.get("min_length")
            if min_length and len(data) < min_length:
                self._add_validation_result("validate_input", False, f"String too short: {len(data)} < {min_length}")
                return False
            
            max_length = schema.get("max_length")
            if max_length and len(data) > max_length:
                self._add_validation_result("validate_input", False, f"String too long: {len(data)} > {max_length}")
                return False
            
            pattern = schema.get("pattern")
            if pattern and not re.match(pattern, data):
                self._add_validation_result("validate_input", False, "Pattern mismatch")
                return False
        
        if isinstance(data, (int, float)):
            min_val = schema.get("min")
            if min_val is not None and data < min_val:
                self._add_validation_result("validate_input", False, f"Value too small: {data} < {min_val}")
                return False
            
            max_val = schema.get("max")
            if max_val is not None and data > max_val:
                self._add_validation_result("validate_input", False, f"Value too large: {data} > {max_val}")
                return False
        
        self._add_validation_result("validate_input", True, "Validation passed")
        return True
    
    def check_sql_injection(self, query: str) -> bool:
        """
        Check if a query string contains potential SQL injection patterns.
        
        Args:
            query: SQL query string to check
            
        Returns:
            True if injection patterns detected, False if safe
        """
        if not query:
            self._add_validation_result("check_sql_injection", True, "Empty query")
            return False
        
        detected_patterns = []
        
        for pattern in self.SQL_INJECTION_PATTERNS:
            match = pattern.search(query)
            if match:
                detected_patterns.append({
                    "pattern": pattern.pattern,
                    "match": match.group(),
                    "position": match.start()
                })
        
        if detected_patterns:
            self._add_vulnerability("sql_injection", "SQL injection pattern detected", {
                "query_preview": query[:100],
                "detected_patterns": detected_patterns
            })
            self._add_validation_result("check_sql_injection", False, f"SQL injection detected: {len(detected_patterns)} patterns found")
            return True
        
        self._add_validation_result("check_sql_injection", True, "No SQL injection patterns detected")
        return False
    
    def check_xss(self, data: str) -> bool:
        """
        Check if string data contains potential XSS attack patterns.
        
        Args:
            data: String data to check
            
        Returns:
            True if XSS patterns detected, False if safe
        """
        if not data:
            self._add_validation_result("check_xss", True, "Empty data")
            return False
        
        detected_patterns = []
        
        for pattern in self.XSS_PATTERNS:
            match = pattern.search(data)
            if match:
                detected_patterns.append({
                    "pattern": pattern.pattern,
                    "match": match.group()[:50],
                    "position": match.start()
                })
        
        if detected_patterns:
            self._add_vulnerability("xss", "XSS pattern detected", {
                "data_preview": data[:100],
                "detected_patterns": detected_patterns
            })
            self._add_validation_result("check_xss", False, f"XSS detected: {len(detected_patterns)} patterns found")
            return True
        
        self._add_validation_result("check_xss", True, "No XSS patterns detected")
        return False
    
    def validate_auth(self, token: str) -> Dict[str, Any]:
        """
        Validate authentication token format and structure.
        
        Args:
            token: Authentication token string
            
        Returns:
            Dictionary containing:
                - valid: boolean indicating if token is valid
                - token_type: detected token type
                - components: parsed token components
                - issues: list of validation issues
        """
        result = {
            "valid": False,
            "token_type": None,
            "components": {},
            "issues": [],
            "timestamp": datetime.now().isoformat()
        }
        
        if not token:
            result["issues"].append("Empty token")
            self._add_validation_result("validate_auth", False, "Empty token")
            return result
        
        token = token.strip()
        
        if token.startswith("Bearer "):
            result["token_type"] = "bearer"
            token = token[7:]
        
        for pattern in self.AUTH_TOKEN_PATTERNS:
            if pattern.match(f"Bearer {token}"):
                result["token_type"] = "jwt" if "." in token else "opaque"
                
                if "." in token:
                    parts = token.split(".")
                    if len(parts) == 3:
                        result["components"] = {
                            "header": parts[0],
                            "payload": parts[1],
                            "signature": parts[2]
                        }
                        result["valid"] = True
                    else:
                        result["issues"].append("Invalid JWT structure")
                else:
                    result["components"] = {"token": token}
                    result["valid"] = len(token) >= 32
                
                break
        
        if result["token_type"] is None:
            result["issues"].append("Unrecognized token format")
        
        if self.strict_mode and not result["valid"]:
            result["issues"].append("Strict mode validation failed")
        
        self._add_validation_result(
            "validate_auth",
            result["valid"],
            "; ".join(result["issues"]) if result["issues"] else "Token valid"
        )
        
        return result
    
    def scan_dependencies(self) -> List[Dict[str, Any]]:
        """
        Scan project dependencies for known vulnerabilities.
        
        Returns:
            List of vulnerability dictionaries with details
        """
        vulnerabilities = []
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=freeze"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                packages = []
                for line in result.stdout.split("\n"):
                    if "==" in line:
                        pkg, version = line.strip().split("==")
                        packages.append({"name": pkg, "version": version})
                
                vulnerabilities.extend(self._check_known_vulnerabilities(packages))
                
        except Exception as e:
            vulnerabilities.append({
                "severity": "error",
                "package": "unknown",
                "description": f"Failed to scan dependencies: {str(e)}"
            })
        
        self._vulnerabilities.extend(vulnerabilities)
        return vulnerabilities
    
    def _check_known_vulnerabilities(self, packages: List[Dict]) -> List[Dict]:
        """Check packages against known vulnerability database."""
        known_issues = {
            "requests": ["<2.20.0"],
            "urllib3": ["<1.26.0"],
            "setuptools": ["<58.0.0"],
            "jinja2": ["<3.0.0"],
            "flask": ["<2.0.0"],
            "django": ["<3.2.0", "<4.0.0"],
        }
        
        vulnerabilities = []
        
        for pkg in packages:
            pkg_name = pkg["name"].lower()
            pkg_version = pkg["version"]
            
            if pkg_name in known_issues:
                for affected_range in known_issues[pkg_name]:
                    if self._version_affected(pkg_version, affected_range):
                        vulnerabilities.append({
                            "severity": "high",
                            "package": pkg_name,
                            "current_version": pkg_version,
                            "affected_versions": affected_range,
                            "description": f"Known vulnerability in {pkg_name} {affected_range}",
                            "recommendation": f"Upgrade {pkg_name} to latest version"
                        })
        
        return vulnerabilities
    
    def _version_affected(self, version: str, affected_range: str) -> bool:
        """Check if version is in affected range."""
        try:
            current = tuple(map(int, version.split(".")[:3]))
            
            if affected_range.startswith("<"):
                threshold = affected_range[1:]
                threshold_tuple = tuple(map(int, threshold.split(".")[:3]))
                return current < threshold_tuple
            
            return False
        except (ValueError, IndexError):
            return False
    
    def generate_security_report(self, output_path: str) -> None:
        """
        Generate comprehensive security report.
        
        Args:
            output_path: Path where the security report should be saved
        """
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "scan_config": {
                "strict_mode": self.strict_mode,
                "check_dependencies": self.check_dependencies,
                "allowed_domains": self.allowed_domains
            },
            "validation_history": self._validation_history,
            "vulnerabilities": self._vulnerabilities,
            "summary": {
                "total_validations": len(self._validation_history),
                "passed": sum(1 for v in self._validation_history if v["passed"]),
                "failed": sum(1 for v in self._validation_history if not v["passed"]),
                "total_vulnerabilities": len(self._vulnerabilities),
                "high_severity": sum(1 for v in self._vulnerabilities if v.get("severity") == "high"),
                "medium_severity": sum(1 for v in self._vulnerabilities if v.get("severity") == "medium"),
                "low_severity": sum(1 for v in self._vulnerabilities if v.get("severity") == "low")
            }
        }
        
        if self.report_format == "json" or output_path_obj.suffix == ".json":
            output_path_obj.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
        elif self.report_format == "html" or output_path_obj.suffix == ".html":
            self._generate_html_report(output_path_obj, report_data)
        elif self.report_format == "txt" or output_path_obj.suffix == ".txt":
            self._generate_text_report(output_path_obj, report_data)
        else:
            output_path_obj.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    
    def _add_validation_result(self, check_type: str, passed: bool, message: str) -> None:
        """Add validation result to history."""
        self._validation_history.append({
            "check_type": check_type,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def _add_vulnerability(self, vuln_type: str, description: str, details: Dict) -> None:
        """Add vulnerability to tracked vulnerabilities."""
        self._vulnerabilities.append({
            "type": vuln_type,
            "description": description,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def _generate_html_report(self, output_path: Path, report_data: Dict) -> None:
        """Generate HTML security report."""
        summary = report_data["summary"]
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Security Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #2c3e50; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .card {{ padding: 20px; border-radius: 8px; flex: 1; text-align: center; }}
        .card.success {{ background: #d4edda; }}
        .card.danger {{ background: #f8d7da; }}
        .card.warning {{ background: #fff3cd; }}
        .vuln-list {{ margin-top: 20px; }}
        .vuln-item {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #dc3545; }}
        .vuln-item.high {{ border-left-color: #dc3545; }}
        .vuln-item.medium {{ border-left-color: #ffc107; }}
        .vuln-item.low {{ border-left-color: #17a2b8; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Security Validation Report</h1>
        <p>Generated: {report_data['generated_at']}</p>
        
        <div class="summary">
            <div class="card success">
                <h3>Passed</h3>
                <p>{summary['passed']}</p>
            </div>
            <div class="card danger">
                <h3>Failed</h3>
                <p>{summary['failed']}</p>
            </div>
            <div class="card warning">
                <h3>Vulnerabilities</h3>
                <p>{summary['total_vulnerabilities']}</p>
            </div>
        </div>
        
        <h2>Vulnerabilities</h2>
        <div class="vuln-list">
"""
        
        for vuln in report_data["vulnerabilities"]:
            severity = vuln.get("severity", "low")
            html_content += f"""
            <div class="vuln-item {severity}">
                <strong>{vuln.get('description', 'Unknown vulnerability')}</strong>
                <p>Package: {vuln.get('package', 'N/A')}</p>
                <p>Severity: {severity.upper()}</p>
            </div>
"""
        
        html_content += """
        </div>
    </div>
</body>
</html>"""
        
        output_path.write_text(html_content, encoding="utf-8")
    
    def _generate_text_report(self, output_path: Path, report_data: Dict) -> None:
        """Generate plain text security report."""
        lines = [
            "=" * 60,
            "SECURITY VALIDATION REPORT",
            "=" * 60,
            f"Generated: {report_data['generated_at']}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Validations: {report_data['summary']['total_validations']}",
            f"Passed: {report_data['summary']['passed']}",
            f"Failed: {report_data['summary']['failed']}",
            f"Total Vulnerabilities: {report_data['summary']['total_vulnerabilities']}",
            "",
            "VULNERABILITIES",
            "-" * 40
        ]
        
        for vuln in report_data["vulnerabilities"]:
            lines.append(f"  [{vuln.get('severity', 'unknown').upper()}] {vuln.get('description', 'Unknown')}")
            lines.append(f"    Package: {vuln.get('package', 'N/A')}")
        
        output_path.write_text("\n".join(lines), encoding="utf-8")
