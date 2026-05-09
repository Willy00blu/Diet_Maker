"""
Sport Nutrition Axioms (Chrono-Nutrition).

This module defines constraints that control the TEMPORAL DISTRIBUTION
of macronutrients throughout the day, based on chrono-nutrition principles.

Chrono-nutrition is a nutritional approach that considers not only WHAT
you eat, but also WHEN you eat, optimizing nutrient intake according to
circadian rhythms and metabolic needs.

Axioms include:
- Chrono-Carbohydrates: more carbs at lunch (energy), fewer at dinner
- Chrono-Protein: consistent protein distribution across main meals
- Chrono-Fat: balanced fat intake, with a morning minimum for satiety
"""

from typing import List, Dict, Any, Optional, Tuple
from pulp import LpProblem, lpSum

from backend.config import TARGET_KCAL, TARGET_PROT, TARGET_CARB, TARGET_FAT
from backend.config.axioms import SPORT_NUTRITION_AXIOMS
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


def _is_slot_disabled(slot_key: str, axioms_config: Optional[Dict]) -> bool:
    """
    Returns True if the meal_validity axiom for this slot is disabled.

    Chrono-nutrition constraints that target a specific slot must be skipped
    when that slot is disabled and forced empty by meal_validity.

    Args:
        slot_key: Lowercase slot name ("breakfast", "lunch", "snack", "dinner")
        axioms_config: Full axiom configuration from the GUI
    """
    if not axioms_config:
        return False
    return not axioms_config.get("meal_validity", {}).get(slot_key, {}).get("enabled", True)


def _calculate_slot_macronutrient_total(
    quantity_variables: Dict,
    day: str,
    slot: str,
    food_data: List[FoodItem],
    macro_attribute: str
) -> Any:
    """
    Calculates the total of a macronutrient for a single meal slot.

    Creates a linear expression summing each food's contribution to
    the specified macronutrient.

    Formula: sum( value_per_100g / 100 * quantity_grams )

    Args:
        quantity_variables: Dictionary {(food_id, day, slot): LpVariable}
        day: Day name
        slot: Meal slot name (Breakfast, Lunch, Snack, Dinner)
        food_data: List of food items
        macro_attribute: Macronutrient attribute name
            - "carb_100g" for carbohydrates
            - "prot_100g" for protein
            - "fat_100g" for fat

    Returns:
        LpAffineExpression with the macronutrient total
    """
    food_quantity_pairs = [
        (food, quantity_variables[food.id, day, slot])
        for food in food_data
    ]

    return lpSum([
        (getattr(food, macro_attribute) / 100) * quantity_var
        for food, quantity_var in food_quantity_pairs
    ])


def _get_macronutrient_targets(
    nutrition_targets: Optional[Dict]
) -> Dict[str, float]:
    """
    Calculates macronutrient gram targets from configuration.

    Converts caloric percentages to grams using conversion factors:
    - Protein: 4 kcal/g
    - Carbohydrates: 4 kcal/g
    - Fat: 9 kcal/g

    Args:
        nutrition_targets: Dict from the GUI with kcal and percentages,
            may be None to use defaults

    Returns:
        Dictionary {"prot": grams, "carb": grams, "fat": grams}
    """
    if nutrition_targets:
        target_kcal = nutrition_targets.get("kcal", TARGET_KCAL)

        # Convert percentages to fractions (e.g. 20 -> 0.20)
        protein_percentage = nutrition_targets.get("prot_pct", 20) / 100
        carb_percentage = nutrition_targets.get("carb_pct", 55) / 100
        fat_percentage = nutrition_targets.get("fat_pct", 25) / 100

        # Calculate grams: (total_kcal * percentage) / kcal_per_gram
        target_protein_grams = (target_kcal * protein_percentage) / KCAL_PER_GRAM_PROTEIN
        target_carb_grams = (target_kcal * carb_percentage) / KCAL_PER_GRAM_CARBOHYDRATE
        target_fat_grams = (target_kcal * fat_percentage) / KCAL_PER_GRAM_FAT

        return {
            "prot": target_protein_grams,
            "carb": target_carb_grams,
            "fat": target_fat_grams
        }

    # Default values from configuration
    return {
        "prot": TARGET_PROT,
        "carb": TARGET_CARB,
        "fat": TARGET_FAT
    }


