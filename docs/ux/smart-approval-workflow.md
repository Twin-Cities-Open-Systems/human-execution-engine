# Smart Approval Workflow: Recommended Usage

```yaml
explanation:
  topic: new_chat_last_hour_effect
  what_it_is:
    - fresh_context_window
    - zero_accumulated_drift
    - clean_scope_and_ownership
  why_last_hour_matters:
    - recent_chat_accumulates_loop_pressure
    - completion_markers_blur
    - intent_and_execution_entangle
  what_new_chat_resets:
    - removes_hidden_state_carryover
    - restores_boundary_between_plan_and_act
    - reasserts explicit_start_conditions
  hee_reasoning:
    - correctness_degrades_with_unbounded_context
    - termination_requires_hard_reset
    - new_chat_is_cheapest_safe_reset
  conclusion: new_chat_is_a_structural_control_not_a_memory_upgrade
```

## Overview

The smart approval workflow automatically determines whether commands require
explicit user approval based on safety profiles, reducing friction for safe
operations while maintaining security for risky ones.

## How It Works

### Safety Profiles

- **read_only**: Commands that don't change system state (ls, git status, cat, etc.)
- **low_risk**: Commands that make bounded local changes (git add, mkdir, etc.)
- **unknown/dangerous**: Commands that require explicit approval

### Decision Logic

1. Parse command into tokens
2. Check against denylist patterns (dangerous operations)
3. Match against read_only allowlists (auto-approve)
4. Match against low_risk allowlists with git status check (auto-approve if clean)
5. Default to explicit approval for unknowns

## Recommended Usage Patterns

### Development Workflow

```bash
# Auto-approved (read-only)
git status
git diff
git log
ls -la
cat README.md

# Auto-approved (low-risk, clean repo)
git add .
git restore --staged file.txt
mkdir new-dir

# Requires approval
git push origin main
rm -rf important-data/
sudo apt update
```

### Interactive Development

- **Safe commands**: Execute immediately with visual feedback
- **Risky commands**: Show clear warning with approval prompt
- **Unknown commands**: Conservative approach with detailed reasoning

### CI/CD Integration

- **Pre-commit hooks**: Validate commands before execution
- **Audit logging**: Record all command evaluations
- **Policy enforcement**: Block denied patterns automatically

## Guardrails

### Default Deny on Ambiguity

- Unknown commands always require explicit approval
- Conservative bias toward safety over convenience

### Explicit User Override

- Users can force approval for normally auto-approved commands
- Emergency override mechanisms for urgent situations

### Full Transcript Capture

- All command evaluations logged with reasoning
- Confidence scores and decision paths recorded
- Audit trail for security and debugging

### No Execution Without Disk Trace

- Every command evaluation leaves verifiable artifacts
- Command history and decisions persisted to disk
- No ephemeral-only operations

## Implementation Status

### ✅ Completed

- Safety profile definitions
- Command tokenization and parsing
- Decision logic implementation
- Prototype validation with replay testing

### 🔄 In Progress

- Integration with Cline interface
- User experience optimization
- Performance benchmarking

### 📋 Planned

- CI/CD pipeline integration
- Advanced pattern recognition
- User customization options

## Success Metrics

### UX Improvements

- **Approval prompts reduced by >80%** for development workflows
- **Command execution time improved** by eliminating unnecessary waits
- **User satisfaction increased** through reduced friction

### Safety Maintenance

- **False negatives minimized** (dangerous commands blocked)
- **False positives reduced** (safe commands auto-approved)
- **Audit compliance maintained** through comprehensive logging

### Reliability Goals

- **Command evaluation accuracy >95%**
- **Response time <100ms** for typical commands
- **Error rate <1%** for known command patterns

## Eye Candy: Extensible Metrics Visualization

### Overview

The Eye Candy system provides extensible metrics visualization for smart approval systems,
enabling stakeholders to monitor system health, decision patterns, and performance trends
through beautiful, interactive dashboards.

### Architecture

#### Core Components

- **Contracts**: JSON Schema definitions for metrics and events data
- **Ingestion**: Reads transcripts and metrics from disk storage
- **Transform**: Computes timeseries and aggregations from raw data
- **Rendering API**: Pluggable renderer interface supporting multiple output formats
- **CLI Tool**: Unified command-line interface for building dashboard bundles

#### Extension Points

- **New Metrics**: Add fields to schema, update transform logic
- **New Renderers**: Implement renderer interface (Plotly, JSON, Markdown, etc.)
- **New Data Sources**: Implement custom ingestion adapters
- **Dashboard Views**: Add view configurations without core changes

