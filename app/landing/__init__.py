"""
app/landing package
===================
Top-level landing page package exporting LandingWindow and LandingPage.
"""

from app.landing.landing_page import LandingPage
from app.landing.landing_window import LandingWindow

__all__ = [
    "LandingPage",
    "LandingWindow",
]
