"""
Main diet optimization module.

This module contains the solver that generates optimized meal plans
using Mixed Integer Linear Programming (MILP) via PuLP.

The solver considers:
- Nutritional constraints (calories, macronutrients)
- Meal composition constraints (meal structure)
- Frequency constraints (daily and weekly)
- Chrono-nutrition constraints (nutrient timing)
"""

from typing import List, Dict, Tuple, Optional, Any
from pulp import (
    LpProblem,
    LpMinimize,
    LpVariable,
    LpBinary,
    LpContinuous,
    lpSum,
    value,
    PULP_CBC_CMD
)

from backend.core.definitions import FoodItem, DAYS_NAMES, SLOTS
from backend.config.nutrition import N_DAYS
from backend.config.objectives import SOLVER_CONFIG
from backend.core.axioms.meal_validity import apply_meal_validity_axioms
from backend.core.axioms.daily_frequency import apply_daily_frequency_axioms
from backend.core.axioms.diet_frequency import apply_diet_frequency_axioms
from backend.core.axioms.nutrition import apply_nutrition_axioms
from backend.core.axioms.nutrizione_sportiva import (
    apply_chrono_carb_axiom,
    apply_chrono_protein_axiom,
    apply_chrono_fat_axiom
)
from backend.core.objective_functions import (
    set_objective_minimize_cost,
    set_objective_maximize_preference
)


# =============================================================================
# SOLVER CONSTANTS
# =============================================================================

# PuLP status codes
SOLVER_STATUS_OPTIMAL = 1
SOLVER_STATUS_NOT_SOLVED = 0
SOLVER_STATUS_INFEASIBLE = -1
SOLVER_STATUS_UNBOUNDED = -2
SOLVER_STATUS_UNDEFINED = -3


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def generate_diet_plan(
    food_data: List[FoodItem],
    objective: str = "none",
    preferences: Optional[Dict[str, int]] = None,
    nutrition_targets: Optional[Dict[str, Any]] = None,
    axioms_config: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[Dict], Optional[float]]:
    """
    Generates an optimized diet plan using linear programming.

    This function is the core of the system: it takes a list of food items
    and generates a meal plan that respects all configured constraints,
    optimizing according to the chosen objective.

    Args:
        food_data: List of FoodItem objects available for the diet.
            Each FoodItem contains: id, name, nutritional values, min/max portions, price.

        objective: Optimization strategy to use:
            - "cost": Minimize the total diet cost
            - "preference": Maximize use of foods preferred by the user
            - "none": Find any valid solution (faster)

        preferences: User preferences dictionary.
            Format: {food_name: rating} where rating is 1-5.
            If None, uses default values from FOODS_CONFIG.

        nutrition_targets: Custom nutritional targets from the GUI.
            Format: {
                "n_days": int,      # Number of days (1-7)
                "kcal": int,        # Daily calorie target
                "prot_pct": int,    # Protein percentage (e.g. 20)
                "carb_pct": int,    # Carbohydrate percentage (e.g. 55)
                "fat_pct": int      # Fat percentage (e.g. 25)
            }
            If None, uses default values from nutrition.py.

        axioms_config: Axioms (constraints) configuration from the GUI.
            Format: {
                "group_name": {
                    "axiom_name": {
                        "enabled": bool,
                        "params": {...}
                    }
                }
            }
            If None, uses default values from axioms.py.

    Returns:
        Tuple[Optional[Dict], Optional[float]]:
            - If solution found: (diet_plan, total_cost)
              where diet_plan = {day: {slot: [(food_name, grams), ...]}}
            - If no solution: (None, None)

    Example:
        >>> foods = load_food_database("data/food_db.csv")
        >>> plan, cost = generate_diet_plan(foods, objective="cost")
        >>> if plan:
        ...     print(f"Diet generated! Cost: €{cost:.2f}")
    """
    # Determine the number of days to plan
    number_of_days = _get_number_of_days(nutrition_targets)
    print(f"Searching for a valid combination over {number_of_days} days...")

    # Create the optimization problem
    optimization_problem = LpProblem("Diet_Optimization_System", LpMinimize)

    # Prepare days and variable indices
    active_days = DAYS_NAMES[:number_of_days]
    variable_indices = _create_variable_indices(food_data, active_days)

    # Create decision variables
    is_food_selected = _create_selection_variables(variable_indices)
    food_quantity_grams = _create_quantity_variables(variable_indices)

    # Apply semi-continuity constraints (linking selection to quantity)
    _apply_semicontinuity_constraints(
        optimization_problem,
        is_food_selected,
        food_quantity_grams,
        food_data,
        variable_indices
    )

    # Apply diet frequency axioms (weekly constraints)
    apply_diet_frequency_axioms(
        optimization_problem,
        is_food_selected,
        food_data,
        active_days,
        axioms_config
    )

    # Apply daily axioms for each day
    for day in active_days:
        _apply_daily_axioms(
            optimization_problem,
            is_food_selected,
            food_quantity_grams,
            day,
            food_data,
            nutrition_targets,
            axioms_config
        )

    # Set the optimization objective
    _set_optimization_objective(
        optimization_problem,
        is_food_selected,
        food_quantity_grams,
        food_data,
        objective,
        preferences,
        number_of_days
    )

    # Solve the problem
    solver_status = _solve_problem(optimization_problem)

    # Process and return the result
    if solver_status == SOLVER_STATUS_OPTIMAL:
        print("Solution found!")
        return _format_solution(
            is_food_selected,
            food_quantity_grams,
            food_data,
            number_of_days
        )
    else:
        print("No solution found within the timeout.")
        return None, None


