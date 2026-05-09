"""
Custom CSS Styles for the Streamlit Application.

This module defines and applies custom CSS styles to customize
the appearance of the Streamlit interface.

Styles cover:
- Application background and text colors
- Sidebar dimensions
- Button styling
- Custom status bar
- Compact layout for specific widgets
"""

import streamlit as st


# =============================================================================
# COLOR CONSTANTS
# =============================================================================

# Main theme colors
BACKGROUND_COLOR = "#0e1117"
TEXT_COLOR = "#ffffff"

# Button colors
BUTTON_BACKGROUND = "#2c5d63"
BUTTON_HOVER_BACKGROUND = "#3d7a82"
BUTTON_HOVER_BORDER = "#4ade80"

# Status bar colors
STATUS_BAR_BACKGROUND = "#1a1c23"
STATUS_BAR_TEXT = "#4ade80"
STATUS_BAR_BORDER = "#4ade80"


# =============================================================================
# SIZE CONSTANTS
# =============================================================================

SIDEBAR_MIN_WIDTH = "400px"
SIDEBAR_MAX_WIDTH = "500px"
BUTTON_HEIGHT = "3em"
BUTTON_BORDER_RADIUS = "5px"
STATUS_BAR_BORDER_WIDTH = "5px"


# =============================================================================
# CSS DEFINITION
# =============================================================================

CUSTOM_CSS = f"""
<style>
/* =========================================
   GENERAL APPLICATION THEME
   ========================================= */
.stApp {{
    background-color: {BACKGROUND_COLOR};
    color: {TEXT_COLOR};
}}


/* =========================================
   SIDEBAR
   ========================================= */
[data-testid="stSidebar"] {{
    min-width: {SIDEBAR_MIN_WIDTH};
    max-width: {SIDEBAR_MAX_WIDTH};
}}


/* =========================================
   BUTTONS
   ========================================= */
.stButton>button {{
    width: 100%;
    background-color: {BUTTON_BACKGROUND};
    color: white;
    font-weight: bold;
    border-radius: {BUTTON_BORDER_RADIUS};
    height: {BUTTON_HEIGHT};
    transition: 0.3s;
}}

.stButton>button:hover {{
    background-color: {BUTTON_HOVER_BACKGROUND};
    border-color: {BUTTON_HOVER_BORDER};
}}


/* =========================================
   CUSTOM STATUS BAR
   ========================================= */
.status-bar {{
    background-color: {STATUS_BAR_BACKGROUND};
    padding: 10px;
    border-radius: {BUTTON_BORDER_RADIUS};
    font-family: monospace;
    color: {STATUS_BAR_TEXT};
    border-left: {STATUS_BAR_BORDER_WIDTH} solid {STATUS_BAR_BORDER};
}}


/* =========================================
   WIDGET LAYOUT OPTIMIZATIONS
   ========================================= */

/* Compacts the st.feedback widget (stars) for better alignment */
[data-testid="stFeedbackAdornment"] {{
    padding: 0px !important;
    gap: 2px !important;
}}

/* Reduces vertical spacing between elements in columns */
div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] {{
    gap: 0rem !important;
}}
</style>
"""


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def apply_custom_css() -> None:
    """
    Applies custom CSS styles to the Streamlit application.

    This function must be called at the start of the application,
    before rendering any component, to ensure styles are applied correctly.

    Styles are injected as raw HTML using the `unsafe_allow_html=True`
    parameter which allows insertion of custom CSS.
    """
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
