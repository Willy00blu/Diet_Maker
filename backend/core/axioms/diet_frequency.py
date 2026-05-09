"""
Diet Frequency Axioms (Macro-Logic).

This module defines constraints that control food distribution
across the ENTIRE diet period (week or configured duration).
Called "Macro-Logic" because it operates at the full-diet level.

Axioms include:
- D1: Meat limit (2-4 times per week)
- D2: Fish requirement (2-4 times per week)
- D3: Legume centrality (2-5 times per week)
- D4: Specific variety (same food max N times)
- D5: Logistical feasibility (meal prep)
"""

from typing import List, Dict, Any, Optional
from pulp import LpProblem, lpSum, LpVariable, LpBinary

from backend.core.definitions import FoodItem, TAGS, SLOTS
from backend.config.axioms import DIET_FREQUENCY_AXIOMS


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


def apply_diet_frequency_axioms(
    problem: LpProblem,
    selection_variables: Dict,
    food_data: List[FoodItem],
    active_days: List[str],
    axioms_config: Optional[Dict] = None
) -> None:
    """
    Applies diet frequency axioms.

    These axioms control how many times certain food types can appear
    across the entire diet period.

    Args:
        problem: The PuLP optimization problem
        selection_variables: Selection variables {(food_id, day, slot): var}
        food_data: List of food items
        active_days: List of active days (e.g. ["Monday", "Tuesday"])
        axioms_config: Configuration from the GUI
    """
    default_config = DIET_FREQUENCY_AXIOMS

    def get_selection_vars_for_tag_across_diet(tag: str) -> List:
        """
        Returns all selection variables for a given tag across
        all days and slots in the diet.
        """
        return [
            selection_variables[food.id, day, slot]
            for food in food_data
            for day in active_days
            for slot in SLOTS
            if tag in food.tags
        ]

    # =========================================================================
    # AXIOM D1: MEAT LIMIT
    # Controls how many times meat appears in the diet (min to max)
    # =========================================================================
    _apply_meat_frequency_axiom(
        problem, get_selection_vars_for_tag_across_diet, axioms_config, default_config
    )

    # =========================================================================
    # AXIOM D2: FISH REQUIREMENT
    # Controls how many times fish appears in the diet (min to max)
    # =========================================================================
    _apply_fish_frequency_axiom(
        problem, get_selection_vars_for_tag_across_diet, axioms_config, default_config
    )

    # =========================================================================
    # AXIOM D3: LEGUME CENTRALITY
    # Controls how many times legumes appear in the diet (min to max)
    # =========================================================================
    _apply_legumes_frequency_axiom(
        problem, get_selection_vars_for_tag_across_diet, axioms_config, default_config
    )

    # =========================================================================
    # AXIOM D4: SPECIFIC VARIETY
    # Limits how many times the same food can appear in the diet
    # =========================================================================
    _apply_variety_axiom(
        problem, selection_variables, food_data, active_days, axioms_config, default_config
    )

    # =========================================================================
    # AXIOM D5: LOGISTICAL FEASIBILITY (Meal Prep)
    # If a food is used, it must be used at least N times
    # (to make preparing it in advance worthwhile)
    # =========================================================================
    _apply_meal_prep_axiom(
        problem, selection_variables, food_data, active_days, axioms_config, default_config
    )


# =============================================================================
# HELPER FUNCTIONS FOR INDIVIDUAL AXIOMS
# =============================================================================

