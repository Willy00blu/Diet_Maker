"""
Food data loading module.

Loads the CSV food database and transforms rows into FoodItem objects
usable by the optimization solver.
"""

import pandas as pd
from typing import List, Tuple
from backend.core.definitions import FoodItem
from backend.config.food import FOODS_CONFIG


def load_food_database(file_path: str, include_non_selectable: bool = False) -> List[FoodItem]:
    """
    Loads the CSV database and transforms each row into a FoodItem object.

    Filters foods based on configuration in FOODS_CONFIG:
    - enabled=False: food completely excluded (not visible)
    - selectable=False: food visible but not selectable by the solver

    Args:
        file_path: Path to the food database CSV file
        include_non_selectable: If True, also includes foods with selectable=False
                                (useful for the UI which must display all of them)

    Returns:
        List of FoodItem objects ready for optimization
    """
    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()

        food_list = []
        disabled_count = 0
        non_selectable_count = 0

        for _, row in df.iterrows():
            food_id = str(int(row['id']))
            food_config = FOODS_CONFIG.get(food_id, {})

            # Check if the food is enabled (visible)
            if not food_config.get("enabled", True):
                disabled_count += 1
                continue

            # Check if the food is selectable by the solver
            is_selectable = food_config.get("selectable", True)
            if not is_selectable and not include_non_selectable:
                non_selectable_count += 1
                continue

            # Tag parsing
            raw_tags = str(row['tags'])
            separator = ';' if ';' in raw_tags else ','
            tags_list = [t.strip() for t in raw_tags.split(separator)]

            item = FoodItem(
                id=int(row['id']),
                name=str(row['name']),
                kcal_100g=float(row['kcal_100g']),
                prot_100g=float(row['prot_100g']),
                carb_100g=float(row['carb_100g']),
                fat_100g=float(row['fat_100g']),
                portion_min=float(row['portion_min']),
                portion_max=float(row['portion_max']),
                tags=tags_list,
                price=float(row['price'])
            )
            food_list.append(item)

        # Loading log
        msg = f"Food set F loaded: {len(food_list)} items"
        exclusions = []
        if disabled_count > 0:
            exclusions.append(f"{disabled_count} disabled")
        if non_selectable_count > 0:
            exclusions.append(f"{non_selectable_count} non-selectable")
        if exclusions:
            msg += f" ({', '.join(exclusions)})"
        print(msg)

        return food_list

    except Exception as e:
        print(f"Error loading food database: {e}")
        return []


def load_all_visible_foods(file_path: str) -> List[FoodItem]:
    """
    Loads all visible foods (enabled=True), including non-selectable ones.

    Useful for the UI which must display all available foods,
    including those the solver cannot select automatically.

    Args:
        file_path: Path to the food database CSV file

    Returns:
        List of all visible food items
    """
    return load_food_database(file_path, include_non_selectable=True)


def is_food_selectable(food_id: int) -> bool:
    """
    Checks whether a food item can be selected by the solver.

    Args:
        food_id: Food item ID

    Returns:
        True if the food is selectable, False otherwise
    """
    food_config = FOODS_CONFIG.get(str(food_id), {})
    return food_config.get("selectable", True)


# Alias for pipeline compatibility
load_food_data = load_food_database
