"""
Nutritional Axioms.

This module defines constraints that enforce daily nutritional targets
(calories and macronutrients).

Axioms include:
- Daily targets: calories, protein, carbohydrates, fat with configurable elastic margin
- Caloric distribution: calorie split across meals

The "Elastic Margin" allows tolerance around targets:
- DELTA_KCAL: calorie tolerance (e.g. ±10%)
- DELTA_MACRO: macronutrient tolerance (e.g. ±50%)
"""

from typing import List, Dict, Tuple, Any, Optional
from pulp import LpProblem, lpSum

from backend.config import (
    TARGET_KCAL, TARGET_PROT, TARGET_CARB, TARGET_FAT,
    DELTA_KCAL, DELTA_MACRO
)
from backend.config.axioms import NUTRITION_AXIOMS
from backend.config.constants import (
    KCAL_PER_GRAM_PROTEIN,
    KCAL_PER_GRAM_CARBOHYDRATE,
    KCAL_PER_GRAM_FAT
)
from backend.core.definitions import FoodItem, SLOTS


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


def _calculate_macro_targets_from_percentages(
    target_kcal: int,
    protein_percentage: float,
    carb_percentage: float,
    fat_percentage: float
) -> Tuple[float, float, float]:
    """
    Calculates macronutrient gram targets from caloric percentages.

    Formula: grams = (total_kcal * percentage) / kcal_per_gram

    Where:
    - Protein: 4 kcal per gram
    - Carbohydrates: 4 kcal per gram
    - Fat: 9 kcal per gram

    Args:
        target_kcal: Daily calorie target
        protein_percentage: Fraction of calories from protein (0.0-1.0)
        carb_percentage: Fraction of calories from carbohydrates (0.0-1.0)
        fat_percentage: Fraction of calories from fat (0.0-1.0)

    Returns:
        Tuple (target_protein_grams, target_carb_grams, target_fat_grams)
    """
    target_protein_grams = (target_kcal * protein_percentage) / KCAL_PER_GRAM_PROTEIN
    target_carb_grams = (target_kcal * carb_percentage) / KCAL_PER_GRAM_CARBOHYDRATE
    target_fat_grams = (target_kcal * fat_percentage) / KCAL_PER_GRAM_FAT

    return target_protein_grams, target_carb_grams, target_fat_grams


def _get_nutrition_targets(
    nutrition_targets: Optional[Dict]
) -> Tuple[int, float, float, float]:
    """
    Extracts nutritional targets from GUI configuration or uses defaults.

    Args:
        nutrition_targets: Dict with targets from the GUI, may be None

    Returns:
        Tuple (target_kcal, target_protein_g, target_carb_g, target_fat_g)
    """
    if nutrition_targets:
        target_kcal = nutrition_targets.get("kcal", TARGET_KCAL)

        # Convert percentages to fractions
        protein_pct = nutrition_targets.get("prot_pct", 20) / 100
        carb_pct = nutrition_targets.get("carb_pct", 55) / 100
        fat_pct = nutrition_targets.get("fat_pct", 25) / 100

        # Calculate grams from percentages
        target_prot, target_carb, target_fat = _calculate_macro_targets_from_percentages(
            target_kcal, protein_pct, carb_pct, fat_pct
        )
    else:
        target_kcal = TARGET_KCAL
        target_prot = TARGET_PROT
        target_carb = TARGET_CARB
        target_fat = TARGET_FAT

    return target_kcal, target_prot, target_carb, target_fat


def _get_delta_kcal(nutrition_targets: Optional[Dict]) -> float:
    """
    Extracts calorie tolerance from GUI configuration or uses default.

    Args:
        nutrition_targets: Dict with targets from the GUI, may be None

    Returns:
        Calorie tolerance as a decimal (e.g. 0.10 = ±10%)
    """
    if nutrition_targets and "delta_kcal" in nutrition_targets:
        return nutrition_targets["delta_kcal"]
    return DELTA_KCAL


def _get_delta_macro(nutrition_targets: Optional[Dict]) -> float:
    """
    Extracts macronutrient tolerance from GUI configuration or uses default.

    Args:
        nutrition_targets: Dict with targets from the GUI, may be None

    Returns:
        Macro tolerance as a decimal (e.g. 0.50 = ±50%)
    """
    if nutrition_targets and "delta_macro" in nutrition_targets:
        return nutrition_targets["delta_macro"]
    return DELTA_MACRO


def _is_slot_disabled(slot_key: str, axioms_config: Optional[Dict]) -> bool:
    """
    Returns True if the meal_validity axiom for this slot is disabled.

    When a slot is disabled, it is forced empty by meal_validity and must be
    excluded from nutritional constraints that reference that specific slot.

    Args:
        slot_key: Lowercase slot name ("breakfast", "lunch", "snack", "dinner")
        axioms_config: Full axiom configuration from the GUI

    Returns:
        True if the slot's meal_validity axiom is explicitly disabled
    """
    if not axioms_config:
        return False
    return not axioms_config.get("meal_validity", {}).get(slot_key, {}).get("enabled", True)