# =============================================================================
# AXIOM 1: CHRONO-CARBOHYDRATES
# =============================================================================

def apply_chrono_carb_axiom(
    problem: LpProblem,
    quantity_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    nutrition_targets: Optional[Dict] = None,
    axioms_config: Optional[Dict] = None
) -> None:
    """
    Applies chrono-nutrition constraints for carbohydrates.

    Principle: Carbohydrates provide quick energy. It is preferable to
    consume them during the day (lunch) when metabolic activity is higher,
    and reduce them in the evening (dinner) when the body prepares for rest.

    Constraints applied:
    - Lunch: at least a certain percentage of the daily carbohydrate target
    - Dinner: at most a certain percentage of the daily target

    The "delta" parameter adds flexibility to constraints (elastic margin).

    Args:
        problem: The PuLP optimization problem
        quantity_variables: Quantity variables {(food_id, day, slot): var}
        day: Day name
        food_data: List of food items
        nutrition_targets: Nutritional targets from the GUI
        axioms_config: Axioms configuration from the GUI
    """
    config = _get_axiom_config(
        axioms_config,
        "sport_nutrition",
        "chrono_carb",
        SPORT_NUTRITION_AXIOMS["chrono_carb"]
    )

    if not config["enabled"]:
        return

    macro_targets = _get_macronutrient_targets(nutrition_targets)
    target_carb_grams = macro_targets["carb"]

    params = config["params"]
    flexibility_delta = params["delta"]

    # --- LUNCH CONSTRAINT: at least X% of daily carbohydrates ---
    # Ensures sufficient energy for afternoon activities.
    # Skipped when lunch is disabled (slot is forced empty).
    if not _is_slot_disabled("lunch", axioms_config):
        carbs_at_lunch = _calculate_slot_macronutrient_total(
            quantity_variables, day, "Lunch", food_data, "carb_100g"
        )

        lunch_min_percentage = params["lunch_min_pct"] - flexibility_delta
        lunch_min_carbs = target_carb_grams * lunch_min_percentage

        problem += (
            carbs_at_lunch >= lunch_min_carbs,
            f"ChronoCarb_Lunch_Min_{day}"
        )

    # --- DINNER CONSTRAINT: at most Y% of daily carbohydrates ---
    # Avoids excess energy intake before sleep
    carbs_at_dinner = _calculate_slot_macronutrient_total(
        quantity_variables, day, "Dinner", food_data, "carb_100g"
    )

    dinner_max_percentage = params["dinner_max_pct"] + flexibility_delta
    dinner_max_carbs = target_carb_grams * dinner_max_percentage

    problem += (
        carbs_at_dinner <= dinner_max_carbs,
        f"ChronoCarb_Dinner_Max_{day}"
    )


# =============================================================================
# AXIOM 2: CHRONO-PROTEIN
# =============================================================================

def apply_chrono_protein_axiom(
    problem: LpProblem,
    quantity_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    nutrition_targets: Optional[Dict] = None,
    axioms_config: Optional[Dict] = None
) -> None:
    """
    Applies chrono-nutrition constraints for protein.

    Principle: Protein is essential for muscle synthesis and lean mass
    maintenance. To optimize the anabolic effect, it is important to
    distribute it evenly throughout the day, ensuring a consistent
    intake at each main meal.

    Constraints applied:
    - Breakfast, Lunch, Dinner: at least X% of the daily protein target per meal

    Snack is excluded as it is typically not a primary protein meal.

    Args:
        problem: The PuLP optimization problem
        quantity_variables: Quantity variables
        day: Day name
        food_data: List of food items
        nutrition_targets: Nutritional targets from the GUI
        axioms_config: Axioms configuration from the GUI
    """
    config = _get_axiom_config(
        axioms_config,
        "sport_nutrition",
        "chrono_protein",
        SPORT_NUTRITION_AXIOMS["chrono_protein"]
    )

    if not config["enabled"]:
        return

    macro_targets = _get_macronutrient_targets(nutrition_targets)
    target_protein_grams = macro_targets["prot"]

    params = config["params"]
    flexibility_delta = params["delta"]

    # Only require protein at meal slots that are actually active
    main_meals = [
        slot for slot in ["Breakfast", "Lunch", "Dinner"]
        if not _is_slot_disabled(slot.lower(), axioms_config)
    ]

    min_percentage = params["min_pct_per_meal"] - flexibility_delta
    min_protein_per_meal = target_protein_grams * min_percentage

    for meal_slot in main_meals:
        protein_at_meal = _calculate_slot_macronutrient_total(
            quantity_variables, day, meal_slot, food_data, "prot_100g"
        )

        problem += (
            protein_at_meal >= min_protein_per_meal,
            f"ChronoProtein_{meal_slot}_Min_{day}"
        )


