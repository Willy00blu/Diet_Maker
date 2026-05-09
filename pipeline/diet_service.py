"""
Orchestration Service for Diet Plan Generation.

This module implements the Service pattern that acts as a bridge between the GUI
(frontend) and the solver (backend), orchestrating the complete data flow.

DietService responsibilities:
- Loading and managing the food database
- Validating GUI requests before passing them to the backend
- Transforming user selections into a format consumable by the solver
- Handling errors and returning structured responses

The service encapsulates all coordination logic, allowing the GUI to remain
simple and the backend to be agnostic to the interface.

Usage example:
    >>> service = DietService()
    >>> food_data = service.load_foods()
    >>> response = service.generate(diet_request)
    >>> if response.success:
    ...     display_plan(response.plan)
"""

from typing import Dict, List, Optional

from backend.core.definitions import FoodItem
from backend.data_loader import load_food_data, load_all_visible_foods
from backend.optimizer import generate_diet_plan
from backend.config.constants import MIN_ENABLED_FOODS as MIN_FOODS_FOR_GENERATION
from pipeline.contracts import DietRequest, DietResponse, FoodSelection
from pipeline.validators import validate_request


# =============================================================================
# CONSTANTS
# =============================================================================

# Default path to the food database
DEFAULT_CSV_PATH = "data/food_db.csv"

# Messaggi di errore standardizzati
ERROR_VALIDATION_PREFIX = "Validation errors:\n"
ERROR_TOO_FEW_FOODS = (
    "Too few foods enabled. "
    f"Please enable at least {MIN_FOODS_FOR_GENERATION} foods."
)
ERROR_NO_SOLUTION = (
    "No solution found. Try:\n"
    "- Enabling more foods\n"
    "- Relaxing nutritional constraints\n"
    "- Disabling some axioms"
)
ERROR_GENERATION_PREFIX = "Error during generation: "


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================