def _get_active_kcal_fraction(
    axioms_config: Optional[Dict],
    default_config: Dict
) -> float:
    """
    Returns the fraction of daily kcal expected from active (non-disabled) meal slots.

    When a meal_validity axiom is disabled, that slot is forced empty.
    The daily kcal target must be scaled down by the expected contribution
    of the disabled slots, otherwise the remaining meals cannot reach the target.

    The expected contribution of each slot is derived from the midpoint of its
    meal_distribution range (e.g. breakfast: (15%+25%)/2 = 20%).

    Args:
        axioms_config: Full axiom configuration from the GUI
        default_config: Default NUTRITION_AXIOMS configuration

    Returns:
        Fraction in (0, 1] representing the share of kcal expected from active slots
    """
    meal_dist_config = _get_axiom_config(
        axioms_config, "nutrition", "meal_distribution", default_config["meal_distribution"]
    )
    dist_params = meal_dist_config.get("params", {})

    disabled_fraction = 0.0
    for slot in SLOTS:
        slot_key = slot.lower()
        if _is_slot_disabled(slot_key, axioms_config) and slot_key in dist_params:
            slot_params = dist_params[slot_key]
            midpoint = (slot_params["min_pct"] + slot_params["max_pct"]) / 2
            disabled_fraction += midpoint

    return max(0.01, 1.0 - disabled_fraction)


def _get_daily_food_quantity_pairs(
    quantity_variables: Dict,
    food_data: List[FoodItem],
    day: str
) -> List[Tuple[FoodItem, Any]]:
    """
    Creates (food, quantity_variable) pairs for all foods across a day.

    Args:
        quantity_variables: Quantity variables {(food_id, day, slot): var}
        food_data: List of food items
        day: Day name

    Returns:
        List of (FoodItem, LpVariable) tuples
    """
    pairs = []
    for food in food_data:
        for slot in SLOTS:
            pairs.append((food, quantity_variables[food.id, day, slot]))
    return pairs


def _get_slot_food_quantity_pairs(
    quantity_variables: Dict,
    food_data: List[FoodItem],
    day: str,
    slot: str
) -> List[Tuple[FoodItem, Any]]:
    """
    Creates (food, quantity_variable) pairs for a single meal slot.

    Args:
        quantity_variables: Quantity variables
        food_data: List of food items
        day: Day name
        slot: Meal slot name

    Returns:
        List of (FoodItem, LpVariable) tuples
    """
    return [(food, quantity_variables[food.id, day, slot]) for food in food_data]


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def apply_nutrition_axioms(
    problem: LpProblem,
    quantity_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    nutrition_targets: Optional[Dict] = None,
    axioms_config: Optional[Dict] = None
) -> None:
    """
    Applies nutritional axioms for a given day.

    These axioms ensure the diet meets targets for:
    - Daily calories (with configurable elastic margin)
    - Macronutrients: protein, carbohydrates, fat (with configurable margin)
    - Caloric distribution across meals

    Args:
        problem: The PuLP optimization problem
        quantity_variables: Quantity variables {(food_id, day, slot): var}
        day: Day name (e.g. "Monday")
        food_data: List of food items
        nutrition_targets: GUI targets (optional), includes delta_kcal and delta_macro
        axioms_config: Axioms configuration from the GUI (optional)
    """
    default_config = NUTRITION_AXIOMS

    # Calculate nutritional targets
    target_kcal, target_prot, target_carb, target_fat = _get_nutrition_targets(nutrition_targets)

    # Extract deltas from nutrition_targets or use defaults
    delta_kcal = _get_delta_kcal(nutrition_targets)
    delta_macro = _get_delta_macro(nutrition_targets)

    # Apply individual axioms
    _apply_daily_macros_axiom(
        problem, quantity_variables, day, food_data,
        target_kcal, target_prot, target_carb, target_fat,
        delta_kcal, delta_macro,
        axioms_config, default_config
    )

    _apply_meal_distribution_axiom(
        problem, quantity_variables, day, food_data,
        target_kcal,
        axioms_config, default_config
    )


# =============================================================================
# SPECIFIC AXIOMS
# =============================================================================

