"""
Sidebar Component - Axiom Configuration, Objectives and Nutrition Targets.

The sidebar is the main control panel for configuring diet generation parameters:
- Axiom (constraint) toggles and parameters
- Optimization objective selection
- Daily nutrition targets and tolerances
- Generate button
"""

import streamlit as st
from typing import Dict, Any, Tuple

from backend.config.axioms import AXIOMS_CONFIG
from backend.config.nutrition import N_DAYS, TARGET_KCAL, PCT_PROT, PCT_CARB, PCT_FAT, DELTA_KCAL, DELTA_MACRO
from backend.config.objectives import OBJECTIVES_CONFIG
from backend.config.constants import (
    MIN_DIET_DAYS as DAYS_MIN,
    MAX_DIET_DAYS as DAYS_MAX,
    AXIOM_PARAMETER_MAX_RANGE as RANGE_SLIDER_MAX,
    MAX_MEAL_COMPONENTS as MEAL_PARAM_SLIDER_MAX,
)


# =============================================================================
# UI CONSTANTS
# =============================================================================

MACRO_PERCENTAGE_MIN = 0
MACRO_PERCENTAGE_MAX = 100
MACRO_TOTAL_REQUIRED = 100

RANGE_SLIDER_MIN = 0
MEAL_PARAM_SLIDER_MIN = 0

ENERGY_STEP = 50

DELTA_KCAL_MIN = 0
DELTA_KCAL_MAX = 50
DELTA_MACRO_MIN = 0
DELTA_MACRO_MAX = 100


# =============================================================================
# AXIOM PARAMETER RENDERING HELPERS
# =============================================================================

def _render_meal_validity_parameter(
    group_key: str,
    axiom_key: str,
    param_key: str,
    param_value: Any
) -> None:
    """Renders a single parameter for meal_validity axioms."""
    session_key = f"param_{group_key}_{axiom_key}_{param_key}"
    label = param_key.replace("_", " ").capitalize()

    if isinstance(param_value, dict):
        if "exact" in param_value:
            st.slider(
                label,
                min_value=MEAL_PARAM_SLIDER_MIN,
                max_value=MEAL_PARAM_SLIDER_MAX,
                value=param_value["exact"],
                key=session_key
            )
        else:
            st.select_slider(
                label,
                options=list(range(MEAL_PARAM_SLIDER_MIN, MEAL_PARAM_SLIDER_MAX + 1)),
                value=(param_value.get("min", 0), param_value.get("max", 1)),
                key=session_key
            )
    elif isinstance(param_value, bool):
        st.toggle(label, value=param_value, key=session_key)
    elif isinstance(param_value, int):
        st.number_input(label, value=param_value, key=session_key)


def _render_standard_axiom_parameter(
    group_key: str,
    axiom_key: str,
    param_key: str,
    param_value: Any
) -> None:
    """Renders a single parameter for standard (non meal_validity) axioms."""
    session_key = f"param_{group_key}_{axiom_key}_{param_key}"
    label = param_key.replace("_", " ").capitalize()

    if isinstance(param_value, bool):
        st.toggle(label, value=param_value, key=session_key)
    elif isinstance(param_value, float):
        # Float params are percentage fractions in [0, 1] (e.g. 0.35 = 35%)
        # Clamp to prevent the user from entering an integer (e.g. 35) that
        # would be interpreted as 35× the target, causing infeasibility.
        st.number_input(
            label, value=param_value,
            min_value=0.0, max_value=1.0, step=0.01,
            key=session_key
        )
    elif isinstance(param_value, int):
        st.number_input(label, value=param_value, key=session_key)


def _render_axiom_parameters(
    group_key: str,
    axiom_key: str,
    params: Dict[str, Any]
) -> None:
    """Renders all parameters of an axiom inside its settings popover."""
    if group_key == "meal_validity":
        for param_key, param_value in params.items():
            _render_meal_validity_parameter(group_key, axiom_key, param_key, param_value)
    else:
        if "min" in params and "max" in params:
            st.select_slider(
                "Range",
                options=list(range(RANGE_SLIDER_MIN, RANGE_SLIDER_MAX + 1)),
                value=(params["min"], params["max"]),
                key=f"param_{group_key}_{axiom_key}_range"
            )
            for param_key, param_value in params.items():
                if param_key not in ("min", "max"):
                    _render_standard_axiom_parameter(
                        group_key, axiom_key, param_key, param_value
                    )
        else:
            for param_key, param_value in params.items():
                _render_standard_axiom_parameter(
                    group_key, axiom_key, param_key, param_value
                )


# =============================================================================
# SIDEBAR SECTIONS
# =============================================================================

def _render_axioms_section() -> None:
    """Renders the axiom configuration section."""
    for group_key, group_data in AXIOMS_CONFIG.items():
        group_icon = group_data['icon']
        group_label = group_data['label']
        group_description = group_data['description']

        with st.expander(f"{group_icon} {group_label}", expanded=False):
            st.caption(group_description)

            for axiom_key, axiom_data in group_data['axioms'].items():
                axiom_icon = axiom_data['icon']
                axiom_label = axiom_data['label']
                axiom_description = axiom_data['description']
                axiom_enabled_default = axiom_data.get("enabled", True)
                axiom_params = axiom_data.get("params", {})

                toggle_column, params_column = st.columns([4, 1])

                with toggle_column:
                    st.toggle(
                        f"{axiom_icon} {axiom_label}",
                        value=axiom_enabled_default,
                        help=axiom_description,
                        key=f"toggle_{group_key}_{axiom_key}"
                    )

                with params_column:
                    if axiom_params:
                        with st.popover("⚙️"):
                            st.caption(f"**{axiom_label}**")
                            _render_axiom_parameters(group_key, axiom_key, axiom_params)


