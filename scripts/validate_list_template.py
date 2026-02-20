#!/usr/bin/env python
"""
List View Template Validator
=============================

Validates list view templates to ensure they follow the standard pattern
and include all required elements for proper functionality.

Usage:
    python scripts/validate_list_template.py <template_path>
    
Example:
    python scripts/validate_list_template.py modules/basic_data/templates/contact/list.html
"""

import sys
import re
from pathlib import Path


class Colors:
    """Terminal colors for formatted output"""
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def read_template(template_path):
    """Read template file content"""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"{Colors.RED}✗ Error: File not found: {template_path}{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}✗ Error reading file: {e}{Colors.END}")
        sys.exit(1)


def validate_list_template(content, template_path):
    """
    Validate list view template content
    Returns: (errors, warnings)
    """
    errors = []
    warnings = []
    
    # Check 1: Must extend list_view.html
    if "extends 'components/list_view.html'" not in content and 'extends "components/list_view.html"' not in content:
        errors.append("Template must extend 'components/list_view.html'")
    
    # Check 2: Required blocks
    required_blocks = {
        'page_title': 'Browser tab title',
        'header_title': 'Page header',
        'header_description': 'Page description',
        'content': 'list-metadata script (CRITICAL for select-all)',
        'table_headers': 'Table column headers',
        'table_rows': 'Table data rows',
        'overlays': 'Email/Line sidebars'
    }
    
    for block, description in required_blocks.items():
        pattern = r'{%\s*block\s+' + block + r'\s*%}'
        if not re.search(pattern, content):
            if block == 'content':
                errors.append(f"CRITICAL: Missing block '{block}' - {description}")
            elif block == 'overlays':
                errors.append(f"CRITICAL: Missing block '{block}' - {description}")
            else:
                warnings.append(f"Missing recommended block: {block} - {description}")
    
    # Check 3: list-metadata script
    if 'list-metadata' in content:
        # Check for escapejs usage
        if 'escapejs' not in content:
            warnings.append("list-metadata script should use |escapejs filter to prevent JSON parse errors")
        
        # Check for block.super
        content_block_match = re.search(r'{%\s*block\s+content\s*%}(.*?){%\s*endblock\s*%}', content, re.DOTALL)
        if content_block_match:
            content_block_content = content_block_match.group(1)
            if 'block.super' not in content_block_content:
                errors.append("Block 'content' must include {{ block.super }} after list-metadata script")
    else:
        if re.search(r'{%\s*block\s+content\s*%}', content):
            errors.append("CRITICAL: list-metadata script is missing - select-all functionality will NOT work")
    
    # Check 4: Checkbox binding
    checkbox_pattern = r'x-model\s*=\s*["\']selectedRows["\']'
    checkbox_number_pattern = r'x-model\.number\s*=\s*["\']selectedRows["\']'
    
    if re.search(checkbox_pattern, content):
        if not re.search(checkbox_number_pattern, content):
            errors.append("CRITICAL: Checkbox uses x-model=\"selectedRows\" but should use x-model.number=\"selectedRows\"")
    
    # Check 5: Overlays content
    if re.search(r'{%\s*block\s+overlays\s*%}', content):
        overlays_match = re.search(r'{%\s*block\s+overlays\s*%}(.*?){%\s*endblock\s*%}', content, re.DOTALL)
        if overlays_match:
            overlays_content = overlays_match.group(1)
            if 'export_modal.html' not in overlays_content:
                warnings.append("export_modal.html not included in overlays block")
            if 'email_sidebar.html' not in overlays_content:
                warnings.append("email_sidebar.html not included in overlays - Email action won't work")
            if 'line_sidebar.html' not in overlays_content:
                warnings.append("line_sidebar.html not included in overlays - Line action won't work")
    
    # Check 6: Common mistake - sidebars in wrong block
    if 'email_sidebar.html' in content or 'line_sidebar.html' in content:
        if not re.search(r'{%\s*block\s+overlays\s*%}', content):
            errors.append("Sidebars included but not in 'overlays' block - page may be blank")
    
    return errors, warnings


