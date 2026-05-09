"""
Results Component - Diet Plan and Shopping List Display.

Renders the output of a successful diet generation:
- Daily meal plan with foods and quantities per meal
- Estimated total cost
- Shopping list grouped by category
"""

import streamlit as st
from typing import Dict, List, Tuple, Optional

from backend.core.definitions import FoodItem
from lista_della_spesa import generate_shopping_list


# =============================================================================
# TYPES
# =============================================================================

DietPlan = Dict[str, Dict[str, List[Tuple[str, int]]]]


# =============================================================================
# CONSTANTS
# =============================================================================

SHOPPING_LIST_COLUMNS = 3


# =============================================================================
# DISPLAY COMPONENTS
# =============================================================================

def _format_meal_foods(foods: List[Tuple[str, int]]) -> str:
    """
    Formats a list of meal foods into a readable string.

    Returns "Food1 (100g), Food2 (150g)" or "—" if empty.
    """
    if not foods:
        return "—"
    return ", ".join(
        f"{food_name} ({quantity_grams}g)"
        for food_name, quantity_grams in foods
    )


def render_diet_plan(diet_plan: DietPlan, total_cost: float) -> None:
    """
    Renders the generated meal plan.

    Each day is shown as an expander with the foods per meal slot.

    Args:
        diet_plan: Structured plan {day: {meal: [(name, grams), ...]}}
        total_cost: Estimated total cost in euros
    """
    st.header("Generated Meal Plan")

    for day_name, meals in diet_plan.items():
        with st.expander(f"{day_name}", expanded=True):
            for meal_name, meal_foods in meals.items():
                formatted_foods = _format_meal_foods(meal_foods)
                st.write(f"**{meal_name}**: {formatted_foods}")

    st.success(f"Estimated total cost: {total_cost:.2f} EUR")


def render_shopping_list(diet_plan: DietPlan, food_data: List[FoodItem]) -> None:
    """
    Renders the shopping list grouped by category.

    Args:
        diet_plan: Diet plan to aggregate foods from
        food_data: Full food list (needed for category mapping)
    """
    st.header("Shopping List")

    shopping_list_by_category = generate_shopping_list(diet_plan, food_data)

    columns = st.columns(SHOPPING_LIST_COLUMNS)
    sorted_categories = sorted(shopping_list_by_category.keys())

    for category_index, category_name in enumerate(sorted_categories):
        column_index = category_index % SHOPPING_LIST_COLUMNS

        with columns[column_index]:
            st.subheader(category_name)

            category_foods = shopping_list_by_category[category_name]

            for food_name in sorted(category_foods.keys()):
                quantity_grams = round(category_foods[food_name])
                st.write(f"• {food_name}: **{quantity_grams}g**")


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def render_results(food_data: List[FoodItem]) -> None:
    """
    Renders the results section if a diet has been generated.

    Args:
        food_data: Available foods (needed for the shopping list)
    """
    diet_result = st.session_state.get("diet_result")

    if diet_result is None:
        return

    diet_plan, total_cost = diet_result

    render_diet_plan(diet_plan, total_cost)
    render_shopping_list(diet_plan, food_data)
