"""
Daily Frequency Axioms (Meso-Logic).

This module defines constraints that control food distribution
within a SINGLE DAY (24 hours).
Called "Meso-Logic" because it operates at an intermediate level between
the individual meal (micro) and the full diet (macro).

Axioms include:
- Vegetable volume: how many times vegetables must appear in a day
- Fruit limit: how many times fruit can appear in a day
- Anti-repetition: the same food cannot appear more than N times per day
"""

from typing import List, Dict, Any, Optional
from pulp import LpProblem, lpSum

from backend.core.definitions import FoodItem, TAGS, SLOTS
from backend.config.axioms import DAILY_FREQUENCY_AXIOMS


# =============================================================================
# CONSTANTS
# =============================================================================

TAG_VEGETABLES = TAGS["ALTRI"]["VERDURE"]["ROOT"]
TAG_FRUIT = TAGS["ALTRI"]["FRUTTA"]["ROOT"]
TAG_JOLLY = TAGS["TECNICI"]["JOLLY"]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_axiom_config(
    axioms_config: Optional[Dict],
    group: str,
    axiom: str,
    default_config: Dict
) -> Dict[str, Any]:
    """
    Retrieves axiom configuration from the GUI or falls back to defaults.

    Args:
        axioms_config: Configuration from the GUI (may be None)
        group: Axiom group name
        axiom: Specific axiom name
        default_config: Default configuration

    Returns:
        Dict with "enabled" and "params"
    """
    if axioms_config and group in axioms_config and axiom in axioms_config[group]:
        return axioms_config[group][axiom]
    return default_config


def _is_slot_disabled(slot_key: str, axioms_config: Optional[Dict]) -> bool:
    """Returns True if the meal_validity axiom for this slot is disabled."""
    if not axioms_config:
        return False
    return not axioms_config.get("meal_validity", {}).get(slot_key, {}).get("enabled", True)


def _get_daily_selection_vars_for_tag(
    selection_variables: Dict,
    food_data: List[FoodItem],
    day: str,
    tag: str
) -> List:
    """
    Returns selection variables for a given tag across all slots in a day.

    Args:
        selection_variables: Dictionary {(food_id, day, slot): var}
        food_data: List of food items
        day: Day name
        tag: Tag to search for in food items

    Returns:
        List of LpVariable objects
    """
    variables = []
    for food in food_data:
        if tag in food.tags:
            for slot in SLOTS:
                variables.append(selection_variables[food.id, day, slot])
    return variables


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def apply_daily_frequency_axioms(
    problem: LpProblem,
    selection_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    axioms_config: Optional[Dict] = None
) -> None:
    """
    Applies daily frequency axioms for a given day.

    These axioms control how many times certain food types can appear
    within a single day.

    Args:
        problem: The PuLP optimization problem
        selection_variables: Selection variables {(food_id, day, slot): var}
        day: Day name (e.g. "Monday")
        food_data: List of food items
        axioms_config: Configuration from the GUI
    """
    default_config = DAILY_FREQUENCY_AXIOMS

    # Apply individual axioms
    _apply_vegetable_volume_axiom(
        problem, selection_variables, day, food_data, axioms_config, default_config
    )

    _apply_fruit_limit_axiom(
        problem, selection_variables, day, food_data, axioms_config, default_config
    )

    _apply_anti_repetition_axiom(
        problem, selection_variables, day, food_data, axioms_config, default_config
    )


# =============================================================================
# SPECIFIC AXIOMS
# =============================================================================

