"""
app/landing/module_config.py
=============================
Configuration file for dynamic landing page module cards.
Adding a new dictionary here automatically renders a new module card in the UI.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Crisp SVG Icon Definitions tailored for dark industrial metrology UI
SVG_DISTANCE_ICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="48" height="48">
  <defs>
    <linearGradient id="distGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#4f8ff7"/>
      <stop offset="100%" stop-color="#0052cc"/>
    </linearGradient>
  </defs>
  <!-- Coordinate Grid Lines -->
  <line x1="8" y1="52" x2="56" y2="52" stroke="#3d4557" stroke-width="2" stroke-dasharray="2 2"/>
  <line x1="12" y1="8" x2="12" y2="56" stroke="#3d4557" stroke-width="2" stroke-dasharray="2 2"/>
  <!-- Point A -->
  <circle cx="18" cy="42" r="5" fill="url(#distGrad)"/>
  <circle cx="18" cy="42" r="2" fill="#ffffff"/>
  <!-- Point B -->
  <circle cx="48" cy="16" r="5" fill="url(#distGrad)"/>
  <circle cx="48" cy="16" r="2" fill="#ffffff"/>
  <!-- Dimension Line -->
  <line x1="22" y1="38" x2="44" y2="20" stroke="#00b0ff" stroke-width="2.5" stroke-linecap="round"/>
  <!-- Arrow heads -->
  <path d="M 22 38 L 28 36 L 25 41 Z" fill="#00b0ff"/>
  <path d="M 44 20 L 38 22 L 41 17 Z" fill="#00b0ff"/>
  <!-- Angle Arc -->
  <path d="M 18 28 A 14 14 0 0 1 32 42" fill="none" stroke="#6ba2ff" stroke-width="1.5" stroke-dasharray="3 3"/>
</svg>"""

SVG_CIRCULARITY_ICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="48" height="48">
  <defs>
    <linearGradient id="circGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00d2ff"/>
      <stop offset="100%" stop-color="#007acc"/>
    </linearGradient>
  </defs>
  <!-- Outer Concentric Circle -->
  <circle cx="32" cy="32" r="24" fill="none" stroke="url(#circGrad)" stroke-width="2.5"/>
  <!-- Inner Concentric Circle -->
  <circle cx="32" cy="32" r="14" fill="none" stroke="#3d74d6" stroke-width="2" stroke-dasharray="4 2"/>
  <!-- Center Point -->
  <circle cx="32" cy="32" r="3.5" fill="#ffffff"/>
  <!-- Crosshairs -->
  <line x1="32" y1="4" x2="32" y2="60" stroke="#4f8ff7" stroke-width="1.5" stroke-dasharray="2 2"/>
  <line x1="4" y1="32" x2="60" y2="32" stroke="#4f8ff7" stroke-width="1.5" stroke-dasharray="2 2"/>
  <!-- Radius Indicator Line -->
  <line x1="32" y1="32" x2="49" y2="15" stroke="#00b0ff" stroke-width="2"/>
  <circle cx="49" cy="15" r="2.5" fill="#00b0ff"/>
</svg>"""

SVG_PARALLELISM_ICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="48" height="48">
  <defs>
    <linearGradient id="paraGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38ef7d"/>
      <stop offset="100%" stop-color="#11998e"/>
    </linearGradient>
  </defs>
  <!-- Base Reference Surface -->
  <line x1="8" y1="46" x2="56" y2="46" stroke="#4f8ff7" stroke-width="3" stroke-linecap="round"/>
  <!-- Parallel Top Surface -->
  <line x1="8" y1="20" x2="56" y2="20" stroke="#00b0ff" stroke-width="3" stroke-linecap="round"/>
  <!-- Perpendicular Vertical Axis -->
  <line x1="22" y1="46" x2="22" y2="20" stroke="#6ba2ff" stroke-width="2" stroke-dasharray="3 3"/>
  <!-- 90 Degree Angle Square -->
  <path d="M 22 40 L 28 40 L 28 46" fill="none" stroke="#00b0ff" stroke-width="1.5"/>
  <circle cx="25" cy="43" r="1" fill="#00b0ff"/>
  <!-- Tolerance Zone Indicators -->
  <line x1="8" y1="14" x2="56" y2="14" stroke="#3d4557" stroke-width="1" stroke-dasharray="2 2"/>
  <line x1="8" y1="26" x2="56" y2="26" stroke="#3d4557" stroke-width="1" stroke-dasharray="2 2"/>
</svg>"""

MODULES: List[Dict[str, Any]] = [
    {
        "id": "distance",
        "title": "Distance & Coordinate Measurement",
        "subtitle": "3D Coordinate & Geometric Inspection",
        "badge": "Module 01",
        "description": [
            "Distance Measurement",
            "Coordinate Measurement",
            "Point Measurement",
            "Line Measurement",
            "Angle Measurement",
        ],
        "icon_svg": SVG_DISTANCE_ICON,
        "button_text": "Open Module",
    },
    {
        "id": "circularity",
        "title": "Circularity & Concentricity",
        "subtitle": "Radial Form & Alignment Evaluation",
        "badge": "Module 02",
        "description": [
            "Circularity",
            "Concentricity",
            "Radius",
            "Diameter",
            "Arc",
        ],
        "icon_svg": SVG_CIRCULARITY_ICON,
        "button_text": "Open Module",
    },
    {
        "id": "parallelism",
        "title": "Parallelism & Perpendicularity",
        "subtitle": "Orientation & Flatness Tolerancing",
        "badge": "Module 03",
        "description": [
            "Parallelism",
            "Perpendicularity",
            "Straightness",
            "Flatness",
            "Angularity",
        ],
        "icon_svg": SVG_PARALLELISM_ICON,
        "button_text": "Open Module",
    },
]
