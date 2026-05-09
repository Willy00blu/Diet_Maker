"""
Meal Validity Axioms (Micro-Logic).

This module defines constraints that determine the COMPOSITION of each individual meal.
Called "Micro-Logic" because it operates at the meal level (the most granular level).

Each meal must follow a specific structure:
- BREAKFAST: 1 protein, 1 carbohydrate, 0-1 fat, 0-1 fruit, XOR sweet/savory
- LUNCH: 1 protein, 1 carbohydrate, 1 vegetable, 1 fat, 0-1 fruit
- SNACK: max 1 per category, minimum 1 total item, XOR sweet/savory
- DINNER: 1 protein, 1 carbohydrate, 1 vegetable, 1 fat, 0-1 fruit

The XOR sweet/savory constraint ensures sweet and savory foods are not mixed
in the same meal (e.g. no sweet yogurt with whole wheat bread).
"""

from typing import List, Set, Dict, Any, Optional
from pulp import LpProblem, lpSum

from backend.core.definitions import FoodItem, TAGS
from backend.config.axioms import MEAL_VALIDITY_AXIOMS


# =============================================================================
# TAG NAME CONSTANTS
# =============================================================================

# Protein tags
TAG_MEAT = TAGS["PROTEINE"]["CARNE"]
TAG_FISH = TAGS["PROTEINE"]["PESCE"]
TAG_EGGS = TAGS["PROTEINE"]["UOVA"]
TAG_DAIRY_SAVORY = TAGS["PROTEINE"]["LATTICINI_SALATI"]
TAG_DAIRY_SWEET = TAGS["PROTEINE"]["LATTICINI_DOLCI"]
TAG_LEGUMES = TAGS["PROTEINE"]["LEGUMI"]

# Carbohydrate tags
TAG_CARBS_SAVORY = TAGS["CARBO"]["COMPLESSI_SALATI"]
TAG_CARBS_SWEET = TAGS["CARBO"]["DOLCI_COLAZIONE"]