def validate_view_file(template_path):
    """
    Try to find and validate the corresponding view file
    Returns: (errors, warnings)
    """
    errors = []
    warnings = []
    
    # Try to locate views.py based on template path
    template_path = Path(template_path)
    
    # Assume structure: modules/<app>/templates/<model>/list.html
    # Corresponding view: modules/<app>/views/<model>.py OR modules/<app>/views.py
    
    parts = template_path.parts
    if 'templates' in parts:
        template_idx = parts.index('templates')
        if template_idx >= 2:
            app_path = Path(*parts[:template_idx])
            
            # Try views/<model>.py first
            if len(parts) > template_idx + 1:
                model_name = parts[template_idx + 1]
                view_file_1 = app_path / 'views' / f'{model_name}.py'
                view_file_2 = app_path / 'views.py'
                
                view_file = None
                if view_file_1.exists():
                    view_file = view_file_1
                elif view_file_2.exists():
                    view_file = view_file_2
                
                if view_file:
                    try:
                        with open(view_file, 'r', encoding='utf-8') as f:
                            view_content = f.read()
                        
                        # Check for ListActionMixin
                        if 'ListActionMixin' not in view_content:
                            errors.append(f"View file ({view_file.name}) doesn't import/use ListActionMixin - bulk actions won't work")
                        
                        # Check for ListView
                        if 'ListView' not in view_content:
                            warnings.append(f"View file ({view_file.name}) doesn't seem to use ListView")
                        
                    except Exception:
                        pass  # Silently skip if can't read view file
    
    return errors, warnings


def print_results(template_path, errors, warnings, view_errors, view_warnings):
    """Print validation results with colors"""
    print(f"\n{Colors.BOLD}Validating List View Template{Colors.END}")
    print(f"File: {Colors.BLUE}{template_path}{Colors.END}\n")
    
    total_issues = len(errors) + len(warnings) + len(view_errors) + len(view_warnings)
    
    if errors:
        print(f"{Colors.RED}{Colors.BOLD}✗ ERRORS ({len(errors)}):{Colors.END}")
        for error in errors:
            print(f"  {Colors.RED}• {error}{Colors.END}")
        print()
    
    if view_errors:
        print(f"{Colors.RED}{Colors.BOLD}✗ VIEW ERRORS ({len(view_errors)}):{Colors.END}")
        for error in view_errors:
            print(f"  {Colors.RED}• {error}{Colors.END}")
        print()
    
    if warnings:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ WARNINGS ({len(warnings)}):{Colors.END}")
        for warning in warnings:
            print(f"  {Colors.YELLOW}• {warning}{Colors.END}")
        print()
    
    if view_warnings:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ VIEW WARNINGS ({len(view_warnings)}):{Colors.END}")
        for warning in view_warnings:
            print(f"  {Colors.YELLOW}• {warning}{Colors.END}")
        print()
    
    if total_issues == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ All checks passed! Template looks good.{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.BOLD}Total Issues: {len(errors) + len(view_errors)} errors, {len(warnings) + len(view_warnings)} warnings{Colors.END}")
        print(f"\nRefer to {Colors.BLUE}.agent/skills/standard_list_view/SKILL.md{Colors.END} for guidance.\n")
        return 1 if errors or view_errors else 0


def main():
    if len(sys.argv) < 2:
        print(f"{Colors.BOLD}Usage:{Colors.END} python scripts/validate_list_template.py <template_path>")
        print(f"{Colors.BOLD}Example:{Colors.END} python scripts/validate_list_template.py modules/basic_data/templates/contact/list.html")
        sys.exit(1)
    
    template_path = sys.argv[1]
    
    # Read and validate template
    content = read_template(template_path)
    errors, warnings = validate_list_template(content, template_path)
    
    # Try to validate corresponding view file
    view_errors, view_warnings = validate_view_file(template_path)
    
    # Print results
    exit_code = print_results(template_path, errors, warnings, view_errors, view_warnings)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
