"""
ui/styles.py
============
Shared Qt stylesheets and factory functions for industrial themes (Dark and Light)
(coordinate input fields, buttons, group boxes, tables, tabs, toolbar,
status bar, and divider lines) -- modeled after Zeiss Calypso / PC-DMIS /
PolyWorks control-panel chrome.
"""

from __future__ import annotations

from typing import Any
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QFrame, QLineEdit

from config import COORD_INPUT_DECIMALS, COORD_MAX, COORD_MIN
from config.colors import get_active_theme, set_active_theme

# ---------------------------------------------------------------------------
# Theme Palettes
# ---------------------------------------------------------------------------
DARK_PALETTE: dict[str, str] = {
    "BG_APP": "#14161b",
    "BG_PANEL": "#1b1e25",
    "BG_CARD": "#20242c",
    "BG_INPUT": "#262b34",
    "BG_INPUT_FOCUS": "#2a3140",
    "BORDER": "#333a48",
    "BORDER_LIGHT": "#3d4557",
    "TEXT_PRIMARY": "#e7eaf1",
    "TEXT_SECONDARY": "#9aa3b5",
    "TEXT_MUTED": "#6b7386",
    "ACCENT": "#4f8ff7",
    "ACCENT_HOVER": "#6ba2ff",
    "ACCENT_PRESSED": "#3d74d6",
    "DANGER": "#e0596b",
    "DANGER_BG": "#3a2429",
}

LIGHT_PALETTE: dict[str, str] = {
    "BG_APP": "#f4f5f7",
    "BG_PANEL": "#eceef2",
    "BG_CARD": "#ffffff",
    "BG_INPUT": "#ffffff",
    "BG_INPUT_FOCUS": "#eaf1ff",
    "BORDER": "#d3d7e0",
    "BORDER_LIGHT": "#b7bdcc",
    "TEXT_PRIMARY": "#1c1f26",
    "TEXT_SECONDARY": "#4c5568",
    "TEXT_MUTED": "#8b93a3",
    "ACCENT": "#2f6fe0",
    "ACCENT_HOVER": "#1f5bcc",
    "ACCENT_PRESSED": "#18449e",
    "DANGER": "#c73c50",
    "DANGER_BG": "#fbe4e7",
}


def get_palette() -> dict[str, str]:
    """Return active theme palette dictionary."""
    return LIGHT_PALETTE if get_active_theme() == "light" else DARK_PALETTE


def get_ui_color(key: str) -> str:
    """Return hex color value for given key from active palette."""
    palette = get_palette()
    return palette.get(key, DARK_PALETTE.get(key, "#ffffff"))


# ---------------------------------------------------------------------------
# Dynamic Stylesheet Builders
# ---------------------------------------------------------------------------

def get_app_stylesheet() -> str:
    p = get_palette()
    return f"""
    QMainWindow, QWidget {{
        background-color: {p['BG_APP']};
        color: {p['TEXT_PRIMARY']};
        font-family: 'Segoe UI', 'Inter', sans-serif;
        font-size: 12px;
    }}
    QSplitter::handle {{
        background-color: {p['BORDER']};
    }}
    QSplitter::handle:hover {{
        background-color: {p['ACCENT']};
    }}
    QScrollBar:vertical {{
        background: {p['BG_PANEL']};
        width: 11px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {p['BORDER_LIGHT']};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {p['ACCENT']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{
        background: {p['BG_PANEL']};
        height: 11px;
    }}
    QScrollBar::handle:horizontal {{
        background: {p['BORDER_LIGHT']};
        border-radius: 4px;
        min-width: 24px;
    }}
    QToolTip {{
        background-color: {p['BG_CARD']};
        color: {p['TEXT_PRIMARY']};
        border: 1px solid {p['BORDER_LIGHT']};
        padding: 4px 6px;
    }}
"""


def get_toolbar_style() -> str:
    p = get_palette()
    checked_bg = "#dbe6fe" if get_active_theme() == "light" else "#223252"
    return f"""
    QToolBar {{
        background-color: {p['BG_PANEL']};
        border: none;
        border-bottom: 1px solid {p['BORDER']};
        padding: 3px 6px;
        spacing: 4px;
    }}
    QToolButton {{
        color: {p['TEXT_SECONDARY']};
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 11px;
        font-weight: 600;
    }}
    QToolButton:hover {{
        background-color: {p['BG_INPUT']};
        color: {p['TEXT_PRIMARY']};
        border-color: {p['BORDER_LIGHT']};
    }}
    QToolButton:checked {{
        background-color: {checked_bg};
        color: {p['ACCENT_HOVER']};
        border-color: {p['ACCENT']};
    }}
    QToolBar::separator {{
        background-color: {p['BORDER']};
        width: 1px;
        margin: 4px 4px;
    }}
"""


