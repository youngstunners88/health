---
name: humanizer
description: >
  Makes AI-generated text sound more natural, conversational, and human-like.
  Use when Kofi needs to: (1) Convert robotic or technical output into friendly language,
  (2) Improve tone of reports, summaries, or agent notes,
  (3) Add empathy and clarity to patient-facing messages.
---

# Humanizer Skill

## Overview

This skill takes structured or technical text and rewrites it in a warm, human‑readable tone. It is useful for turning agent logs, JSON summaries, or clinical notes into language that patients, caregivers, or non‑technical stakeholders can easily understand.

## Core Capabilities

### 1. Tone Adjustment
- Convert formal/jargony language into conversational style.
- Add empathy markers (e.g., “I understand this might be concerning…”).

### 2. Clarity Enhancement
- Replace acronyms with plain‑language explanations on first use.
- Break long sentences into shorter, easier‑to‑read chunks.

### 3. Formatting for Readability
- Use bullet points for lists.
- Add headings and spacing to improve scannability.

## Workflow: From Raw Output to Human‑Friendly Text

### Step 1: Receive Input
Accept any of the following:
- Plain text
- JSON object (will be stringified)
- Markdown

### Step 2: Apply Humanizing Rules
1. Identify technical terms and add lay‑explanations in parentheses.
2. Replace passive voice with active voice where appropriate.
3. Insert transitional phrases (“As a result,” “For example,”).
4. Ensure sentences end with a period and vary length.

### Step 3: Output
Return the revised text as plain Markdown (or plain text if requested).

## Example

**Input:**
```json
{
  "patient_id": "demo-001",
  "risk_score": 0.72,
  "handoff_log": [
    {"agent": "intake", "output": {"patient_id": "demo-001", "name": "John Doe"}},
    {"agent": "risk", "risk_score": 0.72}
  ]
}
```

**Humanized Output:**
> The assessment for patient **demo-001** (John Doe) shows a readmission risk of **72 %**, which is considered high.  
> - The intake agent successfully retrieved the patient’s basic information.  
> - The risk agent flagged an elevated risk due to the presence of congestive heart failure in the diagnosis list.  
>   
> Next steps include verifying insurance coverage and scheduling follow‑up appointments.

## Resources

### scripts/
- `humanize.py` – a simple Python function that applies the rules above (see below).

### references/
- `style_guide.md` – quick reference for tone, empathy phrases, and formatting tips.

### assets/
- None required.

---

**scripts/humanize.py**
```python
import re
from typing import Any, Dict

def humanize_text(text: str) -> str:
    """Apply basic humanizing heuristics."""
    # Add space after commas if missing
    text = re.sub(r",(\S)", r", \1", text)
    # Ensure sentences end with a period
    text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)
    # Replace common acronyms with expansions on first use (simplified)
    expansions = {
        "EHR": "electronic health record (EHR)",
        "MCP": "model context protocol (MCP)",
        "A2A": "agent-to-agent (A2A)",
        "PCP": "primary care physician (PCP)",
        "CHF": "congestive heart failure (CHF)",
        "T2DM": "type 2 diabetes mellitus (T2DM)"
    }
    for acr, full in expansions.items():
        # Replace only the first occurrence
        if acr in text:
            text = re.sub(rf"\b{acr}\b", full, text, count=1)
    return text

def humanize_json(data: Dict[str, Any]) -> str:
    """Convert a dict to a readable, humanized summary."""
    # Very simple formatter – can be expanded
    lines = []
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"**{k.replace('_', ' ').title()}:**")
            for subk, subv in v.items():
                lines.append(f"  - {subk.replace('_', ' ').title()}: {subv}")
        elif isinstance(v, list):
            lines.append(f"**{k.replace('_', ' ').title()}:** {len(v)} item(s)")
        else:
            lines.append(f"**{k.replace('_', ' ').title()}:** {v}")
    return "\n".join(lines)
```

**references/style_guide.md**
```
# Humanizer Style Guide

- Use active voice: “The agent retrieved the record” not “The record was retrieved by the agent.”
- Add empathy: “I understand this may be stressful; here’s what we found.”
- Prefer short sentences (15‑20 words max).
- Use bullet points for lists of three or more items.
- Explain acronyms on first use.
- End with a clear next step or summary.
```