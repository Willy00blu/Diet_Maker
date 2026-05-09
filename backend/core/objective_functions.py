"""
Objective Functions for Optimization.

This module defines the objective functions that the solver can optimize.
In a linear programming problem, the objective function is the measure
we want to minimize or maximize.

Available objective functions:
- Minimize cost: finds the cheapest possible diet
- Maximize preferences: favors foods preferred by the user

Note: PuLP always minimizes. To maximize, we use the mathematical trick
of minimizing the negative (-value).
"""

from typing import List, Dict, Optional
from pulp import LpProblem, lpSum

from backend.core.definitions import FoodItem, DAYS_NAMES, SLOTS
from backend.config.food import FOODS_CONFIG
from backend.config.nutrition import N_DAYS


# =============================================================================
# OBJECTIVE 1: MINIMIZE TOTAL DIET COST
# =============================================================================

def set_objective_minimize_cost(
    problem: LpProblem,
    quantity_variables: Dict,
    food_data: List[FoodItem],
    number_of_days: Optional[int] = None
) -> None:
    """
    Sets the objective function to minimize total diet cost.

    Calculates total cost as the sum of costs for each food portion:
        total_cost = sum( price_per_100g / 100 * quantity_grams )

    Useful when budget is a priority and the cheapest diet that satisfies
    all nutritional constraints is desired.

    Args:
        problem: The PuLP optimization problem
        quantity_variables: Continuous quantity variables in grams
            Format: {(food_id, day, slot): LpVariable}
        food_data: List of available food items, each FoodItem must have
            the `price` attribute (price per 100g in euros)
        number_of_days: Number of days to consider.
            If None, uses N_DAYS from configuration.

    Example:
        >>> set_objective_minimize_cost(problem, quantity_vars, foods)
        # The solver will find the food combination that minimizes
        # total cost while respecting all constraints
    """
    active_days = DAYS_NAMES[:number_of_days] if number_of_days else DAYS_NAMES[:N_DAYS]

    # Calculate the cost of each possible food portion
    food_costs = []

    for day in active_days:
        for slot in SLOTS:
            for food in food_data:
                # Cost = (price per 100g) * (grams / 100) = (price/100) * grams
                portion_cost = (food.price / 100) * quantity_variables[food.id, day, slot]
                food_costs.append(portion_cost)

    # Set the objective function: minimize the sum of costs
    problem += lpSum(food_costs), "Objective_Minimize_Diet_Cost"


# =============================================================================
# OBJECTIVE 2: MAXIMIZE USER PREFERENCES
# =============================================================================

def set_objective_maximize_preference(
    problem: LpProblem,
    selection_variables: Dict,
    food_data: List[FoodItem],
    preferences: Optional[Dict[str, int]] = None,
    number_of_days: Optional[int] = None
) -> None:
    """
    Sets the objective function to maximize use of preferred foods.

    Calculates a total preference score based on how often the user's
    preferred foods are selected in the diet:
        total_preference = sum( food_rating * is_selected )

    Where `is_selected` is a binary variable (0 or 1).

    Foods with higher ratings contribute more to the score,
    so the solver will tend to include them more frequently.

    Technical note: PuLP always minimizes, so to maximize preferences
    we minimize the negative: min(-preferences) = max(preferences)

    Args:
        problem: The PuLP optimization problem
        selection_variables: Binary selection variables (0 or 1)
            Format: {(food_id, day, slot): LpVariable}
        food_data: List of available food items
        preferences: User preferences dictionary from the GUI
            Format: {food_name: rating} where rating is 1-5
            If None, uses default values from FOODS_CONFIG
        number_of_days: Number of days to consider.
            If None, uses N_DAYS from configuration.

    Example:
        >>> user_prefs = {"Chicken Breast": 5, "Salmon": 4, "Broccoli": 3}
        >>> set_objective_maximize_preference(problem, selection_vars, foods, user_prefs)
        # The solver will favor Chicken Breast (rating 5) over Salmon (rating 4)
    """
    active_days = DAYS_NAMES[:number_of_days] if number_of_days else DAYS_NAMES[:N_DAYS]

    # Calculate the preference contribution of each possible selection
    preference_contributions = []

    for day in active_days:
        for slot in SLOTS:
            for food in food_data:
                # Determine the preference rating for this food
                preference_rating = _get_food_preference_rating(food, preferences)

                # If the food has a positive preference, add it to the objective
                if preference_rating > 0:
                    # Contribution = rating * (1 if selected, 0 otherwise)
                    contribution = preference_rating * selection_variables[food.id, day, slot]
                    preference_contributions.append(contribution)

    # Set the objective function: minimize the negative of preferences
    # This is equivalent to maximizing preferences
    problem += -lpSum(preference_contributions), "Objective_Maximize_User_Preference"


def _get_food_preference_rating(
    food: FoodItem,
    preferences: Optional[Dict[str, int]]
) -> int:
    """
    Determines the preference rating for a food item.

    Looks first in GUI-provided preferences, then in default
    values from FOODS_CONFIG.

    Args:
        food: The food item to determine the preference for
        preferences: Preferences dictionary from the GUI (may be None)

    Returns:
        Preference rating (0-5), where:
        - 0 = no preference / neutral
        - 1-2 = low preference
        - 3 = medium preference
        - 4-5 = high preference
    """
    # First priority: preferences from the GUI
    if preferences is not None:
        return preferences.get(food.name, 0)

    # Second priority: default values from FOODS_CONFIG
    food_id_string = str(food.id)
    food_config = FOODS_CONFIG.get(food_id_string, {})
    return food_config.get("preference", 0)