# Fat, vegetable and fruit tags
TAG_FATS = TAGS["GRASSI"]["PURI"]
TAG_VEGETABLES = TAGS["ALTRI"]["VERDURE"]
TAG_FRUIT = TAGS["ALTRI"]["FRUTTA"]


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

    Allows the GUI to override axiom parameters.
    If the axiom is not configured in the GUI, uses default values.

    Args:
        axioms_config: Full axioms configuration from the GUI (may be None)
        group: Axiom group name (e.g. "meal_validity")
        axiom: Specific axiom name (e.g. "breakfast")
        default_config: Default configuration to use if not specified

    Returns:
        Dict with "enabled" (bool) and "params" (dict)
    """
    if axioms_config and group in axioms_config and axiom in axioms_config[group]:
        return axioms_config[group][axiom]
    return default_config


def _get_foods_with_any_tag(
    food_data: List[FoodItem],
    tags: List[str]
) -> List[FoodItem]:
    """
    Filters foods that have AT LEAST ONE of the specified tags.

    Args:
        food_data: List of all available food items
        tags: List of tags to search for

    Returns:
        List of FoodItem objects that have at least one of the tags
    """
    matching_foods = []
    for food in food_data:
        if any(tag in food.tags for tag in tags):
            matching_foods.append(food)
    return matching_foods


def _get_food_ids_with_any_tag(
    food_data: List[FoodItem],
    tags: List[str]
) -> Set[int]:
    """
    Returns the IDs of foods that have AT LEAST ONE of the specified tags.

    Args:
        food_data: List of all available food items
        tags: List of tags to search for

    Returns:
        Set of food_id values for matching food items
    """
    return {food.id for food in _get_foods_with_any_tag(food_data, tags)}


def _get_selection_variables_for_slot_and_tags(
    selection_variables: Dict,
    food_data: List[FoodItem],
    day: str,
    slot: str,
    tags: List[str]
) -> List:
    """
    Returns selection variables for a given slot and set of tags.

    Used to build constraints on food groups. For example, "exactly 1 protein
    at lunch" requires summing all selection variables for protein foods at lunch.

    Args:
        selection_variables: Selection variables dict {(food_id, day, slot): var}
        food_data: List of food items
        day: Day name (e.g. "Monday")
        slot: Meal slot name (e.g. "Lunch")
        tags: List of tags identifying the food group

    Returns:
        List of LpVariable objects for matching foods
    """
    # Convert to list if a single string was passed
    if isinstance(tags, str):
        tags = [tags]

    variables = []
    for food in food_data:
        if any(tag in food.tags for tag in tags):
            variables.append(selection_variables[food.id, day, slot])

    return variables


def _exclude_non_allowed_foods_from_slot(
    problem: LpProblem,
    selection_variables: Dict,
    food_data: List[FoodItem],
    day: str,
    slot: str,
    allowed_tags: List[str]
) -> None:
    """
    Forces the selection of non-allowed foods to zero for a given slot.

    Ensures that only foods with the correct tags can appear in a given meal.
    For example, meat is not allowed at breakfast.

    Args:
        problem: The PuLP optimization problem
        selection_variables: Selection variables dictionary
        food_data: List of food items
        day: Day name
        slot: Meal slot name
        allowed_tags: List of tags allowed for this slot
    """
    allowed_food_ids = _get_food_ids_with_any_tag(food_data, allowed_tags)

    for food in food_data:
        if food.id not in allowed_food_ids:
            constraint_name = f"Excluded_{food.id}_{slot}_{day}"
            problem += selection_variables[food.id, day, slot] == 0, constraint_name


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def apply_meal_validity_axioms(
    problem: LpProblem,
    selection_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    axioms_config: Optional[Dict] = None
) -> None:
    """
    Applies meal validity axioms for a given day.

    These axioms define the structure of each meal, ensuring that:
    1. Each meal contains the correct food groups
    2. Non-allowed foods are excluded
    3. Sweet and savory foods are not mixed (where applicable)

    Args:
        problem: The PuLP optimization problem
        selection_variables: Dictionary {(food_id, day, slot): binary LpVariable}
        day: Day name (e.g. "Monday")
        food_data: List of available food items
        axioms_config: Axioms configuration from the GUI (optional)
    """
    default_config = MEAL_VALIDITY_AXIOMS

    # Apply axioms for each meal
    _apply_breakfast_axiom(problem, selection_variables, day, food_data, axioms_config, default_config)
    _apply_lunch_axiom(problem, selection_variables, day, food_data, axioms_config, default_config)
    _apply_snack_axiom(problem, selection_variables, day, food_data, axioms_config, default_config)
    _apply_dinner_axiom(problem, selection_variables, day, food_data, axioms_config, default_config)


# =============================================================================
# PER-MEAL AXIOMS
# =============================================================================

def _get_param_value(params: Dict, key: str, subkey: str, default: int) -> int:
    """
    Extracts a numeric value from parameters, handling both
    {"key": {"exact": N}} and {"key": N} formats.

    Args:
        params: Parameters dictionary
        key: Main key (e.g. "proteine")
        subkey: Sub-key (e.g. "exact", "min", "max")
        default: Default value if not found

    Returns:
        Extracted numeric value
    """
    value = params.get(key, default)
    if isinstance(value, dict):
        return value.get(subkey, default)
    return value


def _force_empty_slot(
    problem: LpProblem,
    selection_variables: Dict,
    food_data: List[FoodItem],
    day: str,
    slot: str
) -> None:
    """
    Forces a slot to be empty (no food selected).

    Used when a meal is disabled from the GUI.

    Args:
        problem: The optimization problem
        selection_variables: Selection variables
        food_data: List of food items
        day: Day name
        slot: Meal slot name to force empty
    """
    for food in food_data:
        constraint_name = f"ForceEmpty_{slot}_{food.id}_{day}"
        problem += selection_variables[food.id, day, slot] == 0, constraint_name


def _apply_breakfast_axiom(
    problem: LpProblem,
    selection_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """
    Applies the validity axiom for BREAKFAST.

    Required structure:
    - Exactly 1 protein (sweet OR savory)
    - Exactly 1 carbohydrate (sweet OR savory)
    - At most 1 fat
    - At most 1 fruit
    - XOR sweet/savory: if a sweet protein is chosen, a sweet carb must be chosen (and vice versa)

    Args:
        problem: The optimization problem
        selection_variables: Selection variables
        day: Day name
        food_data: List of food items
        axioms_config: Configuration from the GUI
        default_config: Default configuration
    """
    config = _get_axiom_config(axioms_config, "meal_validity", "breakfast", default_config["breakfast"])
    params = config.get("params", {})

    if not config["enabled"]:
        _force_empty_slot(problem, selection_variables, food_data, day, "Breakfast")
        return

    slot = "Breakfast"

    # --- READ PARAMETERS FROM CONFIG ---
    prot_exact = _get_param_value(params, "proteine", "exact", 1)
    carb_exact = _get_param_value(params, "carboidrati", "exact", 1)
    fat_min = _get_param_value(params, "grassi", "min", 0)
    fat_max = _get_param_value(params, "grassi", "max", 1)
    fruit_min = _get_param_value(params, "frutta", "min", 0)
    fruit_max = _get_param_value(params, "frutta", "max", 1)

    # --- DEFINE ALLOWED TAGS FOR BREAKFAST ---
    allowed_tags_for_breakfast = [
        # Proteins
        TAG_MEAT["COL"], TAG_FISH["COL"], TAG_EGGS["COL"],
        TAG_DAIRY_SAVORY["COL"], TAG_DAIRY_SWEET["COL"],
        # Carbohydrates
        TAG_CARBS_SAVORY["COL"], TAG_CARBS_SWEET["COL"],
        # Others
        TAG_FATS["COL"], TAG_FRUIT["COL"]
    ]

    # Exclude all foods not allowed at breakfast
    _exclude_non_allowed_foods_from_slot(
        problem, selection_variables, food_data, day, slot, allowed_tags_for_breakfast
    )

    # --- RETRIEVE VARIABLES FOR EACH FOOD GROUP ---

    # Savory proteins: meat, fish, eggs, savory dairy
    savory_proteins = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_MEAT["COL"], TAG_FISH["COL"], TAG_EGGS["COL"], TAG_DAIRY_SAVORY["COL"]]
    )

    # Sweet proteins: sweet dairy (yogurt, milk...)
    sweet_proteins = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_DAIRY_SWEET["COL"]]
    )

    # Savory carbs: whole wheat bread, crackers...
    savory_carbs = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_CARBS_SAVORY["COL"]]
    )

    # Sweet carbs: cereals, muesli...
    sweet_carbs = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_CARBS_SWEET["COL"]]
    )

    # Fats
    fats = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_FATS["COL"]]
    )

    # Fruit
    fruits = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_FRUIT["COL"]]
    )

    # --- APPLY COMPOSITION CONSTRAINTS (using GUI parameters) ---

    all_proteins = savory_proteins + sweet_proteins
    all_carbs = savory_carbs + sweet_carbs

    # Protein constraint
    if prot_exact > 0:
        problem += lpSum(all_proteins) == prot_exact, f"Breakfast_Exact{prot_exact}_Protein_{day}"
    else:
        problem += lpSum(all_proteins) == 0, f"Breakfast_NoProtein_{day}"

    # Carbohydrate constraint
    if carb_exact > 0:
        problem += lpSum(all_carbs) == carb_exact, f"Breakfast_Exact{carb_exact}_Carb_{day}"
    else:
        problem += lpSum(all_carbs) == 0, f"Breakfast_NoCarb_{day}"

    # Fat constraint (min-max range)
    problem += lpSum(fats) >= fat_min, f"Breakfast_Min{fat_min}_Fat_{day}"
    problem += lpSum(fats) <= fat_max, f"Breakfast_Max{fat_max}_Fat_{day}"

    # Fruit constraint (min-max range)
    problem += lpSum(fruits) >= fruit_min, f"Breakfast_Min{fruit_min}_Fruit_{day}"
    problem += lpSum(fruits) <= fruit_max, f"Breakfast_Max{fruit_max}_Fruit_{day}"

    # --- XOR SWEET/SAVORY CONSTRAINT ---
    # Prevents mixing sweet and savory at breakfast.
    # If a sweet protein is chosen, a sweet carb must be chosen (and vice versa).
    #
    # Implemented with 2 constraints:
    # 1. sweet_protein + savory_carb <= 1 (cannot have both)
    # 2. savory_protein + sweet_carb <= 1 (cannot have both)

    if params.get("xor_dolce_salato", True):
        # Constraint 1: sweet protein excludes savory carb
        problem += (
            lpSum(sweet_proteins) + lpSum(savory_carbs) <= 1,
            f"Breakfast_XOR_SweetProtein_SavoryCarb_{day}"
        )

        # Constraint 2: savory protein excludes sweet carb
        problem += (
            lpSum(savory_proteins) + lpSum(sweet_carbs) <= 1,
            f"Breakfast_XOR_SavoryProtein_SweetCarb_{day}"
        )


def _apply_lunch_axiom(
    problem: LpProblem,
    selection_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """
    Applies the validity axiom for LUNCH.

    Required structure:
    - Exactly 1 protein
    - Exactly 1 carbohydrate
    - Exactly 1 vegetable
    - Exactly 1 fat (dressing/condiment)
    - At most 1 fruit

    Lunch is always SAVORY, so there is no XOR sweet/savory constraint.

    Args:
        problem: The optimization problem
        selection_variables: Selection variables
        day: Day name
        food_data: List of food items
        axioms_config: Configuration from the GUI
        default_config: Default configuration
    """
    config = _get_axiom_config(axioms_config, "meal_validity", "lunch", default_config["lunch"])
    params = config.get("params", {})

    if not config["enabled"]:
        _force_empty_slot(problem, selection_variables, food_data, day, "Lunch")
        return

    slot = "Lunch"

    # --- READ PARAMETERS FROM CONFIG ---
    prot_exact = _get_param_value(params, "proteine", "exact", 1)
    carb_exact = _get_param_value(params, "carboidrati", "exact", 1)
    veg_exact = _get_param_value(params, "verdure", "exact", 1)
    fat_exact = _get_param_value(params, "grassi", "exact", 1)
    fruit_min = _get_param_value(params, "frutta", "min", 0)
    fruit_max = _get_param_value(params, "frutta", "max", 1)

    # --- DEFINE ALLOWED TAGS FOR LUNCH ---
    allowed_tags_for_lunch = [
        # Proteins (all savory)
        TAG_MEAT["PRA"], TAG_FISH["PRA"], TAG_EGGS["PRA"],
        TAG_DAIRY_SAVORY["PRA"], TAG_LEGUMES["PRA"],
        # Carbohydrates
        TAG_CARBS_SAVORY["PRA"],
        # Vegetables and others
        TAG_VEGETABLES["PRA"], TAG_FATS["PRA"], TAG_FRUIT["PRA"]
    ]

    _exclude_non_allowed_foods_from_slot(
        problem, selection_variables, food_data, day, slot, allowed_tags_for_lunch
    )

    # --- RETRIEVE VARIABLES FOR EACH FOOD GROUP ---

    proteins = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_MEAT["PRA"], TAG_FISH["PRA"], TAG_EGGS["PRA"],
         TAG_DAIRY_SAVORY["PRA"], TAG_LEGUMES["PRA"]]
    )

    carbs = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_CARBS_SAVORY["PRA"]]
    )

    vegetables = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_VEGETABLES["PRA"]]
    )

    fats = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_FATS["PRA"]]
    )

    fruits = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_FRUIT["PRA"]]
    )

    # --- APPLY COMPOSITION CONSTRAINTS (using GUI parameters) ---

    # Protein constraint
    if prot_exact > 0:
        problem += lpSum(proteins) == prot_exact, f"Lunch_Exact{prot_exact}_Protein_{day}"
    else:
        problem += lpSum(proteins) == 0, f"Lunch_NoProtein_{day}"

    # Carbohydrate constraint
    if carb_exact > 0:
        problem += lpSum(carbs) == carb_exact, f"Lunch_Exact{carb_exact}_Carb_{day}"
    else:
        problem += lpSum(carbs) == 0, f"Lunch_NoCarb_{day}"

    # Vegetable constraint
    if veg_exact > 0:
        problem += lpSum(vegetables) == veg_exact, f"Lunch_Exact{veg_exact}_Vegetable_{day}"
    else:
        problem += lpSum(vegetables) == 0, f"Lunch_NoVegetable_{day}"

    # Fat constraint
    if fat_exact > 0:
        problem += lpSum(fats) == fat_exact, f"Lunch_Exact{fat_exact}_Fat_{day}"
    else:
        problem += lpSum(fats) == 0, f"Lunch_NoFat_{day}"

    # Fruit constraint (min-max range)
    problem += lpSum(fruits) >= fruit_min, f"Lunch_Min{fruit_min}_Fruit_{day}"
    problem += lpSum(fruits) <= fruit_max, f"Lunch_Max{fruit_max}_Fruit_{day}"


def _apply_snack_axiom(
    problem: LpProblem,
    selection_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """
    Applies the validity axiom for SNACK.

    Required structure:
    - At most 1 protein
    - At most 1 carbohydrate
    - At most 1 fat
    - At most 1 fruit
    - Minimum 1 total item (snack cannot be empty)
    - XOR sweet/savory

    The snack is more flexible than other meals but must still
    contain at least one food item.

    Args:
        problem: The optimization problem
        selection_variables: Selection variables
        day: Day name
        food_data: List of food items
        axioms_config: Configuration from the GUI
        default_config: Default configuration
    """
    config = _get_axiom_config(axioms_config, "meal_validity", "snack", default_config["snack"])
    params = config.get("params", {})

    if not config["enabled"]:
        _force_empty_slot(problem, selection_variables, food_data, day, "Snack")
        return

    slot = "Snack"

    # --- READ PARAMETERS FROM CONFIG ---
    prot_min = _get_param_value(params, "proteine", "min", 0)
    prot_max = _get_param_value(params, "proteine", "max", 1)
    carb_min = _get_param_value(params, "carboidrati", "min", 0)
    carb_max = _get_param_value(params, "carboidrati", "max", 1)
    fat_min = _get_param_value(params, "grassi", "min", 0)
    fat_max = _get_param_value(params, "grassi", "max", 1)
    fruit_min = _get_param_value(params, "frutta", "min", 0)
    fruit_max = _get_param_value(params, "frutta", "max", 1)
    min_total = params.get("min_totale", 1)

    # --- DEFINE ALLOWED TAGS FOR SNACK ---
    allowed_tags_for_snack = [
        # Proteins (sweet and savory)
        TAG_MEAT["SNA"], TAG_FISH["SNA"], TAG_EGGS["SNA"],
        TAG_DAIRY_SAVORY["SNA"], TAG_LEGUMES["SNA"], TAG_DAIRY_SWEET["SNA"],
        # Carbohydrates
        TAG_CARBS_SAVORY["SNA"], TAG_CARBS_SWEET["SNA"],
        # Others
        TAG_FATS["SNA"], TAG_FRUIT["SNA"]
    ]

    _exclude_non_allowed_foods_from_slot(
        problem, selection_variables, food_data, day, slot, allowed_tags_for_snack
    )

    # --- RETRIEVE VARIABLES FOR EACH FOOD GROUP ---

    # Savory proteins
    savory_proteins = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_MEAT["SNA"], TAG_FISH["SNA"], TAG_EGGS["SNA"],
         TAG_DAIRY_SAVORY["SNA"], TAG_LEGUMES["SNA"]]
    )

    # Sweet proteins
    sweet_proteins = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_DAIRY_SWEET["SNA"]]
    )

    # Savory carbs
    savory_carbs = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_CARBS_SAVORY["SNA"]]
    )

    # Sweet carbs
    sweet_carbs = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_CARBS_SWEET["SNA"]]
    )

    # Fats
    fats = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_FATS["SNA"]]
    )

    # Fruit
    fruits = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_FRUIT["SNA"]]
    )

    # All allowed snack items
    all_snack_items = savory_proteins + sweet_proteins + savory_carbs + sweet_carbs + fats + fruits

    # --- APPLY COMPOSITION CONSTRAINTS (using GUI parameters) ---

    all_proteins = savory_proteins + sweet_proteins
    all_carbs = savory_carbs + sweet_carbs

    # Protein constraints (min-max range)
    problem += lpSum(all_proteins) >= prot_min, f"Snack_Min{prot_min}_Protein_{day}"
    problem += lpSum(all_proteins) <= prot_max, f"Snack_Max{prot_max}_Protein_{day}"

    # Carbohydrate constraints (min-max range)
    problem += lpSum(all_carbs) >= carb_min, f"Snack_Min{carb_min}_Carb_{day}"
    problem += lpSum(all_carbs) <= carb_max, f"Snack_Max{carb_max}_Carb_{day}"

    # Fat constraints (min-max range)
    problem += lpSum(fats) >= fat_min, f"Snack_Min{fat_min}_Fat_{day}"
    problem += lpSum(fats) <= fat_max, f"Snack_Max{fat_max}_Fat_{day}"

    # Fruit constraints (min-max range)
    problem += lpSum(fruits) >= fruit_min, f"Snack_Min{fruit_min}_Fruit_{day}"
    problem += lpSum(fruits) <= fruit_max, f"Snack_Max{fruit_max}_Fruit_{day}"

    # Constraint: minimum N total items
    problem += lpSum(all_snack_items) >= min_total, f"Snack_Min{min_total}_Total_{day}"

    # --- XOR SWEET/SAVORY CONSTRAINT ---
    if params.get("xor_dolce_salato", True):
        # Constraint 1: sweet protein excludes savory carb
        problem += (
            lpSum(sweet_proteins) + lpSum(savory_carbs) <= 1,
            f"Snack_XOR_SweetProtein_SavoryCarb_{day}"
        )

        # Constraint 2: savory protein excludes sweet carb
        problem += (
            lpSum(savory_proteins) + lpSum(sweet_carbs) <= 1,
            f"Snack_XOR_SavoryProtein_SweetCarb_{day}"
        )


def _apply_dinner_axiom(
    problem: LpProblem,
    selection_variables: Dict,
    day: str,
    food_data: List[FoodItem],
    axioms_config: Optional[Dict],
    default_config: Dict
) -> None:
    """
    Applies the validity axiom for DINNER.

    Required structure (identical to lunch):
    - Exactly 1 protein
    - Exactly 1 carbohydrate
    - Exactly 1 vegetable
    - Exactly 1 fat (dressing/condiment)
    - At most 1 fruit

    Dinner is always SAVORY, so there is no XOR sweet/savory constraint.

    Args:
        problem: The optimization problem
        selection_variables: Selection variables
        day: Day name
        food_data: List of food items
        axioms_config: Configuration from the GUI
        default_config: Default configuration
    """
    config = _get_axiom_config(axioms_config, "meal_validity", "dinner", default_config["dinner"])
    params = config.get("params", {})

    if not config["enabled"]:
        _force_empty_slot(problem, selection_variables, food_data, day, "Dinner")
        return

    slot = "Dinner"

    # --- READ PARAMETERS FROM CONFIG ---
    prot_exact = _get_param_value(params, "proteine", "exact", 1)
    carb_exact = _get_param_value(params, "carboidrati", "exact", 1)
    veg_exact = _get_param_value(params, "verdure", "exact", 1)
    fat_exact = _get_param_value(params, "grassi", "exact", 1)
    fruit_min = _get_param_value(params, "frutta", "min", 0)
    fruit_max = _get_param_value(params, "frutta", "max", 1)

    # --- DEFINE ALLOWED TAGS FOR DINNER ---
    allowed_tags_for_dinner = [
        # Proteins (all savory)
        TAG_MEAT["CEN"], TAG_FISH["CEN"], TAG_EGGS["CEN"],
        TAG_DAIRY_SAVORY["CEN"], TAG_LEGUMES["CEN"],
        # Carbohydrates
        TAG_CARBS_SAVORY["CEN"],
        # Vegetables and others
        TAG_VEGETABLES["CEN"], TAG_FATS["CEN"], TAG_FRUIT["CEN"]
    ]

    _exclude_non_allowed_foods_from_slot(
        problem, selection_variables, food_data, day, slot, allowed_tags_for_dinner
    )

    # --- RETRIEVE VARIABLES FOR EACH FOOD GROUP ---

    proteins = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_MEAT["CEN"], TAG_FISH["CEN"], TAG_EGGS["CEN"],
         TAG_DAIRY_SAVORY["CEN"], TAG_LEGUMES["CEN"]]
    )

    carbs = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_CARBS_SAVORY["CEN"]]
    )

    vegetables = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_VEGETABLES["CEN"]]
    )

    fats = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_FATS["CEN"]]
    )

    fruits = _get_selection_variables_for_slot_and_tags(
        selection_variables, food_data, day, slot,
        [TAG_FRUIT["CEN"]]
    )

    # --- APPLY COMPOSITION CONSTRAINTS (using GUI parameters) ---

    # Protein constraint
    if prot_exact > 0:
        problem += lpSum(proteins) == prot_exact, f"Dinner_Exact{prot_exact}_Protein_{day}"
    else:
        problem += lpSum(proteins) == 0, f"Dinner_NoProtein_{day}"

    # Carbohydrate constraint
    if carb_exact > 0:
        problem += lpSum(carbs) == carb_exact, f"Dinner_Exact{carb_exact}_Carb_{day}"
    else:
        problem += lpSum(carbs) == 0, f"Dinner_NoCarb_{day}"

    # Vegetable constraint
    if veg_exact > 0:
        problem += lpSum(vegetables) == veg_exact, f"Dinner_Exact{veg_exact}_Vegetable_{day}"
    else:
        problem += lpSum(vegetables) == 0, f"Dinner_NoVegetable_{day}"

    # Fat constraint
    if fat_exact > 0:
        problem += lpSum(fats) == fat_exact, f"Dinner_Exact{fat_exact}_Fat_{day}"
    else:
        problem += lpSum(fats) == 0, f"Dinner_NoFat_{day}"

    # Fruit constraint (min-max range)
    problem += lpSum(fruits) >= fruit_min, f"Dinner_Min{fruit_min}_Fruit_{day}"
    problem += lpSum(fruits) <= fruit_max, f"Dinner_Max{fruit_max}_Fruit_{day}"
