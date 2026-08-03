"""
app/landing/landing_style.py
============================
QSS stylesheet definitions for the Industrial Metrology Landing Page.
Designed for high contrast, dark black and charcoal typography, crisp cards,
and bold blue accent buttons.
"""

LANDING_STYLE_SHEET = """
QWidget#LandingPageContainer {
    background-color: #f1f5f9;
    color: #0f172a;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
}

/* Header Branding */
QWidget#LogoWidgetContainer {
    background-color: #212121;
    border-bottom: 1px solid #2a2f3d;
    padding: 24px 40px;
}

QLabel#HeaderCompanyName {
    color: #00b0ff;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
}

QLabel#HeaderTitle {
    color: #ffffff;
    font-size: 26px;
    font-weight: 700;
    margin-top: 2px;
}

QLabel#HeaderSubtitle {
    color: #9aa3b8;
    font-size: 13px;
    font-weight: 400;
    margin-top: 4px;
}

QLabel#HeaderVersionBadge {
    background-color: #1e2638;
    color: #4f8ff7;
    border: 1px solid #2d3b59;
    border-radius: 12px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 600;
}

/* Module Cards */
QFrame#ModuleCard {
    background-color: #ffffff;
    border: 2px solid #cbd5e1;
    border-radius: 14px;
}

QFrame#ModuleCard:hover {
    background-color: #ffffff;
    border: 2px solid #2563eb;
}

QLabel#CardBadge {
    background-color: #dbeafe;
    color: #1e40af;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#CardTitle {
    color: #334155;
    font-size: 18px;
    font-weight: 700;
}

QLabel#CardSubtitle {
    color: #64748b;
    font-size: 12px;
    font-weight: 500;
}

QLabel#CardBulletItem {
    color: #475569;
    font-size: 13px;
    font-weight: 600;
    padding-left: 2px;
}

/* Open Module Button */
QPushButton#OpenModuleBtn {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 11px 20px;
    font-size: 13px;
    font-weight: 700;
}

QPushButton#OpenModuleBtn:hover {
    background-color: #1d4ed8;
}

QPushButton#OpenModuleBtn:pressed {
    background-color: #1e40af;
}

/* Industrial Status Bar */
QFrame#LandingStatusBar {
    background-color: #101217;
    border-top: 1px solid #232733;
    padding: 10px 30px;
}

QLabel#StatusText {
    color: #9aa5b9;
    font-size: 12px;
}

QLabel#StatusPillReady {
    background-color: #102d20;
    color: #38ef7d;
    border: 1px solid #1c5235;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#StatusPillLicense {
    background-color: #1a273b;
    color: #4f8ff7;
    border: 1px solid #2b3e5e;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}
"""
