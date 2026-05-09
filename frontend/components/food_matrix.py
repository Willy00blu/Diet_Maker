"""
Food Matrix Component - Food Selection and Preference Configuration.

Displays all available foods grouped by category, allowing the user to:
- Enable/disable each food for diet generation
- Set min/max portion ranges
- Assign a preference rating (stars)
"""

import streamlit as st
from typing import List, Tuple, Dict

from backend.core.definitions import FoodItem
from backend.config.food import FOODS_CONFIG
from backend.config.constants import (
    PORTION_STEP_THRESHOLD as SMALL_PORTION_THRESHOLD,
    PORTION_STEP_SMALL as SMALL_PORTION_STEP,
    PORTION_STEP_LARGE as LARGE_PORTION_STEP,
    PORTION_SLIDER_MAX_SMALL as SMALL_PORTION_MAX,
    PORTION_SLIDER_MAX_LARGE as LARGE_PORTION_MAX,
    FOOD_MATRIX_COLUMN_WEIGHTS as COLUMN_PROPORTIONS,
)


# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# Maps base tag -> (display category name, sort order)
FOOD_CATEGORY_MAPPING: Dict[str, Tuple[str, int]] = {
    "carbo_dolci":  ("Carbohydrates", 1),
    "carbo_salati": ("Carbohydrates", 1),
    "carne":        ("Proteins", 2),
    "pesce":        ("Proteins", 2),
    "uova":         ("Proteins", 2),
    "legumi":       ("Proteins", 2),
    "latte_dolce":  ("Proteins", 2),
    "latte_salato": ("Proteins", 2),
    "verdure":      ("Vegetables", 3),
    "frutta":       ("Fruit", 4),
    "grassi":       ("Fats", 5),
}

DEFAULT_CATEGORY = ("Other", 99)


# =============================================================================
# HELPERS
# =============================================================================

def _extract_base_tag(tag: str) -> str:
    """
    Extracts the base category from a full tag.

    Tags have the format "category_slot" (e.g. "carne_pra", "carbo_dolci_col").
    """
    parts = tag.split("_")
    if parts[0] in ("carbo", "latte") and len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"
    return parts[0]


def _get_food_category(food_item: FoodItem) -> Tuple[str, int]:
    """Returns (category_name, sort_order) for a food item."""
    for tag in food_item.tags:
        base_tag = _extract_base_tag(tag)
        if base_tag in FOOD_CATEGORY_MAPPING:
            return FOOD_CATEGORY_MAPPING[base_tag]
    return DEFAULT_CATEGORY


def _get_portion_slider_config(food_item: FoodItem) -> Tuple[int, int]:
    """Returns (step, max_value) for the portion slider of a food."""
    if food_item.portion_min < SMALL_PORTION_THRESHOLD:
        return SMALL_PORTION_STEP, SMALL_PORTION_MAX
    return LARGE_PORTION_STEP, LARGE_PORTION_MAX


def _round_to_step(value: float, step: int) -> int:
    return round(value / step) * step


# =============================================================================
# RENDERING COMPONENTS
# =============================================================================

def _render_food_row(food_item: FoodItem) -> None:
    """Renders a single row of the food matrix."""
    food_name = food_item.name

    col_checkbox, col_name, col_portions, col_rating = st.columns(COLUMN_PROPORTIONS)

    is_enabled = col_checkbox.checkbox(
        label="",
        value=st.session_state.food_enabled.get(food_name, True),
        key=f"check_{food_name}"
    )
    st.session_state.food_enabled[food_name] = is_enabled

    primary_tag = food_item.tags[0] if food_item.tags else ""
    col_name.markdown(f"**{food_name}**")
    col_name.caption(primary_tag)

    step, max_range = _get_portion_slider_config(food_item)

    current_portions = st.session_state.food_portions.get(
        food_name,
        (int(food_item.portion_min), int(food_item.portion_max))
    )

    portions_rounded = (
        max(step, _round_to_step(current_portions[0], step)),
        min(max_range, max(step, _round_to_step(current_portions[1], step)))
    )

    slider_options = list(range(step, max_range + 1, step))

    new_portions = col_portions.select_slider(
        label=f"portions_{food_name}",
        options=slider_options,
        value=portions_rounded,
        label_visibility="collapsed",
        key=f"slider_portions_{food_name}"
    )
    st.session_state.food_portions[food_name] = new_portions

    with col_rating:
        default_rating = FOODS_CONFIG.get(str(food_item.id), {}).get("preference", 3)
        current_rating = st.session_state.food_ratings.get(food_name, default_rating)

        feedback_result = st.feedback(
            "stars",
            key=f"stars_{food_name}",
            default=current_rating - 1
        )

        if feedback_result is not None:
            st.session_state.food_ratings[food_name] = feedback_result + 1


def _render_matrix_header() -> None:
    """Renders the column headers of the food matrix."""
    header_columns = st.columns(COLUMN_PROPORTIONS)
    header_columns[0].write("Sel")
    header_columns[1].write("**Ingredient**")
    header_columns[2].write("**Min/Max Portion (g)**")
    header_columns[3].write("**Enjoyment Rating**")


def _render_status_bar(food_data: List[FoodItem]) -> None:
    """Renders the status bar showing active food count."""
    active_count = sum(
        1 for is_enabled in st.session_state.food_enabled.values()
        if is_enabled
    )
    total_count = len(food_data)

    st.markdown(
        f'<div class="status-bar">Solver Status: Ready | '
        f'Active Items: {active_count}/{total_count}</div>',
        unsafe_allow_html=True
    )


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def render_food_matrix(food_data: List[FoodItem]) -> None:
    """
    Renders the full food matrix.

    Foods are sorted by category first, then alphabetically within each category.

    Args:
        food_data: List of food items from the database
    """
    _render_status_bar(food_data)

    with st.expander("🍽️ **Food Database & Matrix**", expanded=False):
        st.caption(
            "Configure each food item. "
            "The solver will prioritise foods with higher star ratings."
        )

        _render_matrix_header()
        st.divider()

        sorted_food_data = sorted(
            food_data,
            key=lambda food: (_get_food_category(food)[1], food.name)
        )

        current_category_name = None

        for food_item in sorted_food_data:
            category_name, _ = _get_food_category(food_item)

            if category_name != current_category_name:
                current_category_name = category_name
                st.subheader(category_name)

            _render_food_row(food_item)
