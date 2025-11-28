#!/usr/bin/env bash
# Security Scanning Suite for SmartHR360
# ======================================
# Runs comprehensive security scans including dependency vulnerabilities,
# code security issues, and configuration audits.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  SmartHR360 Security Scanning Suite   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Create reports directory
REPORTS_DIR="security_reports"
mkdir -p "$REPORTS_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo ""
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
print_section "Checking Prerequisites"

if ! command_exists python; then
    echo -e "${RED}✗ Python not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python found${NC}"

if ! command_exists pip; then
    echo -e "${RED}✗ pip not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ pip found${NC}"

# Install/update security tools if needed
print_section "Installing Security Tools"

echo "Installing security scanning dependencies..."
pip install -q --upgrade safety bandit pip-audit semgrep 2>/dev/null || true
echo -e "${GREEN}✓ Security tools installed/updated${NC}"

# 1. Dependency Vulnerability Scanning with Safety
print_section "1. Dependency Vulnerability Scan (Safety)"

echo "Scanning Python dependencies for known vulnerabilities..."
SAFETY_REPORT="$REPORTS_DIR/safety_report_$TIMESTAMP.txt"

if safety check --output text > "$SAFETY_REPORT" 2>&1; then
    echo -e "${GREEN}✓ No vulnerabilities found by Safety${NC}"
    cat "$SAFETY_REPORT"
else
    echo -e "${YELLOW}⚠ Vulnerabilities found - see report${NC}"
    cat "$SAFETY_REPORT"
    echo ""
    echo -e "${YELLOW}Report saved to: $SAFETY_REPORT${NC}"
fi

# 2. Dependency Audit with pip-audit
print_section "2. Dependency Audit (pip-audit)"

echo "Auditing installed packages against OSV database..."
PIP_AUDIT_REPORT="$REPORTS_DIR/pip_audit_report_$TIMESTAMP.txt"

if pip-audit --desc > "$PIP_AUDIT_REPORT" 2>&1; then
    echo -e "${GREEN}✓ No vulnerabilities found by pip-audit${NC}"
else
    echo -e "${YELLOW}⚠ Vulnerabilities found - see report${NC}"
    cat "$PIP_AUDIT_REPORT"
    echo ""
    echo -e "${YELLOW}Report saved to: $PIP_AUDIT_REPORT${NC}"
fi

# 3. Code Security Scanning with Bandit
print_section "3. Code Security Analysis (Bandit)"

echo "Scanning Python code for security issues..."
BANDIT_REPORT="$REPORTS_DIR/bandit_report_$TIMESTAMP.txt"
BANDIT_JSON="$REPORTS_DIR/bandit_report_$TIMESTAMP.json"

bandit -r . \
    -f txt \
    -o "$BANDIT_REPORT" \
    --exclude '.venv,venv,env,htmlcov,*/migrations/*,*/tests/*,node_modules' \
    -ll 2>/dev/null || true

bandit -r . \
    -f json \
    -o "$BANDIT_JSON" \
    --exclude '.venv,venv,env,htmlcov,*/migrations/*,*/tests/*,node_modules' \
    -ll 2>/dev/null || true

if [ -f "$BANDIT_REPORT" ]; then
    # Check if issues were found
    if grep -q "Total issues (by severity)" "$BANDIT_REPORT"; then
        echo -e "${YELLOW}⚠ Security issues found - see report${NC}"
        # Show summary
        grep -A 10 "Total issues" "$BANDIT_REPORT" || true
    else
        echo -e "${GREEN}✓ No security issues found${NC}"
    fi
    echo ""
    echo -e "${BLUE}Full report saved to: $BANDIT_REPORT${NC}"
else
    echo -e "${RED}✗ Bandit scan failed${NC}"
fi

# 4. SAST with Semgrep
print_section "4. Static Analysis (Semgrep)"

if command_exists semgrep; then
    echo "Running Semgrep security rules..."
    SEMGREP_REPORT="$REPORTS_DIR/semgrep_report_$TIMESTAMP.txt"
    SEMGREP_JSON="$REPORTS_DIR/semgrep_report_$TIMESTAMP.json"

    semgrep --config=auto \
        --exclude='*.pyc' \
        --exclude='.venv' \
        --exclude='venv' \
        --exclude='htmlcov' \
        --exclude='node_modules' \
        --exclude='*/migrations/*' \
        --text > "$SEMGREP_REPORT" 2>&1 || true

    semgrep --config=auto \
        --exclude='*.pyc' \
        --exclude='.venv' \
        --exclude='venv' \
        --exclude='htmlcov' \
        --exclude='node_modules' \
        --exclude='*/migrations/*' \
        --json > "$SEMGREP_JSON" 2>&1 || true

    if [ -f "$SEMGREP_REPORT" ]; then
        if grep -q "findings" "$SEMGREP_REPORT"; then
            echo -e "${YELLOW}⚠ Findings detected - see report${NC}"
            head -50 "$SEMGREP_REPORT"
        else
            echo -e "${GREEN}✓ No issues found${NC}"
        fi
        echo ""
        echo -e "${BLUE}Full report saved to: $SEMGREP_REPORT${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Semgrep not installed, skipping SAST${NC}"
