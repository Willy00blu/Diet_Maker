"""
Communication Contracts between Frontend and Backend.

This module defines the dataclasses that act as "contracts" for
communication between the GUI (frontend) and the solver (backend).

Using explicit contracts allows:
- Defining a clear, typed interface between modules
- Changing the backend implementation without modifying the frontend
- Centralizing input data validation
- Documenting the structure of exchanged data

Main contracts:
- DietRequest: data from the GUI to the backend to generate a diet
- DietResponse: result from the backend to the GUI
- NutritionTargets: nutritional targets configured by the user
- FoodSelection: preferences and configuration for a single food item
- AxiomConfig: configuration for a single axiom
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any


# =============================================================================
# NUTRITIONAL CONFIGURATION CONTRACTS
# =============================================================================

@dataclass
class NutritionTargets:
    """
    Nutritional targets configured by the user.

    Represents the caloric goals and macronutrient distribution
    that the generated diet must satisfy, with associated tolerances.

    Attributes:
        n_days: Number of days to plan (1-7)
        kcal: Daily calorie target
        prot_pct: Percentage of calories from protein (e.g. 20 = 20%)
        carb_pct: Percentage of calories from carbohydrates
        fat_pct: Percentage of calories from fat
        delta_kcal: Calorie tolerance as percentage (e.g. 10 = ±10%)
        delta_macro: Macronutrient tolerance as percentage (e.g. 50 = ±50%)

    Note:
        The sum of prot_pct + carb_pct + fat_pct must equal 100.
    """
    n_days: int = 5
    kcal: int = 2200
    prot_pct: int = 20
    carb_pct: int = 55
    fat_pct: int = 25
    delta_kcal: int = 10
    delta_macro: int = 50

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the object to a dictionary for backend compatibility.

        The backend accepts nutritional targets as a dictionary;
        this method facilitates the conversion.

        Returns:
            Dictionary with the same keys and values as the object
        """
        return {
            "n_days": self.n_days,
            "kcal": self.kcal,
            "prot_pct": self.prot_pct,
            "carb_pct": self.carb_pct,
            "fat_pct": self.fat_pct,
            "delta_kcal": self.delta_kcal / 100,  # Convert to decimal
            "delta_macro": self.delta_macro / 100,  # Convert to decimal
        }


# =============================================================================
# AXIOM CONFIGURATION CONTRACTS
# =============================================================================

@dataclass
class AxiomConfig:
    """
    Configuration for a single axiom (constraint).

    Each axiom can be enabled/disabled and can have specific
    parameters that modify its behavior.

    Attributes:
        enabled: True if the axiom is active, False if disabled
        params: Dictionary of axiom-specific parameters
                (e.g. {"min": 2, "max": 4} for frequency limits)
    """
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# FOOD SELECTION CONTRACTS
# =============================================================================

@dataclass
class FoodSelection:
    """
    Selection and preferences for a single food item.

    Represents the user's choices regarding a food item:
    whether to include it, how much to prefer it, and what portion sizes to accept.

    Attributes:
        food_id: Unique food item ID in the database
        name: Food item name (for reference)
        enabled: True if the food can be used in the diet
        rating: User preference (1=low, 5=high)
        portion_min: Minimum acceptable portion in grams
        portion_max: Maximum acceptable portion in grams
    """
    food_id: int
    name: str
    enabled: bool = True
    rating: int = 3
    portion_min: float = 0.0
    portion_max: float = 0.0


# =============================================================================
# REQUEST CONTRACT (GUI -> BACKEND)
# =============================================================================

@dataclass
class DietRequest:
    """
    Diet generation request from the GUI.

    Contains all parameters needed to generate a diet plan,
    in a format agnostic to the backend implementation.
    This allows changing the backend without modifying the GUI.

    Attributes:
        food_selections: List of user selections for each food item
        preferences: Dictionary {food_name: rating} for quick access
        nutrition_targets: Caloric and macronutrient targets
        objective: Optimization strategy ("cost", "preference", "none")
        axioms_config: Configuration for all active axioms
    """
    food_selections: List[FoodSelection] = field(default_factory=list)
    preferences: Dict[str, int] = field(default_factory=dict)
    nutrition_targets: NutritionTargets = field(default_factory=NutritionTargets)
    objective: str = "none"
    axioms_config: Dict[str, Dict[str, AxiomConfig]] = field(default_factory=dict)

    def get_axioms_dict(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Converts axioms_config to a dictionary for backend compatibility.

        The backend expects axiom configuration as a nested dictionary,
        not as AxiomConfig objects.

        Returns:
            Structured dictionary: {group: {axiom: {enabled, params}}}
        """
        result = {}

        for group_key, group_axioms in self.axioms_config.items():
            result[group_key] = {}

            for axiom_key, axiom_config in group_axioms.items():
                result[group_key][axiom_key] = {
                    "enabled": axiom_config.enabled,
                    "params": axiom_config.params,
                }

        return result


# =============================================================================
# PLAN STRUCTURE CONTRACTS (used internally)
# =============================================================================

@dataclass
class MealPlan:
    """
    Plan for a single meal.

    Attributes:
        slot: Meal name (Breakfast, Lunch, Snack, Dinner)
        items: List of tuples (food_name, quantity_grams)
    """
    slot: str
    items: List[Tuple[str, int]] = field(default_factory=list)


@dataclass
class DayPlan:
    """
    Plan for a single day.

    Attributes:
        day: Day name (Monday, Tuesday, etc.)
        meals: Dictionary {slot: [(name, grams), ...]}
    """
    day: str
    meals: Dict[str, List[Tuple[str, int]]] = field(default_factory=dict)


# =============================================================================
# RESPONSE CONTRACT (BACKEND -> GUI)
# =============================================================================

@dataclass
class DietResponse:
    """
    Backend response containing the generated diet plan.

    Contains the optimization result in a format easily
    consumable by the GUI, along with any error information or statistics.

    Attributes:
        success: True if a solution was found
        plan: Structured diet plan {day: {slot: [(name, grams), ...]}}
        total_cost: Estimated total diet cost in euros
        error_message: Error message if success=False
        stats: Additional statistics (optional, for debug/analysis)

    Example:
        >>> response = DietResponse(
        ...     success=True,
        ...     plan={"Monday": {"Breakfast": [("Yogurt", 150), ("Muesli", 50)]}},
        ...     total_cost=45.50
        ... )
    """
    success: bool = False
    plan: Dict[str, Dict[str, List[Tuple[str, int]]]] = field(default_factory=dict)
    total_cost: float = 0.0
    error_message: Optional[str] = None
    stats: Dict[str, Any] = field(default_factory=dict)