def get_statusbar_style() -> str:
    p = get_palette()
    return f"""
    QStatusBar {{
        background-color: {p['BG_PANEL']};
        color: {p['TEXT_SECONDARY']};
        border-top: 1px solid {p['BORDER']};
        font-size: 11px;
    }}
    QStatusBar::item {{ border: none; }}
    QStatusBar QLabel {{ color: {p['TEXT_SECONDARY']}; padding: 0 8px; }}
"""


def get_panel_header_style() -> str:
    p = get_palette()
    return f"color: {p['TEXT_PRIMARY']}; font-size: 13px; font-weight: 700; letter-spacing: 0.3px;"


def get_subheader_style() -> str:
    p = get_palette()
    return f"color: {p['TEXT_SECONDARY']}; font-size: 10.5px; font-weight: 600; text-transform: uppercase;"


def get_tab_widget_style() -> str:
    p = get_palette()
    return f"""
    QTabWidget::pane {{
        border: 1px solid {p['BORDER']};
        background: {p['BG_CARD']};
        border-radius: 5px;
        top: -1px;
    }}
    QTabBar::tab {{
        background: {p['BG_PANEL']};
        color: {p['TEXT_SECONDARY']};
        padding: 6px 14px;
        font-weight: 600;
        font-size: 11px;
        border: 1px solid {p['BORDER']};
        border-bottom: none;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background: {p['BG_CARD']};
        color: {p['ACCENT_HOVER']};
        border-bottom: 2px solid {p['ACCENT']};
    }}
    QTabBar::tab:hover:!selected {{ color: {p['TEXT_PRIMARY']}; }}
"""


def get_table_style() -> str:
    p = get_palette()
    alt_bg = "#f0f2f5" if get_active_theme() == "light" else "#252a33"
    sel_bg = "#d0e1fd" if get_active_theme() == "light" else "#2a3f63"
    return f"""
    QTableWidget {{
        background-color: {p['BG_CARD']};
        alternate-background-color: {alt_bg};
        gridline-color: {p['BORDER']};
        color: {p['TEXT_PRIMARY']};
        font-size: 11px;
        border: none;
        selection-background-color: {sel_bg};
        selection-color: {p['TEXT_PRIMARY']};
    }}
    QHeaderView::section {{
        background-color: {p['BG_PANEL']};
        color: {p['TEXT_SECONDARY']};
        font-weight: 700;
        font-size: 10.5px;
        border: none;
        border-bottom: 1px solid {p['BORDER']};
        padding: 5px 4px;
    }}
    QTableWidget::item {{ padding: 3px 4px; }}
"""


def get_field_style() -> str:
    p = get_palette()
    return f"""
    QLineEdit {{
        background-color: {p['BG_INPUT']};
        color: {p['TEXT_PRIMARY']};
        border: 1px solid {p['BORDER']};
        border-radius: 3px;
        padding: 3px 6px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 12px;
        selection-background-color: {p['ACCENT']};
    }}
    QLineEdit:focus {{ border: 1px solid {p['ACCENT']}; background-color: {p['BG_INPUT_FOCUS']}; }}
    QLineEdit:disabled {{ color: {p['TEXT_MUTED']}; background-color: {p['BG_PANEL']}; }}
"""


def get_button_style() -> str:
    p = get_palette()
    pressed_bg = "#d9dfeb" if get_active_theme() == "light" else "#1c2129"
    return f"""
    QPushButton {{
        background-color: {p['BG_INPUT']};
        color: {p['TEXT_PRIMARY']};
        border: 1px solid {p['BORDER']};
        border-radius: 4px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background-color: {p['BG_INPUT_FOCUS']}; border-color: {p['BORDER_LIGHT']}; }}
    QPushButton:pressed {{ background-color: {pressed_bg}; }}
    QPushButton:disabled {{ color: {p['TEXT_MUTED']}; background-color: {p['BG_PANEL']}; border-color: {p['BORDER']}; }}
"""