# =============================================================================
# PRIVATE HELPER FUNCTIONS
# =============================================================================

def _get_number_of_days(nutrition_targets: Optional[Dict]) -> int:
    """
    Extracts the number of days from the configuration.

    Args:
        nutrition_targets: Dictionary with nutritional targets, may contain "n_days"

    Returns:
        Number of days to plan (default: N_DAYS from config)
    """
    if nutrition_targets and "n_days" in nutrition_targets:
        return nutrition_targets["n_days"]
    return N_DAYS


def _create_variable_indices(
    food_data: List[FoodItem],
    days: List[str]
) -> List[Tuple[int, str, str]]:
    """
    Creates indices for the decision variables.

    Each index is a tuple (food_id, day, slot) that uniquely identifies
    a possible food-meal assignment.

    Args:
        food_data: List of available food items
        days: List of days to plan

    Returns:
        List of (food_id, day_name, slot_name) tuples
    """
    indices = []
    for food in food_data:
        for day in days:
            for slot in SLOTS:
                indices.append((food.id, day, slot))
    return indices


def _create_selection_variables(
    indices: List[Tuple[int, str, str]]
) -> Dict[Tuple[int, str, str], LpVariable]:
    """
    Creates binary selection variables.

    These variables indicate WHETHER a food is selected for a given meal:
    - 1 = the food is present in the meal
    - 0 = the food is not present in the meal

    Args:
        indices: List of (food_id, day, slot) indices

    Returns:
        Dictionary {(food_id, day, slot): binary LpVariable}
    """
    return LpVariable.dicts(
        name="is_selected",
        indices=indices,
        cat=LpBinary
    )


def _create_quantity_variables(
    indices: List[Tuple[int, str, str]]
) -> Dict[Tuple[int, str, str], LpVariable]:
    """
    Creates continuous quantity variables.

    These variables indicate HOW MUCH of a food is present (in grams).
    They are linked to selection variables via semi-continuity constraints.

    Args:
        indices: List of (food_id, day, slot) indices

    Returns:
        Dictionary {(food_id, day, slot): continuous LpVariable >= 0}
    """
    return LpVariable.dicts(
        name="quantity_grams",
        indices=indices,
        lowBound=0,
        cat=LpContinuous
    )


def _apply_semicontinuity_constraints(
    problem: LpProblem,
    is_selected: Dict,
    quantity: Dict,
    food_data: List[FoodItem],
    indices: List[Tuple[int, str, str]]
) -> None:
    """
    Applies semi-continuity constraints linking selection and quantity.

    Semi-continuity ensures:
    - If a food is NOT selected (is_selected=0), quantity is 0
    - If a food IS selected (is_selected=1), quantity is between portion_min and portion_max

    Mathematically:
        is_selected * portion_min <= quantity <= is_selected * portion_max

    Args:
        problem: The PuLP optimization problem
        is_selected: Binary selection variables
        quantity: Continuous quantity variables
        food_data: List of food items with their min/max portions
        indices: List of variable indices
    """
    # Create a dictionary for fast food lookup by ID
    food_lookup_by_id = {food.id: food for food in food_data}

    for food_id, day, slot in indices:
        food = food_lookup_by_id[food_id]

        # Minimum constraint: if selected, at least portion_min grams
        constraint_name_min = f"SemiCont_Min_{food_id}_{day}_{slot}"
        problem += (
            quantity[food_id, day, slot] >= is_selected[food_id, day, slot] * food.portion_min,
            constraint_name_min
        )

        # Maximum constraint: if selected, at most portion_max grams
        constraint_name_max = f"SemiCont_Max_{food_id}_{day}_{slot}"
        problem += (
            quantity[food_id, day, slot] <= is_selected[food_id, day, slot] * food.portion_max,
            constraint_name_max
        )


