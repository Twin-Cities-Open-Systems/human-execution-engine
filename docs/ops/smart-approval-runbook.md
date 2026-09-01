# Smart Approval Workflow Operations Runbook

## Overview

The smart approval workflow automatically determines command approval requirements to reduce
friction while maintaining safety. This runbook covers operations, overrides, and rollback procedures.

## Current Phase: Read-Only Auto-Approval

- **Status**: Active (7-day observation period)
- **Auto-approved**: Read-only commands (ls, cat, git status, etc.)
- **Manual approval**: All other commands
- **Override controls**: Available for emergency situations

## Monitoring Dashboard

Daily metrics are collected in `var/smart-approval/metrics.json`:

- `prompt_rate`: Percentage of commands requiring manual approval
- `override_rate`: Percentage of decisions using overrides
- `approval_rate`: Percentage of commands auto-approved

## Alert Thresholds

- **Warning**: prompt_rate > 80% (too many approvals required)
- **Info**: override_rate > 10% (override usage tracking)

## Emergency Procedures

### Immediate Override (Single Command)

```bash
# Force approve a specific command pattern
override_controller.force_approve("exact:git push origin main")

# Force prompt for a command pattern
override_controller.force_prompt("contains:sudo")
```

### System-Wide Disable

1. Edit `tooling/smart-approval/rollout_config.yml <!-- hee-check:refs-ok  removed since; the runbook records the rollout as it ran -->`
2. Set `read_only_auto_approve: false`
3. Restart Cline integration

### Full Rollback

1. Remove Cline adapter integration
2. Delete `var/smart-approval/` directory
3. All commands require explicit approval

## Common Issues

### High Prompt Rate

- Check if low-risk commands are being blocked
- Review safety profiles for overly restrictive rules
- Consider enabling low-risk auto-approval after observation

### False Positives

- Commands incorrectly requiring approval
- Use override controls for temporary fixes
- Update safety profiles for permanent fixes

### Performance Issues

- High latency in command evaluation
- Check transcript file size
- Consider log rotation for long-running deployments

## Maintenance Procedures

### Weekly Review

1. Review metrics report
2. Check for new command patterns needing classification
3. Update safety profiles if needed
4. Clear old transcripts (>30 days)

### Monthly Audit

1. Full replay corpus validation
2. Configuration schema validation
3. Override usage analysis
4. Rollout progression assessment

## Contact

For issues or questions about smart approval workflow:

- Check metrics in `var/smart-approval/metrics.json`
- Review runbook at `docs/ops/smart-approval-runbook.md`
- Emergency rollback: Set `read_only_auto_approve: false`