def _apply_meat_frequency_axiom(
    problem: LpProblem,
    get_vars_func,
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """Applies the meat frequency constraint."""
    config = _get_axiom_config(axioms_config, "diet_frequency", "diet_meat", default_config["diet_meat"])

    if not config["enabled"]:
        return

    params = config["params"]
    meat_tag = TAGS["PROTEINE"]["CARNE"]["ROOT"]
    meat_selection_vars = get_vars_func(meat_tag)

    problem += lpSum(meat_selection_vars) >= params["min"], "Diet_Meat_Min"
    problem += lpSum(meat_selection_vars) <= params["max"], "Diet_Meat_Max"


def _apply_fish_frequency_axiom(
    problem: LpProblem,
    get_vars_func,
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """Applies the fish frequency constraint."""
    config = _get_axiom_config(axioms_config, "diet_frequency", "diet_fish", default_config["diet_fish"])

    if not config["enabled"]:
        return

    params = config["params"]
    fish_tag = TAGS["PROTEINE"]["PESCE"]["ROOT"]
    fish_selection_vars = get_vars_func(fish_tag)

    problem += lpSum(fish_selection_vars) >= params["min"], "Diet_Fish_Min"
    problem += lpSum(fish_selection_vars) <= params["max"], "Diet_Fish_Max"


def _apply_legumes_frequency_axiom(
    problem: LpProblem,
    get_vars_func,
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """Applies the legumes frequency constraint."""
    config = _get_axiom_config(axioms_config, "diet_frequency", "diet_legumes", default_config["diet_legumes"])

    if not config["enabled"]:
        return

    params = config["params"]
    legumes_tag = TAGS["PROTEINE"]["LEGUMI"]["ROOT"]
    legumes_selection_vars = get_vars_func(legumes_tag)

    problem += lpSum(legumes_selection_vars) >= params["min"], "Diet_Legumes_Min"
    problem += lpSum(legumes_selection_vars) <= params["max"], "Diet_Legumes_Max"


def _apply_variety_axiom(
    problem: LpProblem,
    selection_variables: Dict,
    food_data: List[FoodItem],
    active_days: List[str],
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """
    Applies the variety constraint: each food can appear at most N times.

    "Jolly" foods (like oil, salt) have a higher limit
    because it is normal to use them more frequently.
    """
    config = _get_axiom_config(axioms_config, "diet_frequency", "diet_variety", default_config["diet_variety"])

    if not config["enabled"]:
        return

    params = config["params"]
    jolly_tag = TAGS["TECNICI"]["JOLLY"]
    max_times_normal = params["max_normal"]
    max_times_jolly = params["max_jolly"]

    for food in food_data:
        # Collect all selection variables for this food across the diet
        food_selection_vars_across_diet = [
            selection_variables[food.id, day, slot]
            for day in active_days
            for slot in SLOTS
        ]

        # Jolly foods have a higher limit
        if jolly_tag in food.tags:
            problem += (
                lpSum(food_selection_vars_across_diet) <= max_times_jolly,
                f"Diet_Variety_Jolly_{food.id}"
            )
        else:
            problem += (
                lpSum(food_selection_vars_across_diet) <= max_times_normal,
                f"Diet_Variety_Normal_{food.id}"
            )


def _apply_meal_prep_axiom(
    problem: LpProblem,
    selection_variables: Dict,
    food_data: List[FoodItem],
    active_days: List[str],
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """
    Applies the meal prep constraint: if a food is used, it must be
    used at least N times.

    This makes sense for foods that require preparation (meat, fish,
    legumes, carbohydrates). If you cook chicken, you use it at least
    twice in the week to avoid wasting preparation time.

    Mathematical implementation:
    - z = binary variable (1 if the food is used at least once)
    - sum(selections) <= max_total * z  (if z=0, no selections)
    - sum(selections) >= min_if_used * z (if z=1, at least min_if_used selections)
    """
    config = _get_axiom_config(axioms_config, "diet_frequency", "meal_prep", default_config["meal_prep"])

    if not config["enabled"]:
        return

    params = config["params"]
    jolly_tag = TAGS["TECNICI"]["JOLLY"]
    max_total = params["max_total"]
    min_if_used = params["min_if_used"]

    # Tags for foods that require preparation
    meal_prep_tags = [
        TAGS["PROTEINE"]["CARNE"]["ROOT"],
        TAGS["PROTEINE"]["PESCE"]["ROOT"],
        TAGS["PROTEINE"]["LEGUMI"]["ROOT"],
        TAGS["CARBO"]["COMPLESSI_SALATI"]["ROOT"],
    ]

    for food in food_data:
        # Apply only to foods that require preparation
        food_requires_prep = any(tag in food.tags for tag in meal_prep_tags)
        if not food_requires_prep:
            continue

        # Jolly foods are excluded (e.g. pre-cooked rice)
        if jolly_tag in food.tags:
            continue

        # Collect all selections for this food
        food_selection_vars = [
            selection_variables[food.id, day, slot]
            for day in active_days
            for slot in SLOTS
        ]

        # Binary variable: "has this food been used?"
        is_food_used = LpVariable(f"MealPrep_IsUsed_{food.id}", cat=LpBinary)

        # If z=0, sum must be 0 (not used)
        # If z=1, sum can be up to max_total
        problem += (
            lpSum(food_selection_vars) <= max_total * is_food_used,
            f"MealPrep_MaxIfUsed_{food.id}"
        )

        # If z=1, sum must be at least min_if_used
        # If z=0, this constraint is automatically satisfied (0 >= 0)
        problem += (
            lpSum(food_selection_vars) >= min_if_used * is_food_used,
            f"MealPrep_MinIfUsed_{food.id}"
        )