def _apply_daily_axioms(
    problem: LpProblem,
    is_selected: Dict,
    quantity: Dict,
    day: str,
    food_data: List[FoodItem],
    nutrition_targets: Optional[Dict],
    axioms_config: Optional[Dict]
) -> None:
    """
    Applies all daily axioms (constraints) for a given day.

    Daily axioms include:
    1. Meal validity: correct composition of each meal
    2. Daily frequency: limits on vegetables, fruit, variety
    3. Nutrition: daily calories and macronutrients
    4. Chrono-nutrition: timing of carbohydrates, protein, fat

    Args:
        problem: The optimization problem
        is_selected: Selection variables
        quantity: Quantity variables
        day: Day name (e.g. "Monday")
        food_data: List of food items
        nutrition_targets: Nutritional targets
        axioms_config: Axioms configuration
    """
    # Meal composition axioms (micro-logic)
    apply_meal_validity_axioms(problem, is_selected, day, food_data, axioms_config)

    # Daily frequency axioms (meso-logic)
    apply_daily_frequency_axioms(problem, is_selected, day, food_data, axioms_config)

    # Nutritional axioms
    apply_nutrition_axioms(problem, quantity, day, food_data, nutrition_targets, axioms_config)

    # Chrono-nutrition axioms (sport nutrition)
    apply_chrono_carb_axiom(problem, quantity, day, food_data, nutrition_targets, axioms_config)
    apply_chrono_protein_axiom(problem, quantity, day, food_data, nutrition_targets, axioms_config)
    apply_chrono_fat_axiom(problem, quantity, day, food_data, nutrition_targets, axioms_config)


def _set_optimization_objective(
    problem: LpProblem,
    is_selected: Dict,
    quantity: Dict,
    food_data: List[FoodItem],
    objective: str,
    preferences: Optional[Dict[str, int]],
    number_of_days: int
) -> None:
    """
    Sets the objective function for the optimization problem.

    Args:
        problem: The optimization problem
        is_selected: Selection variables (used for objective="preference")
        quantity: Quantity variables (used for objective="cost")
        food_data: List of food items
        objective: Objective type ("cost", "preference", "none")
        preferences: User preferences dictionary
        number_of_days: Number of active days (must match variable indices)
    """
    if objective == "cost":
        # Minimize the total diet cost
        set_objective_minimize_cost(problem, quantity, food_data, number_of_days)

    elif objective == "preference":
        # Maximize use of preferred foods
        set_objective_maximize_preference(problem, is_selected, food_data, preferences, number_of_days)

    else:  # objective == "none"
        # Find any valid solution (no optimization)
        problem += 0


def _solve_problem(problem: LpProblem) -> int:
    """
    Solves the optimization problem using the CBC solver.

    Args:
        problem: The PuLP problem to solve

    Returns:
        Solver status code:
            1 = Optimal (solution found)
            0 = Not Solved
           -1 = Infeasible (no feasible solution)
           -2 = Unbounded
           -3 = Undefined
    """
    solver = PULP_CBC_CMD(
        msg=SOLVER_CONFIG["msg"],
        timeLimit=SOLVER_CONFIG["timeout"],
        gapRel=SOLVER_CONFIG["gap_rel"]
    )
    problem.solve(solver)
    return problem.status


def _format_solution(
    is_selected: Dict,
    quantity: Dict,
    food_data: List[FoodItem],
    number_of_days: int
) -> Tuple[Dict[str, Dict[str, List[Tuple[str, int]]]], float]:
    """
    Formats the solver solution into a readable structure.

    Extracts values from PuLP variables and organizes them into a
    data structure easily consumable by the GUI.

    Args:
        is_selected: Resolved selection variables
        quantity: Resolved quantity variables
        food_data: List of food items
        number_of_days: Number of days planned

    Returns:
        Tuple containing:
            - diet_plan: {day: {slot: [(food_name, grams), ...]}}
            - total_cost: Total diet cost in euros
    """
    active_days = DAYS_NAMES[:number_of_days]

    # Initialize the plan structure
    diet_plan = {
        day: {slot: [] for slot in SLOTS}
        for day in active_days
    }

    total_cost = 0.0

    # Extract selected foods and their quantities
    for food in food_data:
        for day in active_days:
            for slot in SLOTS:
                # Check if the food was selected for this meal
                # round() is used because PuLP returns floats (e.g. 0.9999999 instead of 1.0)
                is_food_in_meal = value(is_selected[food.id, day, slot])

                if is_food_in_meal is not None and round(is_food_in_meal) == 1:
                    # Extract quantity in grams
                    quantity_grams = value(quantity[food.id, day, slot])
                    quantity_rounded = round(quantity_grams)

                    # Add to plan
                    diet_plan[day][slot].append((food.name, quantity_rounded))

                    # Calculate cost: (price per 100g) * (grams / 100)
                    food_cost = (food.price / 100) * quantity_grams
                    total_cost += food_cost

    return diet_plan, total_cost