def _render_objectives_section() -> str:
    """
    Renders the optimization objective selection section.

    Returns:
        Key of the selected objective ("cost", "preference", or "none")
    """
    st.subheader("Optimization Objective")

    enabled_objectives = {
        key: config
        for key, config in OBJECTIVES_CONFIG.items()
        if config.get("enabled", True)
    }

    objective_keys = list(enabled_objectives.keys())

    default_objective_index = next(
        (index for index, (key, config) in enumerate(enabled_objectives.items())
         if config.get("default", False)),
        0
    )

    help_text = " | ".join(
        f"{config['label']}: {config['description']}"
        for config in enabled_objectives.values()
    )

    selected_objective = st.radio(
        "Search strategy",
        options=objective_keys,
        format_func=lambda key: f"{OBJECTIVES_CONFIG[key]['icon']} {OBJECTIVES_CONFIG[key]['label']}",
        index=default_objective_index,
        help=help_text
    )

    return selected_objective


def _render_daily_targets_section() -> Tuple[int, int, int, int, int, int, int, int]:
    """
    Renders the daily nutrition targets section.

    Returns:
        Tuple (duration_days, calories, prot_pct, carb_pct, fat_pct,
               macro_total, delta_kcal_pct, delta_macro_pct)
    """
    st.subheader("Daily Targets")

    diet_duration_days = st.number_input(
        "Duration (Days)",
        value=N_DAYS,
        min_value=DAYS_MIN,
        max_value=DAYS_MAX
    )

    daily_calories = st.number_input(
        "Energy (kcal)",
        value=TARGET_KCAL,
        step=ENERGY_STEP
    )

    st.write("Macro split")

    protein_percentage = st.slider(
        "Protein %",
        min_value=MACRO_PERCENTAGE_MIN,
        max_value=MACRO_PERCENTAGE_MAX,
        value=int(PCT_PROT * 100)
    )

    carb_percentage = st.slider(
        "Carbohydrates %",
        min_value=MACRO_PERCENTAGE_MIN,
        max_value=MACRO_PERCENTAGE_MAX,
        value=int(PCT_CARB * 100)
    )

    fat_percentage = st.slider(
        "Fat %",
        min_value=MACRO_PERCENTAGE_MIN,
        max_value=MACRO_PERCENTAGE_MAX,
        value=int(PCT_FAT * 100)
    )

    macro_total = protein_percentage + carb_percentage + fat_percentage

    if macro_total != MACRO_TOTAL_REQUIRED:
        st.error(f"Macro sum: {macro_total}% (must equal {MACRO_TOTAL_REQUIRED}%)")
    else:
        st.success(f"Macro sum: {macro_total}%")

    st.write("Tolerances")

    default_delta_kcal = int(DELTA_KCAL * 100)
    default_delta_macro = int(DELTA_MACRO * 100)

    delta_kcal_percentage = st.slider(
        "Calorie tolerance ±%",
        min_value=DELTA_KCAL_MIN,
        max_value=DELTA_KCAL_MAX,
        value=default_delta_kcal,
        help="Tolerance on daily calories (e.g. 10% = ±200 kcal on 2000)"
    )

    delta_macro_percentage = st.slider(
        "Macro tolerance ±%",
        min_value=DELTA_MACRO_MIN,
        max_value=DELTA_MACRO_MAX,
        value=default_delta_macro,
        help="Tolerance on macronutrient targets (e.g. 50% = high flexibility)"
    )

    return (
        diet_duration_days,
        daily_calories,
        protein_percentage,
        carb_percentage,
        fat_percentage,
        macro_total,
        delta_kcal_percentage,
        delta_macro_percentage
    )


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def render_sidebar() -> Dict[str, Any]:
    """
    Renders the full application sidebar.

    Returns:
        Dictionary with all configured values:
        - objective, duration, energy, prot, carb, fat, total_macro,
          delta_kcal, delta_macro, generate_clicked, spinner_placeholder
    """
    with st.sidebar:
        st.title("Logic & Targets")

        button_placeholder = st.empty()
        spinner_placeholder = st.empty()
        warning_placeholder = st.empty()

        st.divider()

        _render_axioms_section()

        st.divider()

        selected_objective = _render_objectives_section()

        st.divider()

        with st.container():
            (
                duration_days,
                daily_energy,
                protein_pct,
                carb_pct,
                fat_pct,
                macro_total,
                delta_kcal_pct,
                delta_macro_pct
            ) = _render_daily_targets_section()

        is_macro_valid = (macro_total == MACRO_TOTAL_REQUIRED)

        with button_placeholder:
            generate_button_clicked = st.button(
                "GENERATE OPTIMIZED DIET",
                use_container_width=True,
                disabled=not is_macro_valid
            )

        with warning_placeholder:
            if not is_macro_valid:
                st.warning("Fix the macro split to enable diet generation")

        if generate_button_clicked:
            st.session_state.generating = True

    return {
        "objective": selected_objective,
        "duration": duration_days,
        "energy": daily_energy,
        "prot": protein_pct,
        "carb": carb_pct,
        "fat": fat_pct,
        "total_macro": macro_total,
        "delta_kcal": delta_kcal_pct,
        "delta_macro": delta_macro_pct,
        "generate_clicked": generate_button_clicked,
        "spinner_placeholder": spinner_placeholder,
    }
