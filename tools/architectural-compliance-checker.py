#!/usr/bin/env python3
"""
Architectural Compliance Checker

Automated tool to detect architectural boundary violations in the Canvas-Tracker-V3 codebase.
This tool scans for patterns that violate the clean architecture principles established
in the architectural analysis report.

Usage:
    python tools/architectural-compliance-checker.py
    python tools/architectural-compliance-checker.py --component canvas-interface
    python tools/architectural-compliance-checker.py --fix-violations
"""

import os
import sys
import re
import ast
import argparse
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class ViolationType(Enum):
    """Types of architectural violations."""
    FILE_SYSTEM_IN_CANVAS_INTERFACE = "file_system_in_canvas_interface"
    IMPROPER_IMPORTS = "improper_imports"
    LAYER_BOUNDARY_VIOLATION = "layer_boundary_violation"
    DEBUG_CODE_IN_PRODUCTION = "debug_code_in_production"
    CONFIGURATION_IN_WRONG_LAYER = "configuration_in_wrong_layer"


@dataclass
class Violation:
    """Represents an architectural violation."""
    type: ViolationType
    file_path: Path
    line_number: int
    line_content: str
    description: str
    severity: str  # 'critical', 'warning', 'info'
    auto_fixable: bool = False
    suggested_fix: Optional[str] = None