# =============================================================================
# AXIOM 3: CHRONO-FAT
# =============================================================================

def apply_chrono_fat_axiom(
    problem: LpProblem,
    quantity_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    nutrition_targets: Optional[Dict] = None,
    axioms_config: Optional[Dict] = None
) -> None:
    """
    Applies chrono-nutrition constraints for fat.

    Principle: Fat is digested slowly and provides prolonged satiety.
    It is useful to guarantee a minimum at breakfast to prevent morning
    hunger, while limiting excess at any single meal to avoid slowing
    digestion too much.

    Constraints applied:
    - Breakfast: at least X% of the daily fat target (morning satiety)
    - All meals: at most Y% of the daily fat target (avoids heavy meals)

    Args:
        problem: The PuLP optimization problem
        quantity_variables: Quantity variables
        day: Day name
        food_data: List of food items
        nutrition_targets: Nutritional targets from the GUI
        axioms_config: Axioms configuration from the GUI
    """
    config = _get_axiom_config(
        axioms_config,
        "sport_nutrition",
        "chrono_fat",
        SPORT_NUTRITION_AXIOMS["chrono_fat"]
    )

    if not config["enabled"]:
        return

    macro_targets = _get_macronutrient_targets(nutrition_targets)
    target_fat_grams = macro_targets["fat"]

    params = config["params"]
    flexibility_delta = params["delta"]

    # --- BREAKFAST CONSTRAINT: at least X% of daily fat ---
    # Ensures satiety and glycemic stability throughout the morning.
    # Skipped when breakfast is disabled (slot is forced empty).
    if not _is_slot_disabled("breakfast", axioms_config):
        fat_at_breakfast = _calculate_slot_macronutrient_total(
            quantity_variables, day, "Breakfast", food_data, "fat_100g"
        )

        breakfast_min_percentage = params["breakfast_min_pct"] - flexibility_delta
        breakfast_min_fat = target_fat_grams * breakfast_min_percentage

        problem += (
            fat_at_breakfast >= breakfast_min_fat,
            f"ChronoFat_Breakfast_Min_{day}"
        )

    # --- ALL MEALS CONSTRAINT: at most Y% of daily fat ---
    # Prevents any single meal from being too heavy and slow to digest
    max_percentage = params["max_pct_per_meal"] + flexibility_delta
    max_fat_per_meal = target_fat_grams * max_percentage

    for meal_slot in SLOTS:
        fat_at_meal = _calculate_slot_macronutrient_total(
            quantity_variables, day, meal_slot, food_data, "fat_100g"
        )

        problem += (
            fat_at_meal <= max_fat_per_meal,
            f"ChronoFat_{meal_slot}_Max_{day}"
        )


# =============================================================================
# AGGREGATE FUNCTION
# =============================================================================

def apply_sport_nutrition_axioms(
    problem: LpProblem,
    quantity_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    nutrition_targets: Optional[Dict] = None,
    axioms_config: Optional[Dict] = None
) -> None:
    """
    Applies all sport nutrition axioms for a given day.

    This is an aggregator function that sequentially applies all
    chrono-nutrition constraints as an alternative to calling
    individual functions separately.

    Args:
        problem: The PuLP optimization problem
        quantity_variables: Quantity variables {(food_id, day, slot): var}
        day: Day name
        food_data: List of food items
        nutrition_targets: Nutritional targets from the GUI
        axioms_config: Axioms configuration from the GUI
    """
    apply_chrono_carb_axiom(
        problem, quantity_variables, day, food_data,
        nutrition_targets, axioms_config
    )

    apply_chrono_protein_axiom(
        problem, quantity_variables, day, food_data,
        nutrition_targets, axioms_config
    )

    apply_chrono_fat_axiom(
        problem, quantity_variables, day, food_data,
        nutrition_targets, axioms_config
    )
