# HEE Compliance Monitoring Scripts

This directory contains scripts for monitoring and enforcing HEE (Human Execution Engine) governance compliance.

## Scripts

### `hee_compliance_monitor.py`

**Purpose**: Continuous monitoring of HEE governance compliance
**Usage**:

```bash
# Run compliance checks
python scripts/hee_compliance_monitor.py

# Generate compliance report
python scripts/hee_compliance_monitor.py --report
```

**Features**:

- **Main Branch Protection**: Detects direct commits to main branch
- **Model Disclosure**: Ensures commit messages include AI model disclosure
- **Branch Naming**: Validates feature branch naming conventions
- **Violation Tracking**: Logs all violations with timestamps
- **Compliance Scoring**: Provides compliance score out of 100
- **Reporting**: Generates detailed compliance reports

**Integration**:

- Can be run manually or integrated into CI/CD pipelines
- Creates violation logs in `docs/history/state_capsules/compliance_violations.json` <!-- hee-check:refs-ok  written at runtime, not committed -->
- Provides actionable feedback for violation resolution

## Pre-commit Hooks

### `.git/hooks/pre-commit`

**Purpose**: Prevents HEE governance violations at commit time
**Features**:

- Blocks direct commits to main branch
- Validates commit message format includes model disclosure
- Provides helpful error messages and solutions

**Installation**:

- Automatically installed when cloning the repository
- Made executable during setup process

## Usage Examples

### Manual Compliance Check

```bash
cd human-execution-engine
python scripts/hee_compliance_monitor.py
```

### Generate Compliance Report

```bash
cd human-execution-engine
python scripts/hee_compliance_monitor.py --report
```

### CI/CD Integration

```yaml
# .github/workflows/hee-compliance.yml
- name: Run HEE Compliance Check
  run: python scripts/hee_compliance_monitor.py
```

## Violation Types

### HIGH Severity

- **MAIN_BRANCH_COMMIT**: Direct commit to main branch

### MEDIUM Severity

- **MISSING_MODEL_DISCLOSURE**: Commit message missing [model: ...] disclosure
- **INVALID_BRANCH_NAME**: Branch name doesn't follow feature/ or fix/ convention

## Compliance Score Calculation

- **Base Score**: 100%
- **Penalty**: -10 points per violation
- **Minimum Score**: 0%
- **Target**: Maintain 100% compliance

## Best Practices

1. **Regular Monitoring**: Run compliance checks before major commits
2. **Report Review**: Review compliance reports weekly
3. **Violation Resolution**: Address violations immediately
4. **Team Training**: Ensure all team members understand HEE standards

## Troubleshooting

### Pre-commit Hook Not Working

- Ensure the hook file is executable: `chmod +x .git/hooks/pre-commit`
- Check git configuration: `git config core.hooksPath`

### Compliance Monitor Errors

- Ensure Python 3.6+ is installed
- Check that git is properly configured
- Verify script has read/write permissions to repository

## Integration with State Capsules

The compliance monitoring system integrates with HEE state capsules by:

- Logging violations to state capsule directories
- Providing violation details for post-mortem analysis
- Tracking compliance trends over time
- Supporting continuous improvement processes

## Future Enhancements

- **Automated Alerts**: Email/Slack notifications for violations
- **Dashboard**: Web-based compliance dashboard
- **Historical Analysis**: Trend analysis and improvement tracking
- **Integration**: Deeper integration with GitHub Actions and CI/CD
