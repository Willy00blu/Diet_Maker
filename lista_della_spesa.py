"""
Shopping list generator from a diet plan.

Example output structure:
{
    "carne": {
        "Chicken Breast": 450,
        "Beef Steak": 300
    },
    "carbo_salati": {
        "Basmati Rice": 700,
        "Whole Wheat Pasta": 200
    },
    "verdure": {
        "Zucchini": 600
    }
}
"""

# Maps internal tag names to user-friendly English category names
TAG_TO_CATEGORY_LABEL = {
    "carne":        "Meat",
    "pesce":        "Fish",
    "legumi":       "Legumes",
    "uova":         "Eggs",
    "latte_dolce":  "Dairy (Sweet)",
    "latte_salato": "Dairy (Savory)",
    "carbo_salati": "Carbohydrates",
    "carbo_dolci":  "Carbohydrates",
    "grassi":       "Fats",
    "verdure":      "Vegetables",
    "frutta":       "Fruit",
    "alimento_jolly": "Other",
}


def generate_shopping_list(diet, food_data):
    """
    Generates a shopping list grouped by food category.

    Args:
        diet: dict with meal plan {day: {meal: [(food, qty), ...]}}
        food_data: list of FoodItem

    Returns:
        dict {category_label: {food_name: total_grams}}
    """
    tag_map = {}
    for item in food_data:
        category_label = "Other"
        for tag in item.tags:
            if tag in TAG_TO_CATEGORY_LABEL:
                category_label = TAG_TO_CATEGORY_LABEL[tag]
                break
        tag_map[item.name] = category_label

    shopping_list = {}

    for day, meals in diet.items():
        for meal, foods in meals.items():
            for food_name, qty in foods:
                category = tag_map.get(food_name, "Other")
                if category not in shopping_list:
                    shopping_list[category] = {}
                shopping_list[category][food_name] = (
                    shopping_list[category].get(food_name, 0) + qty
                )

    return shopping_list


def print_shopping_list(diet, food_data):
    """Prints the shopping list to the terminal (CLI use)."""
    shopping_list = generate_shopping_list(diet, food_data)

    print("\n" + "=" * 50)
    print("WEEKLY SHOPPING LIST (BY CATEGORY)")
    print("=" * 50)

    for category in sorted(shopping_list.keys()):
        print(f"\n{category.upper()}")
        for food_name in sorted(shopping_list[category].keys()):
            qty = round(shopping_list[category][food_name])
            print(f"   • {food_name}: {qty}g")


# Backwards-compat aliases used by older imports
genera_lista_spesa = generate_shopping_list
stampa_lista_spesa = print_shopping_list
