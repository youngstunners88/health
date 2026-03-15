"""
Design system integration using DESIGN.md files.
Loads design systems from awesome-design-md collection and applies them to UI generation.
"""

import json
from pathlib import Path
from datetime import datetime, timezone


DESIGN_DIR = Path(__file__).parent.parent / "references"
DESIGN_DIR.mkdir(exist_ok=True)


DESIGN_SYSTEMS = {
    "linear": {
        "name": "Linear",
        "description": "Ultra-minimal, precise, purple accent",
        "colors": {
            "primary": "#5E6AD2",
            "primary-hover": "#6B77E0",
            "background": "#0D0D12",
            "surface": "#16161D",
            "surface-hover": "#1C1C24",
            "border": "#2A2A35",
            "text-primary": "#F7F7F8",
            "text-secondary": "#8A8F98",
            "text-tertiary": "#5B5B66",
            "success": "#38A169",
            "warning": "#D69E2E",
            "error": "#E53E3E",
        },
        "typography": {
            "font-family": "'Inter', -apple-system, sans-serif",
            "font-size-base": "14px",
            "font-weight-normal": "400",
            "font-weight-medium": "500",
            "font-weight-bold": "600",
            "letter-spacing": "-0.01em",
        },
        "components": {
            "button": {
                "border-radius": "6px",
                "padding": "8px 16px",
                "font-size": "14px",
                "font-weight": "500",
            },
            "card": {
                "border-radius": "8px",
                "border": "1px solid #2A2A35",
                "background": "#16161D",
                "padding": "16px",
            },
            "input": {
                "border-radius": "6px",
                "border": "1px solid #2A2A35",
                "background": "#0D0D12",
                "padding": "8px 12px",
                "font-size": "14px",
            },
        },
        "layout": {
            "spacing-scale": [4, 8, 12, 16, 24, 32, 48, 64],
            "max-width": "1200px",
            "grid-columns": "12",
            "grid-gap": "24px",
        },
    },
    "vercel": {
        "name": "Vercel",
        "description": "Black and white precision, Geist font",
        "colors": {
            "primary": "#FFFFFF",
            "background": "#000000",
            "surface": "#111111",
            "surface-hover": "#1A1A1A",
            "border": "#333333",
            "text-primary": "#EDEDED",
            "text-secondary": "#888888",
            "text-tertiary": "#444444",
            "accent": "#0070F3",
            "success": "#17C964",
            "warning": "#F5A623",
            "error": "#FF0000",
        },
        "typography": {
            "font-family": "'Geist', -apple-system, sans-serif",
            "font-size-base": "16px",
            "font-weight-normal": "400",
            "font-weight-medium": "500",
            "font-weight-bold": "700",
        },
        "components": {
            "button": {
                "border-radius": "5px",
                "padding": "8px 16px",
                "font-size": "14px",
            },
            "card": {
                "border-radius": "5px",
                "border": "1px solid #333",
                "background": "#111",
            },
        },
    },
    "stripe": {
        "name": "Stripe",
        "description": "Signature purple gradients, weight-300 elegance",
        "colors": {
            "primary": "#635BFF",
            "primary-hover": "#7A73FF",
            "background": "#FFFFFF",
            "surface": "#F6F9FC",
            "border": "#E3E8EE",
            "text-primary": "#0A2540",
            "text-secondary": "#425466",
            "text-tertiary": "#8898AA",
            "success": "#3ECF8E",
            "warning": "#F4A261",
            "error": "#FF4D4F",
        },
        "typography": {
            "font-family": "'Sohne', -apple-system, sans-serif",
            "font-size-base": "16px",
            "font-weight-normal": "300",
            "font-weight-medium": "400",
            "font-weight-bold": "600",
        },
        "components": {
            "button": {
                "border-radius": "20px",
                "padding": "10px 20px",
                "font-size": "15px",
                "font-weight": "400",
            },
        },
    },
    "notion": {
        "name": "Notion",
        "description": "Warm minimalism, serif headings, soft surfaces",
        "colors": {
            "primary": "#2EAADC",
            "background": "#FFFFFF",
            "surface": "#F7F7F5",
            "border": "#E9E9E7",
            "text-primary": "#37352F",
            "text-secondary": "#787774",
            "text-tertiary": "#B4B4B0",
            "success": "#448361",
            "warning": "#CB9000",
            "error": "#E03E3E",
        },
        "typography": {
            "font-family": "'ui-sans-serif', -apple-system, sans-serif",
            "heading-font": "'Lyon-Text', Georgia, serif",
            "font-size-base": "16px",
            "font-weight-normal": "400",
            "font-weight-medium": "500",
            "font-weight-bold": "600",
        },
    },
    "supabase": {
        "name": "Supabase",
        "description": "Dark emerald theme, code-first",
        "colors": {
            "primary": "#3ECF8E",
            "primary-hover": "#56D9A2",
            "background": "#171717",
            "surface": "#1F1F1F",
            "surface-hover": "#2A2A2A",
            "border": "#2E2E2E",
            "text-primary": "#EDEDED",
            "text-secondary": "#A0A0A0",
            "text-tertiary": "#606060",
            "success": "#3ECF8E",
            "warning": "#F4A261",
            "error": "#FF4D4F",
        },
        "typography": {
            "font-family": "'Varela Round', -apple-system, sans-serif",
            "font-size-base": "14px",
        },
    },
}


