"""
Streamlit Application Entry Point - Axioma Diet Solver.

Main entry point for the GUI application.
Coordinates all interface components and manages the diet generation
flow through the backend pipeline.

Responsibilities:
- Streamlit page configuration
- Diet service initialization and session state management
- UI component orchestration (sidebar, food matrix, results)
- Diet generation request handling
"""

import streamlit as st
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline import DietService, DietRequest, NutritionTargets, AxiomConfig
from pipeline.contracts import FoodSelection
from backend.config.axioms import AXIOMS_CONFIG
from backend.core.definitions import FoodItem

from frontend.styles import apply_custom_css
from frontend.state import init_session_state
from frontend.components.sidebar import render_sidebar
from frontend.components.food_matrix import render_food_matrix
from frontend.components.results import render_results


# =============================================================================
# HELPER FUNCTIONS FOR REQUEST BUILDING
# =============================================================================

def _extract_axiom_parameters_from_session(
    group_key: str,
    axiom_key: str,
    original_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extracts axiom parameters from Streamlit session_state.

    Axioms can have different parameter types:
    - meal_validity: params with "exact" or "min/max" or booleans
    - other groups: min/max range plus additional parameters

    Args:
        group_key: Axiom group key (e.g. "nutrition", "daily_frequency")
        axiom_key: Specific axiom key (e.g. "daily_vegetables")
        original_params: Default parameters from AXIOMS_CONFIG

    Returns:
        Dictionary with parameters extracted from session_state
    """
    extracted_params = {}

    if group_key == "meal_validity":
        # meal_validity group: handles multiple parameter types
        for param_key, default_value in original_params.items():
            session_key = f"param_{group_key}_{axiom_key}_{param_key}"
            session_value = st.session_state.get(session_key)

            if session_value is None:
                # Use default if not present in session
                extracted_params[param_key] = default_value
            elif isinstance(default_value, dict):
                # Original value was a dict ({"exact": N} or {"min": N, "max": M})
                if "exact" in default_value:
                    # Single slider -> reconstruct {"exact": value}
                    extracted_params[param_key] = {"exact": session_value}
                else:
                    # Range slider -> reconstruct {"min": v1, "max": v2}
                    if isinstance(session_value, tuple):
                        extracted_params[param_key] = {
                            "min": session_value[0],
                            "max": session_value[1]
                        }
                    else:
                        extracted_params[param_key] = default_value
            else:
                # Boolean or other simple type
                extracted_params[param_key] = session_value
    else:
        # Other groups: may have min/max range
        range_session_key = f"param_{group_key}_{axiom_key}_range"

        if range_session_key in st.session_state:
            min_value, max_value = st.session_state[range_session_key]
            extracted_params["min"] = min_value
            extracted_params["max"] = max_value

        # Extract additional parameters (excluding min/max already handled)
        for param_key, default_value in original_params.items():
            if param_key not in ("min", "max"):
                session_key = f"param_{group_key}_{axiom_key}_{param_key}"
                extracted_params[param_key] = st.session_state.get(session_key, default_value)

    return extracted_params


def _build_food_selections_from_session(food_data: List[FoodItem]) -> List[FoodSelection]:
    """
    Builds the food selection list from session_state.

    For each food item, extracts:
    - enabled: whether the food is enabled by the user
    - rating: user preference (1-5)
    - portion_min/max: customized portion ranges

    Args:
        food_data: List of available food items

    Returns:
        List of FoodSelection objects for the pipeline request
    """
    food_selections = []

    for food in food_data:
        is_enabled = st.session_state.food_enabled.get(food.name, True)
        user_rating = st.session_state.food_ratings.get(food.name, 3)
        portion_range = st.session_state.food_portions.get(
            food.name,
            (food.portion_min, food.portion_max)
        )

        selection = FoodSelection(
            food_id=food.id,
            name=food.name,
            enabled=is_enabled,
            rating=user_rating,
            portion_min=float(portion_range[0]),
            portion_max=float(portion_range[1]),
        )
        food_selections.append(selection)

    return food_selections


def _build_user_preferences_dict(food_data: List[FoodItem]) -> Dict[str, int]:
    """
    Builds the user preferences dictionary.

    Args:
        food_data: List of food items

    Returns:
        Dictionary {food_name: rating}
    """
    return {
        food.name: st.session_state.food_ratings.get(food.name, 3)
        for food in food_data
    }


def _build_nutrition_targets_from_sidebar(sidebar_values: Dict[str, Any]) -> NutritionTargets:
    """
    Builds nutrition targets from sidebar values.

    Args:
        sidebar_values: Values collected from the sidebar

    Returns:
        NutritionTargets object for the pipeline request
    """
    return NutritionTargets(
        n_days=sidebar_values["duration"],
        kcal=sidebar_values["energy"],
        prot_pct=sidebar_values["prot"],
        carb_pct=sidebar_values["carb"],
        fat_pct=sidebar_values["fat"],
        delta_kcal=sidebar_values["delta_kcal"],
        delta_macro=sidebar_values["delta_macro"],
    )


def _build_axioms_config_from_session() -> Dict[str, Dict[str, AxiomConfig]]:
    """
    Builds the axioms configuration from session_state.

    Reads each toggle state and associated parameters
    to construct the full axioms configuration.

    Returns:
        Structured dictionary with the configuration of all axioms
    """
    axioms_config = {}

    for group_key, group_data in AXIOMS_CONFIG.items():
        axioms_config[group_key] = {}

        for axiom_key, axiom_data in group_data['axioms'].items():
            # Toggle state (enabled/disabled)
            toggle_session_key = f"toggle_{group_key}_{axiom_key}"
            is_enabled = st.session_state.get(toggle_session_key, True)

            # Axiom parameters
            original_params = axiom_data.get("params", {})
            extracted_params = _extract_axiom_parameters_from_session(
                group_key, axiom_key, original_params
            )

            axioms_config[group_key][axiom_key] = AxiomConfig(
                enabled=is_enabled,
                params=extracted_params
            )

    return axioms_config


def _build_diet_request(
    food_data: List[FoodItem],
    sidebar_values: Dict[str, Any]
) -> DietRequest:
    """
    Builds the complete request for diet generation.

    Aggregates all information from the GUI (sidebar, food matrix,
    axioms configuration) into a single DietRequest object.

    Args:
        food_data: List of available food items
        sidebar_values: Values collected from the sidebar (objective, targets, etc.)

    Returns:
        DietRequest object ready to be sent to the pipeline
    """
    return DietRequest(
        food_selections=_build_food_selections_from_session(food_data),
        preferences=_build_user_preferences_dict(food_data),
        nutrition_targets=_build_nutrition_targets_from_sidebar(sidebar_values),
        objective=sidebar_values["objective"],
        axioms_config=_build_axioms_config_from_session(),
    )


# =============================================================================
# DIET SERVICE INITIALIZATION
# =============================================================================

@st.cache_resource
def get_diet_service() -> DietService:
    """
    Initializes the diet service with caching.

    Uses @st.cache_resource to ensure the service is created once
    and reused across reruns.

    Loads all visible foods (enabled=True), including those with
    selectable=False, so the GUI can display them.

    Returns:
        DietService instance with loaded data
    """
    service = DietService(csv_path="data/food_db.csv")
    service.load_foods(include_non_selectable=True)
    return service


# =============================================================================
# STREAMLIT PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Axioma - Diet Solver",
    layout="wide"
)


# =============================================================================
# APPLICATION INITIALIZATION
# =============================================================================

# Apply custom CSS styles
apply_custom_css()

# Initialize diet service (cached)
diet_service = get_diet_service()
food_data = diet_service.get_foods()

# Initialize session state
init_session_state(food_data)


# =============================================================================
# UI COMPONENT RENDERING
# =============================================================================

# Sidebar: axiom configuration, objectives, nutrition targets
sidebar_values = render_sidebar()

# Main area: food selection matrix
render_food_matrix(food_data)


# =============================================================================
# DIET GENERATION HANDLING
# =============================================================================

if st.session_state.get("generating", False):
    # Reset flag to avoid accidental re-generation
    st.session_state.generating = False

    # Show spinner during generation
    with sidebar_values["spinner_placeholder"]:
        with st.spinner("Generating diet plan..."):
            # Build the request from the GUI state
            diet_request = _build_diet_request(food_data, sidebar_values)

            # Create a fresh service for each generation
            # (avoids corrupted state after repeated generations)
            fresh_service = DietService(csv_path="data/food_db.csv")
            fresh_service.load_foods(include_non_selectable=True)

            # Generate diet via the pipeline
            diet_response = fresh_service.generate(diet_request)

    # Handle the result
    if diet_response.success:
        st.session_state.diet_result = (diet_response.plan, diet_response.total_cost)
        st.success("Diet plan generated successfully!")
    else:
        st.session_state.diet_result = None  # Clear stale result on failure
        st.error(f"Error: {diet_response.error_message}")


# =============================================================================
# RESULTS DISPLAY
# =============================================================================

render_results(food_data)
