# Meta Skills - Autonomous Capability Framework

## Overview
Master skill system that enables autonomous use of external tools and frameworks without requiring explicit permission. Routes tasks to the right skill based on context, manages state across sessions, and provides unified abstraction interfaces.

## Architecture

```
skills/meta-skills/
├── orchestrator/           # Master routing and state management
│   ├── scripts/
│   │   ├── router.py       # Intelligent task routing
│   │   ├── state_manager.py # Cross-session state management
│   │   └── executor.py     # Autonomous execution engine
│   └── config/
│       └── routes.yaml     # Routing rules
├── design-md/              # UI design system integration
│   ├── scripts/
│   │   └── designer.py     # DESIGN.md application and UI generation
│   ├── references/         # DESIGN.md files from awesome-design-md
│   ├── assets/             # Preview HTML templates
│   └── templates/          # UI component templates
├── browser-use/            # Autonomous browser automation
│   ├── scripts/
│   │   └── browser_agent.py # Browser-use integration
│   ├── references/
│   └── config/
│       └── browser.yaml    # Browser configuration
├── autoagent/              # Self-improving agent engineering
│   ├── scripts/
│   │   └── harness.py      # Agent harness iteration
│   ├── references/
│   ├── config/
│   └── templates/          # Agent templates
└── superpowers/            # Dev workflow orchestration
    ├── scripts/
    │   └── workflow.py     # Brainstorm → Plan → Execute → Review
    ├── references/
    ├── config/
    └── workflows/          # Workflow definitions
```

## Autonomous Usage Rules
- Use browser-use for any web research, form filling, or data extraction task
- Use design-md when building UIs, landing pages, or frontend components
- Use autoagent when iterating on agent configurations or optimizing performance
- Use superpowers for any software development task (brainstorm → plan → execute)
- No permission required for read-only or internal operations
- Ask before external actions (emails, public posts, payments)

## Routing Keywords
- "design", "UI", "frontend", "landing page" → design-md
- "browse", "scrape", "fill form", "web task", "research" → browser-use
- "agent", "harness", "optimize agent", "benchmark" → autoagent
- "build", "code", "implement", "feature", "bug", "plan" → superpowers
- "healthcare", "discharge", "patient" → healthcare workspace