fi

# 5. Django Security Check
print_section "5. Django Security Check"

if [ -f "manage.py" ]; then
    echo "Running Django security checks..."
    DJANGO_CHECK_REPORT="$REPORTS_DIR/django_check_$TIMESTAMP.txt"

    if python manage.py check --deploy > "$DJANGO_CHECK_REPORT" 2>&1; then
        echo -e "${GREEN}✓ Django deployment checks passed${NC}"
    else
        echo -e "${YELLOW}⚠ Django deployment issues found${NC}"
        cat "$DJANGO_CHECK_REPORT"
        echo ""
        echo -e "${YELLOW}Report saved to: $DJANGO_CHECK_REPORT${NC}"
    fi
else
    echo -e "${YELLOW}⚠ manage.py not found, skipping Django checks${NC}"
fi

# 6. Git Secrets Scan (if available)
print_section "6. Git Secrets Scan"

if command_exists git; then
    echo "Scanning for secrets in git history..."
    SECRETS_REPORT="$REPORTS_DIR/secrets_scan_$TIMESTAMP.txt"

    # Check for common secret patterns
    git log -p | grep -iE '(password|secret|api[_-]?key|token|credential)' > "$SECRETS_REPORT" 2>/dev/null || true

    if [ -s "$SECRETS_REPORT" ]; then
        echo -e "${YELLOW}⚠ Potential secrets found in git history${NC}"
        echo -e "${YELLOW}Report saved to: $SECRETS_REPORT${NC}"
        echo -e "${YELLOW}Review manually to confirm if these are actual secrets${NC}"
    else
        echo -e "${GREEN}✓ No obvious secrets detected${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Git not available, skipping secrets scan${NC}"
fi

# Generate Summary Report
print_section "Generating Summary Report"

SUMMARY_REPORT="$REPORTS_DIR/security_summary_$TIMESTAMP.txt"

cat > "$SUMMARY_REPORT" << EOF
SmartHR360 Security Scan Summary
================================
Date: $(date)
Scan ID: $TIMESTAMP

Reports Generated:
- Safety Report: $SAFETY_REPORT
- pip-audit Report: $PIP_AUDIT_REPORT
- Bandit Report: $BANDIT_REPORT (JSON: $BANDIT_JSON)
- Semgrep Report: $SEMGREP_REPORT (JSON: $SEMGREP_JSON)
- Django Check: $DJANGO_CHECK_REPORT
- Secrets Scan: $SECRETS_REPORT

Scan Results Summary:
EOF

# Count issues from each tool
if [ -f "$BANDIT_REPORT" ]; then
    BANDIT_ISSUES=$(grep -c "Issue:" "$BANDIT_REPORT" 2>/dev/null || echo "0")
    echo "- Bandit: $BANDIT_ISSUES security issues" >> "$SUMMARY_REPORT"
fi

if [ -f "$SAFETY_REPORT" ]; then
    SAFETY_VULNS=$(grep -c "vulnerability found" "$SAFETY_REPORT" 2>/dev/null || echo "0")
    echo "- Safety: $SAFETY_VULNS vulnerabilities" >> "$SUMMARY_REPORT"
fi

if [ -f "$PIP_AUDIT_REPORT" ]; then
    PIP_AUDIT_VULNS=$(grep -c "found" "$PIP_AUDIT_REPORT" 2>/dev/null || echo "0")
    echo "- pip-audit: $PIP_AUDIT_VULNS vulnerabilities" >> "$SUMMARY_REPORT"
fi

echo "" >> "$SUMMARY_REPORT"
echo "Recommendations:" >> "$SUMMARY_REPORT"
echo "1. Review all reports in detail" >> "$SUMMARY_REPORT"
echo "2. Prioritize fixing HIGH and CRITICAL severity issues" >> "$SUMMARY_REPORT"
echo "3. Update vulnerable dependencies" >> "$SUMMARY_REPORT"
echo "4. Address code security issues found by Bandit" >> "$SUMMARY_REPORT"
echo "5. Review Django deployment checklist warnings" >> "$SUMMARY_REPORT"
echo "6. Run scans regularly (weekly recommended)" >> "$SUMMARY_REPORT"

cat "$SUMMARY_REPORT"
echo ""
echo -e "${GREEN}Summary report saved to: $SUMMARY_REPORT${NC}"

# Final message
print_section "Scan Complete"

echo -e "${GREEN}✓ Security scan completed successfully${NC}"
echo ""
echo "All reports saved to: $REPORTS_DIR/"
echo ""
echo "Next Steps:"
echo "1. Review the summary report: $SUMMARY_REPORT"
echo "2. Check individual reports for details"
echo "3. Address HIGH and CRITICAL severity issues immediately"
echo "4. Plan remediation for MEDIUM severity issues"
echo "5. Run this scan regularly as part of CI/CD"
echo ""
echo -e "${BLUE}For detailed remediation guidance, see: docs/SECURITY_GUIDE.md${NC}"