class DesignSystem:
    """Manages design systems and applies them to UI generation."""

    def __init__(self):
        self._load_custom_designs()

    def _load_custom_designs(self):
        """Load any custom DESIGN.md files from the references directory."""
        for design_file in DESIGN_DIR.glob("*.md"):
            name = design_file.stem.lower()
            if name not in DESIGN_SYSTEMS:
                DESIGN_SYSTEMS[name] = {
                    "name": design_file.stem,
                    "description": f"Custom design from {design_file.name}",
                    "source_file": str(design_file),
                }

    def list_designs(self) -> list[dict]:
        """List all available design systems."""
        return [
            {
                "key": key,
                "name": info.get("name", key),
                "description": info.get("description", ""),
            }
            for key, info in DESIGN_SYSTEMS.items()
        ]

    def get_design(self, name: str) -> dict | None:
        """Get a specific design system by name."""
        return DESIGN_SYSTEMS.get(name.lower())

    def generate_css_variables(self, design_name: str) -> str:
        """Generate CSS custom properties from a design system."""
        design = self.get_design(design_name)
        if not design:
            return f"/* Design '{design_name}' not found */"

        colors = design.get("colors", {})
        typography = design.get("typography", {})

        css = ":root {\n"
        for name, value in colors.items():
            css += f"  --color-{name}: {value};\n"
        for name, value in typography.items():
            css_key = name.replace("font-", "").replace("-", "-")
            css += f"  --{css_key}: {value};\n"
        css += "}\n"
        return css

    def generate_component_css(self, component: str, design_name: str) -> str:
        """Generate CSS for a specific component using a design system."""
        design = self.get_design(design_name)
        if not design:
            return f"/* Design '{design_name}' not found */"

        components = design.get("components", {})
        colors = design.get("colors", {})
        comp = components.get(component, {})

        if not comp:
            return f"/* Component '{component}' not defined in {design_name} */"

        css = f".{component} {{\n"
        for prop, value in comp.items():
            css += f"  {prop}: {value};\n"
        css += "}\n"
        return css

    def process_task(self, task: str, context: dict | None = None) -> dict:
        """
        Process a design-related task.

        Args:
            task: Natural language description
            context: Optional context with design_name, component, etc.

        Returns:
            Result dict with generated CSS, recommendations, etc.
        """
        context = context or {}
        design_name = context.get("design_name", "linear")
        component = context.get("component")

        result = {
            "task": task,
            "design_used": design_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if "css" in task.lower() or "variable" in task.lower():
            result["css_variables"] = self.generate_css_variables(design_name)

        if component:
            result["component_css"] = self.generate_component_css(
                component, design_name
            )

        result["available_designs"] = self.list_designs()
        result["recommendation"] = self._recommend_design(task)

        return result

    def _recommend_design(self, task: str) -> str:
        """Recommend a design system based on task description."""
        task_lower = task.lower()
        if any(w in task_lower for w in ["dashboard", "admin", "minimal", "precise"]):
            return "linear - Clean, minimal, perfect for dashboards"
        if any(w in task_lower for w in ["landing", "marketing", "gradient", "modern"]):
            return "stripe - Polished, gradient-rich, great for marketing"
        if any(w in task_lower for w in ["docs", "content", "reading", "blog"]):
            return "notion - Warm, readable, content-focused"
        if any(w in task_lower for w in ["developer", "code", "api", "terminal"]):
            return "supabase - Dark, code-first, developer-friendly"
        if any(w in task_lower for w in ["clean", "simple", "fast", "deploy"]):
            return "vercel - Black and white precision"
        return "linear - Versatile default for most UI tasks"