### Supported Views

#### Overview Dashboard (`overview.html`)

- **KPI Strip**: Prompt rate, override rate, deny rate, safety incidents, phase day
- **Timeseries Charts**: Interactive rate trends with Plotly.js
- **Real-time Updates**: Automatic refresh from latest metrics data

#### Decisions Analysis (`decisions.html`)

- **Decision Table**: Recent decisions with confidence scores and reasons
- **Deny Reasons Chart**: Pie chart breakdown of denial categories
- **Filtering**: Profile, decision type, and reason-based filtering

#### Replay Health (`replay_health.html`)

- **Test Status**: Pass rate and corpus health metrics
- **Failure Analysis**: Recent test failures with severity levels
- **Health Assessment**: Automated status indicators (Healthy/Warning/Critical)

### Output Formats

#### Static HTML (Plotly Static)

- **Interactive Charts**: Zoom, pan, hover tooltips with Plotly.js
- **Offline Viewing**: No network required, self-contained HTML
- **Responsive Design**: Works on desktop and mobile devices

#### JSON API Bundle

- **Structured Data**: Machine-readable metrics and KPIs
- **API Integration**: Easy consumption by other tools and dashboards
- **Versioned Schema**: Stable contracts for external integrations

#### Markdown Reports

- **Documentation**: Human-readable reports suitable for sharing
- **Version Control**: Git-friendly text format
- **Print-Friendly**: Clean formatting for reports and presentations

### Usage Guide

#### Building Dashboards

```bash
# Build default dashboard (Plotly static HTML)
python tooling/smart-approval/cli.py /path/to/data /path/to/output

# Build specific views only
python tooling/smart-approval/cli.py /path/to/data /path/to/output --views overview decisions

# Use different renderer
python tooling/smart-approval/cli.py /path/to/data /path/to/output --renderer json_bundle

# List available renderers
python tooling/smart-approval/cli.py --list-renderers
```

#### CI/CD Integration

- **Automatic Builds**: GitHub Actions workflow triggers on data changes
- **Artifact Storage**: Dashboard bundles uploaded as build artifacts
- **GitHub Pages**: Automatic deployment for public dashboard access

#### Local Development

```bash
# Quick build for testing
mkdir -p /tmp/dashboard
python tooling/smart-approval/cli.py docs/history/state_capsules /tmp/dashboard

# Open in browser
open /tmp/dashboard/index.html
```

### Data Sources

#### Transcript Files

- **Format**: YAML files containing decision logs and safety events
- **Location**: `docs/history/state_capsules/` directory
- **Content**: Phase information, decision outcomes, confidence scores

#### Metrics Files

- **Format**: JSON files with aggregated metrics data
- **Auto-generation**: Computed from transcript analysis
- **Real-time**: Updated as new transcripts are created

### Customization

#### Adding New Metrics

1. Update `tooling/smart-approval/contracts/metrics.schema.json` with new fields
2. Modify `lib/transform.py` to compute new aggregations
3. Update renderers to display new metrics in views

#### Creating New Renderers

1. Implement `MetricsRenderer` abstract base class
2. Register renderer with `renderer_registry`
3. Support required views: overview, decisions, replay_health

#### Custom Views

- **Configuration-driven**: Add view specs without code changes
- **Template-based**: HTML templates for consistent styling
- **Plugin Architecture**: Drop-in view implementations

### Quality Assurance

#### Validation Checks

- **Schema Compliance**: All data validated against JSON schemas
- **Deterministic Transforms**: Consistent results across builds
- **Reproducible Outputs**: Same input data produces identical dashboards

#### Acceptance Criteria

- **Offline Viewing**: No network dependencies for dashboard access
- **Build ID Embedding**: Git commit hash included in all outputs
- **Cross-platform**: Works on Linux, macOS, Windows browsers

### Troubleshooting

#### Common Issues

- **Missing Data**: Check transcript files exist and are readable
- **Renderer Errors**: Verify renderer name is registered
- **Build Failures**: Check Python dependencies (PyYAML required)

#### Debug Mode

```bash
# Verbose output
PYTHONPATH=tooling/smart-approval/lib python -c "
import sys
sys.path.insert(0, 'tooling/smart-approval/lib')
from lib.ingest import DataIngestor
ingestor = DataIngestor('docs/history/state_capsules')
print('Data check:', len(ingestor.ingest_all_data()['transcripts']), 'transcripts found')
"
```

---

*Document Version: 1.0 | Last Updated: 2026-01-28*
