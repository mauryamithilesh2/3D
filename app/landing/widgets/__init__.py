"""
app/landing/widgets package
============================
Landing page UI components exporting LogoWidget and ModuleCard.
"""

from app.landing.widgets.logo_widget import LogoWidget
from app.landing.widgets.module_card import ModuleCard
from app.landing.widgets.status_pill import StatusPill

__all__ = [
    "LogoWidget",
    "ModuleCard",
    "StatusPill",
]
