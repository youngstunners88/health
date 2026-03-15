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