class DietService:
    """
    Service for generating personalized diet plans.

    Coordinates data flow between frontend and backend, handling:
    - Loading the food database
    - Validating user inputs
    - Transforming data for the solver
    - Error handling and response formatting

    Attributes:
        _csv_path: Path to the food database CSV file
        _food_data: Cache of foods loaded from the database

    Example:
        >>> service = DietService()
        >>> foods = service.load_foods()
        >>> request = build_diet_request(user_selections)
        >>> response = service.generate(request)
        >>> if response.success:
        ...     print(f"Total cost: €{response.total_cost}")
    """

    def __init__(self, csv_path: str = DEFAULT_CSV_PATH) -> None:
        """
        Initializes the service with the path to the food database.

        Args:
            csv_path: Path to the CSV file containing the food database.
                      Default: "data/food_db.csv"
        """
        self._csv_path = csv_path
        self._food_data: List[FoodItem] = []

    # -------------------------------------------------------------------------
    # PUBLIC METHODS - FOOD DATABASE MANAGEMENT
    # -------------------------------------------------------------------------

    def load_foods(self, include_non_selectable: bool = False) -> List[FoodItem]:
        """
        Loads foods from the CSV database.

        Reads the CSV file specified in the constructor and populates the
        internal food cache. This operation should be performed once at
        application startup.

        Args:
            include_non_selectable: If True, also includes foods with
                                    selectable=False (useful for the GUI)

        Returns:
            List of FoodItem objects containing the available foods

        Note:
            The result is also cached internally and can be retrieved later
            with get_foods() without re-reading the file.
        """
        if include_non_selectable:
            self._food_data = load_all_visible_foods(self._csv_path)
        else:
            self._food_data = load_food_data(self._csv_path)
        return self._food_data

    def get_foods(self) -> List[FoodItem]:
        """
        Returns the previously loaded foods.

        Useful for accessing the database without reloading the CSV file.
        If load_foods() has not been called yet, returns an empty list.

        Returns:
            List of loaded FoodItem objects, or empty list if not yet loaded
        """
        return self._food_data

    # -------------------------------------------------------------------------
    # PUBLIC METHODS - DIET GENERATION
    # -------------------------------------------------------------------------

    def generate(self, request: DietRequest) -> DietResponse:
        """
        Generates a diet plan based on the user request.

        Runs the complete generation flow:
        1. Validates the request (nutritional targets, selections, objective)
        2. Builds the list of enabled foods with custom portions
        3. Verifies there are enough foods to generate a diet
        4. Invokes the solver for optimization
        5. Formats and returns the result

        Args:
            request: Full request containing nutritional targets,
                     food selections, preferences and axiom configuration

        Returns:
            DietResponse containing:
            - success=True with plan and cost if a solution was found
            - success=False with error message if generation failed

        Note:
            All errors are handled internally and returned as
            DietResponse with success=False, never as exceptions.
        """
        # Step 1: Validate GUI input
        validation_response = self._validate_input(request)
        if validation_response is not None:
            return validation_response

        # Step 2: Build food list with custom portions
        enabled_food_items = self._build_enabled_food_items(request.food_selections)

        # Step 3: Check minimum number of foods
        if len(enabled_food_items) < MIN_FOODS_FOR_GENERATION:
            return DietResponse(success=False, error_message=ERROR_TOO_FEW_FOODS)

        # Step 4: Invoke the solver
        return self._invoke_solver(request, enabled_food_items)

    # -------------------------------------------------------------------------
    # PRIVATE METHODS - VALIDATION
    # -------------------------------------------------------------------------

    def _validate_input(self, request: DietRequest) -> Optional[DietResponse]:
        """
        Validates the request and returns an error response if invalid.

        Uses centralized validators to verify that all request parameters
        are within acceptable ranges.

        Args:
            request: The request to validate

        Returns:
            DietResponse with error if validation failed, None if valid
        """
        is_valid, validation_errors = validate_request(request)

        if not is_valid:
            formatted_errors = self._format_validation_errors(validation_errors)
            return DietResponse(success=False, error_message=formatted_errors)

        return None

    def _format_validation_errors(self, errors: List[str]) -> str:
        """
        Formats the list of validation errors into a readable message.

        Args:
            errors: List of individual error messages

        Returns:
            Formatted string with all errors listed
        """
        error_lines = [f"- {error}" for error in errors]
        return ERROR_VALIDATION_PREFIX + "\n".join(error_lines)

    # -------------------------------------------------------------------------
    # PRIVATE METHODS - DATA TRANSFORMATION
    # -------------------------------------------------------------------------

    def _build_enabled_food_items(
        self, selections: List[FoodSelection]
    ) -> List[FoodItem]:
        """
        Builds the list of enabled FoodItems from user selections.

        For each food item selected and enabled by the user, creates a new
        FoodItem with custom portions while preserving all other attributes
        (nutritional values, tags, price) from the original.

        Args:
            selections: List of user selections from the GUI, containing
                        enabled state and custom portion range

        Returns:
            List of FoodItems ready for the solver, containing only enabled
            foods with portions updated according to user preferences
        """
        food_lookup_by_id = self._create_food_lookup_map()
        enabled_foods = []

        for selection in selections:
            if not selection.enabled:
                continue

            food_item = self._create_food_item_from_selection(
                selection, food_lookup_by_id
            )
            if food_item is not None:
                enabled_foods.append(food_item)

        return enabled_foods

    def _create_food_lookup_map(self) -> Dict[int, FoodItem]:
        """
        Creates a lookup map for fast food access by ID.

        Returns:
            Dictionary {food_id: FoodItem} for all loaded foods
        """
        return {food.id: food for food in self._food_data}

    def _create_food_item_from_selection(
        self,
        selection: FoodSelection,
        food_lookup: Dict[int, FoodItem]
    ) -> Optional[FoodItem]:
        """
        Creates a FoodItem with custom portions from a user selection.

        Retrieves the original food from the database and creates a copy with
        min/max portions updated according to the user selection.

        Args:
            selection: User selection containing food_id and portion range
            food_lookup: Lookup map {id: FoodItem} for fast retrieval

        Returns:
            New FoodItem with custom portions, or None if the original food
            does not exist in the database
        """
        original_food = food_lookup.get(selection.food_id)

        if original_food is None:
            return None

        return FoodItem(
            id=original_food.id,
            name=original_food.name,
            kcal_100g=original_food.kcal_100g,
            prot_100g=original_food.prot_100g,
            carb_100g=original_food.carb_100g,
            fat_100g=original_food.fat_100g,
            portion_min=selection.portion_min,
            portion_max=selection.portion_max,
            tags=original_food.tags,
            price=original_food.price,
        )

    # -------------------------------------------------------------------------
    # PRIVATE METHODS - SOLVER INVOCATION
    # -------------------------------------------------------------------------

    def _invoke_solver(
        self,
        request: DietRequest,
        food_items: List[FoodItem]
    ) -> DietResponse:
        """
        Invokes the backend solver to generate the diet plan.

        Prepares parameters and calls generate_diet_plan(), handling
        both the success case and any errors or absence of solution.

        Args:
            request: Original request with all parameters
            food_items: List of enabled foods already processed

        Returns:
            DietResponse with the optimization result
        """
        try:
            plan, total_cost = generate_diet_plan(
                food_data=food_items,
                objective=request.objective,
                preferences=request.preferences,
                nutrition_targets=request.nutrition_targets.to_dict(),
                axioms_config=self._get_axioms_config_or_none(request),
            )

            return self._build_solver_response(plan, total_cost)

        except Exception as error:
            return self._build_error_response(error)

    def _get_axioms_config_or_none(self, request: DietRequest) -> Optional[dict]:
        """
        Extracts the axiom configuration from the request if present.

        Args:
            request: The request containing the configuration

        Returns:
            Axiom configuration dictionary, or None if not configured
        """
        if request.axioms_config:
            return request.get_axioms_dict()
        return None

    def _build_solver_response(
        self,
        plan: Optional[dict],
        total_cost: float
    ) -> DietResponse:
        """
        Builds the response from the solver result.

        Args:
            plan: Generated diet plan, or None if no solution found
            total_cost: Total cost calculated by the solver

        Returns:
            Successful DietResponse with plan, or error response if no solution
        """
        if plan is None:
            return DietResponse(success=False, error_message=ERROR_NO_SOLUTION)

        return DietResponse(
            success=True,
            plan=plan,
            total_cost=round(total_cost, 2),
        )

    def _build_error_response(self, error: Exception) -> DietResponse:
        """
        Builds an error response from an exception.

        Args:
            error: The exception caught during generation

        Returns:
            DietResponse with formatted error message
        """
        return DietResponse(
            success=False,
            error_message=f"{ERROR_GENERATION_PREFIX}{str(error)}"
        )