class ArchitecturalComplianceChecker:
    """Main compliance checker class."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations: List[Violation] = []
        
        # Define architectural boundaries and rules
        self.component_boundaries = {
            'canvas-interface': {
                'allowed_operations': ['console.log', 'fetch', 'api_calls'],
                'forbidden_operations': ['fs.writeFileSync', 'fs.readFileSync', 'fs.writeFile'],
                'allowed_imports': ['axios', 'node-fetch', './types/', './utils/'],
                'forbidden_imports': ['fs', 'path', 'os']
            },
            'database': {
                'allowed_operations': ['sqlalchemy', 'logging', 'datetime'],
                'forbidden_operations': ['subprocess', 'os.system'],
                'layer_rules': {
                    'layer1': 'no_forward_references_to_layer2',
                    'layer2': 'no_references_to_layer3',
                    'base': 'no_business_logic'
                }
            }
        }
    
    def run_compliance_check(self, component_filter: Optional[str] = None) -> Dict[str, any]:
        """Run comprehensive compliance check."""
        print("🔍 Starting Architectural Compliance Check...")
        print(f"📁 Project root: {self.project_root}")
        
        if component_filter:
            print(f"🎯 Filtering to component: {component_filter}")
        
        # Check different components
        if not component_filter or component_filter == 'canvas-interface':
            self._check_canvas_interface_compliance()
        
        if not component_filter or component_filter == 'database':
            self._check_database_compliance()
        
        if not component_filter or component_filter == 'general':
            self._check_general_compliance()
        
        # Generate report
        return self._generate_report()
    
    def _check_canvas_interface_compliance(self):
        """Check Canvas interface architectural compliance."""
        print("🎨 Checking Canvas interface compliance...")
        
        canvas_dir = self.project_root / 'canvas-interface'
        if not canvas_dir.exists():
            print(f"⚠️ Canvas interface directory not found: {canvas_dir}")
            return
        
        # Check TypeScript files for violations
        for ts_file in canvas_dir.rglob('*.ts'):
            self._check_typescript_file_compliance(ts_file)
        
        # Check JavaScript files for violations
        for js_file in canvas_dir.rglob('*.js'):
            self._check_javascript_file_compliance(js_file)
    
    def _check_typescript_file_compliance(self, file_path: Path):
        """Check individual TypeScript file for compliance."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            for i, line in enumerate(lines, 1):
                self._check_line_for_file_system_operations(file_path, i, line)
                self._check_line_for_debug_code(file_path, i, line)
                self._check_line_for_improper_imports(file_path, i, line)
                
        except Exception as e:
            print(f"⚠️ Error checking {file_path}: {e}")
    
    def _check_javascript_file_compliance(self, file_path: Path):
        """Check individual JavaScript file for compliance."""
        # Similar to TypeScript but for JS files
        self._check_typescript_file_compliance(file_path)  # Same logic applies
    
    def _check_line_for_file_system_operations(self, file_path: Path, line_num: int, line: str):
        """Check line for prohibited file system operations."""
        # Check for file system operations in Canvas interface
        if 'canvas-interface' in str(file_path):
            fs_patterns = [
                r'fs\.writeFileSync\s*\(',
                r'fs\.readFileSync\s*\(',
                r'fs\.writeFile\s*\(',
                r'fs\.readFile\s*\(',
                r'require\s*\(\s*[\'"]fs[\'"]\s*\)',
                r'import.*from\s*[\'"]fs[\'"]',
                r'\.writeFileSync\s*\(',
                r'\.readFileSync\s*\(',
            ]
            
            for pattern in fs_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip if this is in a demo/archive/test file (these are allowed)
                    if any(x in str(file_path).lower() for x in ['demo', 'archive', 'test']):
                        continue
                    
                    self.violations.append(Violation(
                        type=ViolationType.FILE_SYSTEM_IN_CANVAS_INTERFACE,
                        file_path=file_path,
                        line_number=line_num,
                        line_content=line.strip(),
                        description=f"File system operation found in Canvas interface: {pattern}",
                        severity="critical",
                        auto_fixable=True,
                        suggested_fix="Remove file system operation or move to dedicated utility script"
                    ))
    
    def _check_line_for_debug_code(self, file_path: Path, line_num: int, line: str):
        """Check line for debug code patterns."""
        debug_patterns = [
            r'console\.debug\(',
            r'fs\.writeFileSync\([^)]*debug[^)]*\)',
            r'\.txt[\'"],.*debug',
            r'debug\.log',
            r'// TODO.*debug',
            r'// FIXME.*debug',
            r'\.writeFileSync\([^)]*\.txt',  # Writing to .txt files often debug
        ]
        
        for pattern in debug_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # Skip legitimate logging and test files
                if any(x in str(file_path).lower() for x in ['test', 'spec', 'demo']):
                    continue
                if 'console.log' in line and 'debug' not in line.lower():
                    continue
                
                self.violations.append(Violation(
                    type=ViolationType.DEBUG_CODE_IN_PRODUCTION,
                    file_path=file_path,
                    line_number=line_num,
                    line_content=line.strip(),
                    description=f"Debug code detected: {pattern}",
                    severity="warning",
                    auto_fixable=True,
                    suggested_fix="Remove debug code or replace with proper logging"
                ))
    
    def _check_line_for_improper_imports(self, file_path: Path, line_num: int, line: str):
        """Check line for improper import statements."""
        if 'canvas-interface' in str(file_path):
            # Check for improper imports in Canvas interface
            forbidden_imports = ['fs', 'path', 'os']
            
            import_patterns = [
                r'import.*from\s*[\'"]({})[\'"]]'.format('|'.join(forbidden_imports)),
                r'require\s*\(\s*[\'"]({})[\'"]\s*\)'.format('|'.join(forbidden_imports))
            ]
            
            for pattern in import_patterns:
                if re.search(pattern, line):
                    # Skip demo and test files
                    if any(x in str(file_path).lower() for x in ['demo', 'archive', 'test']):
                        continue
                    
                    self.violations.append(Violation(
                        type=ViolationType.IMPROPER_IMPORTS,
                        file_path=file_path,
                        line_number=line_num,
                        line_content=line.strip(),
                        description=f"Improper import in Canvas interface: {pattern}",
                        severity="critical",
                        auto_fixable=False,
                        suggested_fix="Remove forbidden import or move functionality to appropriate layer"
                    ))
    
    def _check_database_compliance(self):
        """Check database layer architectural compliance."""
        print("🗄️ Checking database layer compliance...")
        
        database_dir = self.project_root / 'database'
        if not database_dir.exists():
            print(f"⚠️ Database directory not found: {database_dir}")
            return
        
        # Check Python files for violations
        for py_file in database_dir.rglob('*.py'):
            self._check_python_file_compliance(py_file)
    
    def _check_python_file_compliance(self, file_path: Path):
        """Check individual Python file for compliance."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            for i, line in enumerate(lines, 1):
                self._check_python_line_compliance(file_path, i, line)
                
            # Parse AST for more complex checks
            try:
                tree = ast.parse(content)
                self._check_python_ast_compliance(file_path, tree)
            except SyntaxError:
                pass  # Skip files with syntax errors
                
        except Exception as e:
            print(f"⚠️ Error checking {file_path}: {e}")
    
    def _check_python_line_compliance(self, file_path: Path, line_num: int, line: str):
        """Check Python line for compliance issues."""
        # Check for subprocess usage in inappropriate contexts
        if 'subprocess' in line and 'operations' in str(file_path):
            if not any(x in str(file_path) for x in ['typescript_interface', 'canvas_bridge']):
                self.violations.append(Violation(
                    type=ViolationType.LAYER_BOUNDARY_VIOLATION,
                    file_path=file_path,
                    line_number=line_num,
                    line_content=line.strip(),
                    description="Subprocess usage in inappropriate database layer",
                    severity="warning",
                    auto_fixable=False,
                    suggested_fix="Move subprocess operations to integration layer"
                ))
    
    def _check_python_ast_compliance(self, file_path: Path, tree: ast.AST):
        """Check Python AST for complex compliance issues."""
        # Check for layer boundary violations in imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._check_import_compliance(file_path, node.lineno, alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._check_import_compliance(file_path, node.lineno, node.module)
    
    def _check_import_compliance(self, file_path: Path, line_num: int, import_name: str):
        """Check if import respects layer boundaries."""
        # Example: Layer 1 should not import Layer 2
        if 'layer1' in str(file_path) and 'layer2' in import_name:
            self.violations.append(Violation(
                type=ViolationType.LAYER_BOUNDARY_VIOLATION,
                file_path=file_path,
                line_number=line_num,
                line_content=f"import {import_name}",
                description="Layer 1 importing from Layer 2 (forward dependency)",
                severity="critical",
                auto_fixable=False,
                suggested_fix="Restructure to avoid forward dependencies between layers"
            ))
    
    def _check_general_compliance(self):
        """Check general architectural compliance."""
        print("🏗️ Checking general architectural compliance...")
        
        # Check for proper directory structure
        self._check_directory_structure()
    
    def _check_directory_structure(self):
        """Check if directory structure follows architectural principles."""
        expected_dirs = [
            'canvas-interface',
            'database',
            'docs',
            'tools'
        ]
        
        for dir_name in expected_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                print(f"⚠️ Missing expected directory: {dir_name}")
    
    def _generate_report(self) -> Dict[str, any]:
        """Generate compliance report."""
        print("\n📊 Generating Compliance Report...")
        
        # Count violations by type and severity
        violation_counts = {
            'critical': len([v for v in self.violations if v.severity == 'critical']),
            'warning': len([v for v in self.violations if v.severity == 'warning']),
            'info': len([v for v in self.violations if v.severity == 'info']),
            'total': len(self.violations)
        }
        
        # Group violations by type
        violations_by_type = {}
        for violation in self.violations:
            violation_type = violation.type.value
            if violation_type not in violations_by_type:
                violations_by_type[violation_type] = []
            violations_by_type[violation_type].append(violation)
        
        # Auto-fixable violations
        auto_fixable_count = len([v for v in self.violations if v.auto_fixable])
        
        report = {
            'summary': {
                'total_violations': violation_counts['total'],
                'critical_violations': violation_counts['critical'],
                'warning_violations': violation_counts['warning'],
                'info_violations': violation_counts['info'],
                'auto_fixable_violations': auto_fixable_count
            },
            'violations_by_type': violations_by_type,
            'violations': self.violations
        }
        
        return report
    
    def print_report(self, report: Dict[str, any]):
        """Print formatted compliance report."""
        print("\n" + "="*60)
        print("🏗️ ARCHITECTURAL COMPLIANCE REPORT")
        print("="*60)
        
        summary = report['summary']
        
        # Overall status
        if summary['critical_violations'] == 0:
            status = "✅ COMPLIANT"
            status_color = "green"
        elif summary['critical_violations'] <= 2:
            status = "⚠️ MINOR ISSUES"
            status_color = "yellow"
        else:
            status = "❌ NON-COMPLIANT"
            status_color = "red"
        
        print(f"Overall Status: {status}")
        print()
        
        # Summary statistics
        print("📊 Summary:")
        print(f"  Total Violations: {summary['total_violations']}")
        print(f"  Critical: {summary['critical_violations']}")
        print(f"  Warning: {summary['warning_violations']}")
        print(f"  Info: {summary['info_violations']}")
        print(f"  Auto-fixable: {summary['auto_fixable_violations']}")
        print()
        
        # Violations by type
        if report['violations_by_type']:
            print("🔍 Violations by Type:")
            for violation_type, violations in report['violations_by_type'].items():
                print(f"  {violation_type}: {len(violations)} violations")
        print()
        
        # Detailed violations
        if self.violations:
            print("📋 Detailed Violations:")
            print("-" * 60)
            
            for violation in self.violations:
                severity_emoji = {
                    'critical': '🔴',
                    'warning': '🟡',
                    'info': '🔵'
                }.get(violation.severity, '⚪')
                
                print(f"{severity_emoji} {violation.severity.upper()}: {violation.description}")
                print(f"   File: {violation.file_path}")
                print(f"   Line {violation.line_number}: {violation.line_content}")
                if violation.suggested_fix:
                    print(f"   💡 Suggested fix: {violation.suggested_fix}")
                print()
        
        # Recommendations
        print("💡 Recommendations:")
        if summary['critical_violations'] > 0:
            print("  1. Address critical violations immediately")
        if summary['auto_fixable_violations'] > 0:
            print(f"  2. Run with --fix-violations to auto-fix {summary['auto_fixable_violations']} violations")
        if summary['total_violations'] == 0:
            print("  🎉 Congratulations! No violations found.")
        print()
    
    def fix_violations(self, dry_run: bool = True) -> int:
        """Attempt to auto-fix violations."""
        print(f"🔧 {'Simulating' if dry_run else 'Applying'} automatic fixes...")
        
        auto_fixable = [v for v in self.violations if v.auto_fixable]
        if not auto_fixable:
            print("No auto-fixable violations found.")
            return 0
        
        fixes_applied = 0
        
        for violation in auto_fixable:
            if violation.type == ViolationType.FILE_SYSTEM_IN_CANVAS_INTERFACE:
                if self._fix_file_system_violation(violation, dry_run):
                    fixes_applied += 1
            elif violation.type == ViolationType.DEBUG_CODE_IN_PRODUCTION:
                if self._fix_debug_code_violation(violation, dry_run):
                    fixes_applied += 1
        
        print(f"{'Would fix' if dry_run else 'Fixed'} {fixes_applied} violations")
        return fixes_applied
    
    def _fix_file_system_violation(self, violation: Violation, dry_run: bool) -> bool:
        """Fix file system operation violations."""
        if dry_run:
            print(f"  Would remove file system operation in {violation.file_path}:{violation.line_number}")
            return True
        
        try:
            # Read file
            with open(violation.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Comment out or replace the problematic line
            original_line = lines[violation.line_number - 1]
            
            # Replace with comment
            fixed_line = f"        // File system operation removed by compliance checker\n        // Original: {original_line.strip()}\n"
            lines[violation.line_number - 1] = fixed_line
            
            # Write back
            with open(violation.file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            print(f"  ✅ Fixed file system violation in {violation.file_path}:{violation.line_number}")
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to fix violation in {violation.file_path}: {e}")
            return False
    
    def _fix_debug_code_violation(self, violation: Violation, dry_run: bool) -> bool:
        """Fix debug code violations."""
        if dry_run:
            print(f"  Would remove debug code in {violation.file_path}:{violation.line_number}")
            return True
        
        # Similar implementation to file system fix
        return False  # Not implemented for safety


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Architectural Compliance Checker for Canvas-Tracker-V3")
    parser.add_argument('--component', choices=['canvas-interface', 'database', 'general'], 
                      help='Check specific component only')
    parser.add_argument('--fix-violations', action='store_true', 
                      help='Attempt to auto-fix violations')
    parser.add_argument('--dry-run', action='store_true', default=True,
                      help='Simulate fixes without making changes (default)')
    parser.add_argument('--apply-fixes', action='store_true',
                      help='Actually apply fixes (overrides --dry-run)')
    
    args = parser.parse_args()
    
    # Initialize checker
    checker = ArchitecturalComplianceChecker(PROJECT_ROOT)
    
    # Run compliance check
    report = checker.run_compliance_check(args.component)
    
    # Print report
    checker.print_report(report)
    
    # Apply fixes if requested
    if args.fix_violations:
        dry_run = not args.apply_fixes  # Apply fixes only if explicitly requested
        fixes_applied = checker.fix_violations(dry_run)
        
        if dry_run and fixes_applied > 0:
            print(f"\n💡 Run with --apply-fixes to actually apply {fixes_applied} automatic fixes")
    
    # Exit with appropriate code
    critical_violations = report['summary']['critical_violations']
    sys.exit(1 if critical_violations > 0 else 0)


if __name__ == '__main__':
    main()