def _apply_daily_macros_axiom(
    problem: LpProblem,
    quantity_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    target_kcal: int,
    target_prot: float,
    target_carb: float,
    target_fat: float,
    delta_kcal: float,
    delta_macro: float,
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """
    Applies daily macronutrient constraints.

    For each nutrient (kcal, protein, carbohydrates, fat), enforces that
    the daily total lies within the interval:
        target * (1 - delta) <= total <= target * (1 + delta)

    This "elastic margin" allows flexibility in meeting targets.

    Args:
        problem: The optimization problem
        quantity_variables: Quantity variables
        day: Day name
        food_data: List of food items
        target_kcal: Calorie target
        target_prot: Protein target (grams)
        target_carb: Carbohydrate target (grams)
        target_fat: Fat target (grams)
        delta_kcal: Calorie tolerance (decimal, e.g. 0.10 = ±10%)
        delta_macro: Macronutrient tolerance (decimal, e.g. 0.50 = ±50%)
        axioms_config: Configuration from the GUI
        default_config: Default configuration
    """
    config = _get_axiom_config(
        axioms_config, "nutrition", "daily_nutrition", default_config["daily_nutrition"]
    )

    if not config["enabled"]:
        return

    # Scale targets proportionally when some meal slots are disabled.
    # Disabled slots are forced empty by meal_validity, so their caloric
    # contribution is 0. The target must reflect only the active meals.
    active_fraction = _get_active_kcal_fraction(axioms_config, default_config)
    effective_kcal = target_kcal * active_fraction
    effective_prot = target_prot * active_fraction
    effective_carb = target_carb * active_fraction
    effective_fat  = target_fat  * active_fraction

    # Prepare (food, quantity) pairs for the day
    daily_food_quantity_pairs = _get_daily_food_quantity_pairs(
        quantity_variables, food_data, day
    )

    # --- CALORIE CONSTRAINTS ---
    # Formula: total_kcal = sum( kcal_per_100g / 100 * quantity_grams )
    total_daily_kcal = lpSum([
        (food.kcal_100g / 100) * quantity_var
        for food, quantity_var in daily_food_quantity_pairs
    ])

    kcal_min = effective_kcal * (1 - delta_kcal)
    kcal_max = effective_kcal * (1 + delta_kcal)

    problem += total_daily_kcal >= kcal_min, f"Nutrition_Kcal_Min_{day}"
    problem += total_daily_kcal <= kcal_max, f"Nutrition_Kcal_Max_{day}"

    # --- PROTEIN CONSTRAINTS ---
    total_daily_protein = lpSum([
        (food.prot_100g / 100) * quantity_var
        for food, quantity_var in daily_food_quantity_pairs
    ])

    protein_min = effective_prot * (1 - delta_macro)
    protein_max = effective_prot * (1 + delta_macro)

    problem += total_daily_protein >= protein_min, f"Nutrition_Protein_Min_{day}"
    problem += total_daily_protein <= protein_max, f"Nutrition_Protein_Max_{day}"

    # --- CARBOHYDRATE CONSTRAINTS ---
    total_daily_carbs = lpSum([
        (food.carb_100g / 100) * quantity_var
        for food, quantity_var in daily_food_quantity_pairs
    ])

    carb_min = effective_carb * (1 - delta_macro)
    carb_max = effective_carb * (1 + delta_macro)

    problem += total_daily_carbs >= carb_min, f"Nutrition_Carbs_Min_{day}"
    problem += total_daily_carbs <= carb_max, f"Nutrition_Carbs_Max_{day}"

    # --- FAT CONSTRAINTS ---
    total_daily_fat = lpSum([
        (food.fat_100g / 100) * quantity_var
        for food, quantity_var in daily_food_quantity_pairs
    ])

    fat_min = effective_fat * (1 - delta_macro)
    fat_max = effective_fat * (1 + delta_macro)

    problem += total_daily_fat >= fat_min, f"Nutrition_Fat_Min_{day}"
    problem += total_daily_fat <= fat_max, f"Nutrition_Fat_Max_{day}"


def _apply_meal_distribution_axiom(
    problem: LpProblem,
    quantity_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    target_kcal: int,
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """
    Applies caloric distribution constraints across meals.

    Ensures each meal contributes an appropriate percentage of daily calories.
    For example:
    - Breakfast: 15-25% of calories
    - Lunch: 35-40% of calories
    - Snack: 5-10% of calories
    - Dinner: 30-35% of calories

    Args:
        problem: The optimization problem
        quantity_variables: Quantity variables
        day: Day name
        food_data: List of food items
        target_kcal: Daily calorie target
        axioms_config: Configuration from the GUI
        default_config: Default configuration
    """
    config = _get_axiom_config(
        axioms_config, "nutrition", "meal_distribution", default_config["meal_distribution"]
    )

    if not config["enabled"]:
        return

    distribution_params = config["params"]

    for slot in SLOTS:
        slot_key = slot.lower()  # "breakfast", "lunch", "snack", "dinner"

        if slot_key not in distribution_params:
            continue

        # Skip distribution constraint for slots disabled in meal_validity.
        # The slot is forced empty, so no kcal can come from it.
        if _is_slot_disabled(slot_key, axioms_config):
            continue

        slot_params = distribution_params[slot_key]
        min_percentage = slot_params["min_pct"]
        max_percentage = slot_params["max_pct"]

        # Calculate calories for this slot
        slot_food_quantity_pairs = _get_slot_food_quantity_pairs(
            quantity_variables, food_data, day, slot
        )

        slot_kcal = lpSum([
            (food.kcal_100g / 100) * quantity_var
            for food, quantity_var in slot_food_quantity_pairs
        ])

        # Apply distribution constraints
        kcal_min_for_slot = target_kcal * min_percentage
        kcal_max_for_slot = target_kcal * max_percentage

        problem += (
            slot_kcal >= kcal_min_for_slot,
            f"MealDistribution_Kcal_Min_{slot}_{day}"
        )
        problem += (
            slot_kcal <= kcal_max_for_slot,
            f"MealDistribution_Kcal_Max_{slot}_{day}"
        )
