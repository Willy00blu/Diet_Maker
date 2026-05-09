"""
Streamlit Session State Management.

This module manages the initialization and handling of Streamlit's session_state,
which persists data across application reruns.

State managed includes:
- food_ratings: user preferences for each food (1-5 stars)
- food_enabled: which foods are enabled for selection
- food_portions: customized min/max portion ranges
- diet_result: result of the last generation (plan + cost)
- generating: flag indicating a generation is in progress
"""

import streamlit as st
from typing import List, Dict, Tuple

from backend.core.definitions import FoodItem
from backend.config.food import FOODS_CONFIG
from backend.config.constants import (
    PORTION_STEP_THRESHOLD as SMALL_PORTION_THRESHOLD,
    PORTION_STEP_SMALL as SMALL_PORTION_STEP,
    PORTION_STEP_LARGE as LARGE_PORTION_STEP,
    DEFAULT_FOOD_RATING as DEFAULT_RATING,
)


# =============================================================================
# CONSTANTS
# =============================================================================

# Default enabled state for foods not explicitly configured
DEFAULT_ENABLED = True


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _round_to_step(value: float, step: int) -> int:
    """
    Rounds a value to the nearest multiple of step.

    Used to align portion values with slider options.

    Args:
        value: Value to round
        step: Step to round to

    Returns:
        Rounded integer value
    """
    return round(value / step) * step


def _get_portion_step(food_item: FoodItem) -> int:
    """
    Determines the rounding step for a food item's portions.

    Foods with small portions (e.g. oil, butter) use smaller steps
    for greater precision.

    Args:
        food_item: The food item to determine the step for

    Returns:
        Step in grams (5 or 10)
    """
    if food_item.portion_min < SMALL_PORTION_THRESHOLD:
        return SMALL_PORTION_STEP
    return LARGE_PORTION_STEP


def _get_food_config(food_item: FoodItem) -> Dict:
    """
    Retrieves a food item's configuration from FOODS_CONFIG.

    Args:
        food_item: The food item to retrieve configuration for

    Returns:
        Configuration dictionary (empty if not found)
    """
    return FOODS_CONFIG.get(str(food_item.id), {})


# =============================================================================
# STATE SECTION INITIALIZATION
# =============================================================================

def _init_food_ratings(food_data: List[FoodItem]) -> None:
    """
    Initializes preference ratings (stars) for each food item.

    Reads default values from FOODS_CONFIG, using DEFAULT_RATING
    as a fallback if not specified.

    Args:
        food_data: List of available food items
    """
    if "food_ratings" in st.session_state:
        return

    st.session_state.food_ratings = {
        food.name: _get_food_config(food).get("preference", DEFAULT_RATING)
        for food in food_data
    }


def _init_food_enabled(food_data: List[FoodItem]) -> None:
    """
    Initializes the enabled state (checkbox) for each food item.

    Reads the 'selectable' field from FOODS_CONFIG to determine the initial
    checkbox state. Foods with selectable=False will appear in the GUI
    but will be unchecked by default.

    Args:
        food_data: List of available food items
    """
    if "food_enabled" in st.session_state:
        return

    st.session_state.food_enabled = {
        food.name: _get_food_config(food).get("selectable", DEFAULT_ENABLED)
        for food in food_data
    }


def _init_food_portions(food_data: List[FoodItem]) -> None:
    """
    Initializes min/max portion ranges for each food item.

    Uses values from the food database, rounded to the appropriate step
    for the UI slider.

    Args:
        food_data: List of available food items
    """
    if "food_portions" in st.session_state:
        return

    portions = {}

    for food in food_data:
        step = _get_portion_step(food)
        portion_min_rounded = _round_to_step(food.portion_min, step)
        portion_max_rounded = _round_to_step(food.portion_max, step)
        portions[food.name] = (portion_min_rounded, portion_max_rounded)

    st.session_state.food_portions = portions


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def init_session_state(food_data: List[FoodItem]) -> None:
    """
    Initializes session_state with all default values.

    Must be called at application startup to ensure all required keys
    are present in session_state.

    Streamlit's session_state persists across page reruns,
    allowing user selections to be maintained.

    Args:
        food_data: List of food items from the database, needed to
                   initialize default values for each food item
    """
    _init_food_ratings(food_data)
    _init_food_enabled(food_data)
    _init_food_portions(food_data)