def _apply_vegetable_volume_axiom(
    problem: LpProblem,
    selection_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """
    Applies the vegetable volume axiom.

    Ensures vegetables appear a minimum and maximum number of times per day.
    Important for adequate fiber and micronutrient intake.

    Example: min=1, max=2 means each day must have at least 1 and
    at most 2 servings of vegetables.

    Args:
        problem: The optimization problem
        selection_variables: Selection variables
        day: Day name
        food_data: List of food items
        axioms_config: Configuration from the GUI
        default_config: Default configuration
    """
    config = _get_axiom_config(
        axioms_config, "daily_frequency", "daily_vegetables", default_config["daily_vegetables"]
    )

    if not config["enabled"]:
        return

    params = config["params"]
    min_vegetables_per_day = params["min"]
    max_vegetables_per_day = params["max"]

    vegetable_selection_vars = _get_daily_selection_vars_for_tag(
        selection_variables, food_data, day, TAG_VEGETABLES
    )

    # Minimum constraint: at least N vegetable servings per day.
    # Vegetables only appear at lunch and dinner. If both are disabled the
    # minimum is structurally impossible, so we skip it in that case.
    lunch_active  = not _is_slot_disabled("lunch",  axioms_config)
    dinner_active = not _is_slot_disabled("dinner", axioms_config)
    if lunch_active or dinner_active:
        problem += (
            lpSum(vegetable_selection_vars) >= min_vegetables_per_day,
            f"Daily_Vegetables_Min_{day}"
        )

    # Maximum constraint: at most M vegetable servings per day
    problem += (
        lpSum(vegetable_selection_vars) <= max_vegetables_per_day,
        f"Daily_Vegetables_Max_{day}"
    )


def _apply_fruit_limit_axiom(
    problem: LpProblem,
    selection_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """
    Applies the fruit limit axiom.

    Limits the maximum number of fruit servings per day.
    Important for controlling simple sugar intake.

    Note: no minimum constraint since fruit is optional.

    Args:
        problem: The optimization problem
        selection_variables: Selection variables
        day: Day name
        food_data: List of food items
        axioms_config: Configuration from the GUI
        default_config: Default configuration
    """
    config = _get_axiom_config(
        axioms_config, "daily_frequency", "daily_fruit", default_config["daily_fruit"]
    )

    if not config["enabled"]:
        return

    params = config["params"]
    min_fruit_per_day = params["min"]
    max_fruit_per_day = params["max"]

    fruit_selection_vars = _get_daily_selection_vars_for_tag(
        selection_variables, food_data, day, TAG_FRUIT
    )

    if min_fruit_per_day > 0:
        problem += (
            lpSum(fruit_selection_vars) >= min_fruit_per_day,
            f"Daily_Fruit_Min_{day}"
        )

    problem += (
        lpSum(fruit_selection_vars) <= max_fruit_per_day,
        f"Daily_Fruit_Max_{day}"
    )


def _apply_anti_repetition_axiom(
    problem: LpProblem,
    selection_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """
    Applies the anti-repetition axiom.

    Prevents the same food from appearing too many times on the same day.
    Ensures variety in daily eating.

    "Jolly" foods (like oil, salt) are exempt from this constraint
    because it is normal to use them multiple times per day.

    Example: max_per_food=1 means each food can appear at most once
    per day (except jolly foods).

    Args:
        problem: The optimization problem
        selection_variables: Selection variables
        day: Day name
        food_data: List of food items
        axioms_config: Configuration from the GUI
        default_config: Default configuration
    """
    config = _get_axiom_config(
        axioms_config, "daily_frequency", "daily_variety", default_config["daily_variety"]
    )

    if not config["enabled"]:
        return

    params = config["params"]
    max_times_per_food_per_day = params["max_per_food"]

    for food in food_data:
        # Jolly foods are exempt from the anti-repetition constraint
        if TAG_JOLLY in food.tags:
            continue

        # Collect all selection variables for this food today
        food_daily_selection_vars = [
            selection_variables[food.id, day, slot]
            for slot in SLOTS
        ]

        # Constraint: this food can appear at most N times today
        problem += (
            lpSum(food_daily_selection_vars) <= max_times_per_food_per_day,
            f"Daily_AntiRepetition_{food.id}_{day}"
        )
