"""
Validators for the Diet Generation Pipeline.

Validates input data from the GUI before passing it to the backend.
"""

from typing import List, Tuple

from pipeline.contracts import DietRequest, NutritionTargets
from backend.config.constants import (
    MIN_DIET_DAYS as DAYS_MIN,
    MAX_DIET_DAYS as DAYS_MAX,
    MIN_DAILY_KCAL as KCAL_MIN,
    MAX_DAILY_KCAL as KCAL_MAX,
    MIN_PROTEIN_PERCENTAGE as PROTEIN_PCT_MIN,
    MAX_PROTEIN_PERCENTAGE as PROTEIN_PCT_MAX,
    MIN_CARBOHYDRATE_PERCENTAGE as CARB_PCT_MIN,
    MAX_CARBOHYDRATE_PERCENTAGE as CARB_PCT_MAX,
    MIN_FAT_PERCENTAGE as FAT_PCT_MIN,
    MAX_FAT_PERCENTAGE as FAT_PCT_MAX,
    MIN_ENABLED_FOODS,
    MIN_FOOD_RATING as RATING_MIN,
    MAX_FOOD_RATING as RATING_MAX,
)


# =============================================================================
# VALIDATION CONSTANTS
# =============================================================================

MACRO_TOTAL_REQUIRED = 100

VALID_OBJECTIVES = ["cost", "preference", "none"]


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ValidationError(Exception):
    """Raised when input data from the GUI fails validation."""
    pass


# =============================================================================
# SPECIFIC VALIDATORS
# =============================================================================

def validate_nutrition_targets(targets: NutritionTargets) -> List[str]:
    """
    Validates the nutrition targets configured by the user.

    Returns:
        List of error messages (empty if all valid)
    """
    errors = []

    if targets.n_days < DAYS_MIN or targets.n_days > DAYS_MAX:
        errors.append(
            f"Number of days must be between {DAYS_MIN} and {DAYS_MAX} "
            f"(received: {targets.n_days})"
        )

    if targets.kcal < KCAL_MIN or targets.kcal > KCAL_MAX:
        errors.append(
            f"Calories must be between {KCAL_MIN} and {KCAL_MAX} "
            f"(received: {targets.kcal})"
        )

    macro_total = targets.prot_pct + targets.carb_pct + targets.fat_pct
    if macro_total != MACRO_TOTAL_REQUIRED:
        errors.append(
            f"Macro percentages must sum to {MACRO_TOTAL_REQUIRED} "
            f"(received: {macro_total})"
        )

    if targets.prot_pct < PROTEIN_PCT_MIN or targets.prot_pct > PROTEIN_PCT_MAX:
        errors.append(
            f"Protein must be between {PROTEIN_PCT_MIN}% and {PROTEIN_PCT_MAX}% "
            f"(received: {targets.prot_pct}%)"
        )

    if targets.carb_pct < CARB_PCT_MIN or targets.carb_pct > CARB_PCT_MAX:
        errors.append(
            f"Carbohydrates must be between {CARB_PCT_MIN}% and {CARB_PCT_MAX}% "
            f"(received: {targets.carb_pct}%)"
        )

    if targets.fat_pct < FAT_PCT_MIN or targets.fat_pct > FAT_PCT_MAX:
        errors.append(
            f"Fat must be between {FAT_PCT_MIN}% and {FAT_PCT_MAX}% "
            f"(received: {targets.fat_pct}%)"
        )

    return errors


def validate_food_selections(request: DietRequest) -> List[str]:
    """
    Validates food selections from the GUI.

    Checks that:
    - Enough foods are enabled
    - Portion min/max are consistent
    - Ratings are in the valid range

    Returns:
        List of error messages (empty if all valid)
    """
    errors = []

    enabled_count = sum(1 for food in request.food_selections if food.enabled)

    if enabled_count < MIN_ENABLED_FOODS:
        errors.append(
            f"Enable at least {MIN_ENABLED_FOODS} foods "
            f"(currently enabled: {enabled_count})"
        )

    for food in request.food_selections:
        if not food.enabled:
            continue

        if food.portion_min > food.portion_max:
            errors.append(
                f"'{food.name}': minimum portion ({food.portion_min}g) "
                f"exceeds maximum ({food.portion_max}g)"
            )

        if food.rating < RATING_MIN or food.rating > RATING_MAX:
            errors.append(
                f"'{food.name}': rating must be between {RATING_MIN} and {RATING_MAX} "
                f"(received: {food.rating})"
            )

    return errors


def validate_objective(objective: str) -> List[str]:
    """
    Validates the optimization objective.

    Returns:
        List of error messages (empty if valid)
    """
    if objective not in VALID_OBJECTIVES:
        return [
            f"Invalid objective: '{objective}'. "
            f"Accepted values: {VALID_OBJECTIVES}"
        ]
    return []


# =============================================================================
# MAIN VALIDATOR
# =============================================================================

def validate_request(request: DietRequest) -> Tuple[bool, List[str]]:
    """
    Validates the full diet generation request.

    Returns:
        Tuple (is_valid, errors)
    """
    all_errors = []
    all_errors.extend(validate_nutrition_targets(request.nutrition_targets))
    all_errors.extend(validate_food_selections(request))
    all_errors.extend(validate_objective(request.objective))

    is_valid = len(all_errors) == 0
    return is_valid, all_errors