def get_accent_button_style() -> str:
    p = get_palette()
    text_color = "#ffffff" if get_active_theme() == "light" else "#0d1117"
    return f"""
    QPushButton {{
        background-color: {p['ACCENT']};
        color: {text_color};
        border: none;
        border-radius: 4px;
        padding: 6px 10px;
        font-size: 12px;
        font-weight: 700;
    }}
    QPushButton:hover {{ background-color: {p['ACCENT_HOVER']}; }}
    QPushButton:pressed {{ background-color: {p['ACCENT_PRESSED']}; }}
"""


def get_group_style() -> str:
    p = get_palette()
    return f"""
    QGroupBox {{
        color: {p['TEXT_PRIMARY']};
        font-weight: 700;
        font-size: 12px;
        border: 1px solid {p['BORDER']};
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 8px;
        background-color: {p['BG_CARD']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
        color: {p['ACCENT_HOVER']};
    }}
"""


def get_remove_button_style() -> str:
    p = get_palette()
    border_col = "#e5b8bf" if get_active_theme() == "light" else "#5a2f38"
    hover_bg = "#f7d0d6" if get_active_theme() == "light" else "#472a30"
    return f"""
    QPushButton {{
        background-color: {p['DANGER_BG']};
        color: {p['DANGER']};
        border: 1px solid {border_col};
        border-radius: 3px;
        font-weight: 700;
    }}
    QPushButton:hover {{ background-color: {hover_bg}; }}
    QPushButton:disabled {{ color: {p['TEXT_MUTED']}; background-color: {p['BG_PANEL']}; border-color: {p['BORDER']}; }}
"""


def get_panel_bg_style() -> str:
    p = get_palette()
    return f"background-color: {p['BG_PANEL']};"


def get_card_bg_style() -> str:
    p = get_palette()
    return f"background-color: {p['BG_CARD']}; border: 1px solid {p['BORDER']}; border-radius: 5px;"


def get_combo_style() -> str:
    p = get_palette()
    sel_bg = "#d0e1fd" if get_active_theme() == "light" else "#2a3f63"
    return f"""
    QComboBox {{
        background-color: {p['BG_INPUT']};
        color: {p['TEXT_PRIMARY']};
        border: 1px solid {p['BORDER']};
        border-radius: 3px;
        padding: 4px 6px;
        font-size: 12px;
    }}
    QComboBox:hover {{ border-color: {p['BORDER_LIGHT']}; }}
    QComboBox::drop-down {{ border: none; width: 18px; }}
    QComboBox QAbstractItemView {{
        background-color: {p['BG_CARD']};
        color: {p['TEXT_PRIMARY']};
        selection-background-color: {sel_bg};
        border: 1px solid {p['BORDER_LIGHT']};
    }}
"""


def _make_coord_edit() -> QLineEdit:
    """Create a styled coordinate input with a bounded double validator."""
    edit = QLineEdit()
    validator = QDoubleValidator(COORD_MIN, COORD_MAX, COORD_INPUT_DECIMALS, edit)
    validator.setNotation(QDoubleValidator.StandardNotation)
    edit.setValidator(validator)
    edit.setFixedWidth(72)
    edit.setAlignment(Qt.AlignRight)
    edit.setStyleSheet(get_field_style())
    return edit


def _make_separator() -> QFrame:
    """Create a thin horizontal divider line."""
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    border = get_ui_color("BORDER")
    line.setStyleSheet(f"color: {border}; background-color: {border}; max-height: 1px;")
    return line


def __getattr__(name: str) -> Any:
    """Dynamic property lookup for backward compatibility."""
    p = get_palette()
    if name in p:
        return p[name]
    mapping = {
        "APP_STYLESHEET": get_app_stylesheet,
        "TOOLBAR_STYLE": get_toolbar_style,
        "STATUSBAR_STYLE": get_statusbar_style,
        "PANEL_HEADER_STYLE": get_panel_header_style,
        "SUBHEADER_STYLE": get_subheader_style,
        "TAB_WIDGET_STYLE": get_tab_widget_style,
        "TABLE_STYLE": get_table_style,
        "_FIELD_STYLE": get_field_style,
        "_BUTTON_STYLE": get_button_style,
        "_ACCENT_BUTTON_STYLE": get_accent_button_style,
        "_GROUP_STYLE": get_group_style,
        "_REMOVE_BUTTON_STYLE": get_remove_button_style,
        "PANEL_BG_STYLE": get_panel_bg_style,
        "CARD_BG_STYLE": get_card_bg_style,
        "_COMBO_STYLE": get_combo_style,
    }
    if name in mapping:
        return mapping[name]()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
