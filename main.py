"""
CLI entry point for the diet optimization system.
Uses the pipeline to separate logic from presentation.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lista_della_spesa import print_shopping_list
from pipeline import DietService, DietRequest, NutritionTargets
from backend.config.objectives import OBJECTIVES_CONFIG


def main():
    db_path = os.path.join("data", "food_db.csv")

    if not os.path.exists(db_path):
        print(f"Error: file {db_path} not found.")
        print(f"Looked in: {os.path.abspath(db_path)}")
        return

    print("--- DIET OPTIMIZATION SYSTEM ---")

    enabled_objectives = {k: v for k, v in OBJECTIVES_CONFIG.items() if v.get("enabled", True)}
    objective_keys = list(enabled_objectives.keys())

    default_objective = next(
        (k for k, v in enabled_objectives.items() if v.get("default", False)),
        objective_keys[0]
    )
    default_idx = objective_keys.index(default_objective) + 1

    print("\nSelect optimization objective:")
    for i, (key, obj) in enumerate(enabled_objectives.items(), 1):
        marker = " (default)" if obj.get("default", False) else ""
        print(f"  {i}. {key:12} - {obj['description']}{marker}")

    choice = input(f"\nChoice [1-{len(objective_keys)}] (default: {default_idx}): ").strip()

    try:
        idx = int(choice) - 1
        objective = objective_keys[idx] if 0 <= idx < len(objective_keys) else default_objective
    except (ValueError, IndexError):
        objective = default_objective

    print(f"\nSelected objective: {objective.upper()}")

    print("\n[1/3] Loading food database...")
    service = DietService(csv_path=db_path)
    food_data = service.load_foods()

    if not food_data:
        print("Loading failed: food_data is empty.")
        return

    from pipeline.contracts import FoodSelection

    food_selections = [
        FoodSelection(
            food_id=f.id,
            name=f.name,
            enabled=True,
            rating=3,
            portion_min=f.portion_min,
            portion_max=f.portion_max,
        )
        for f in food_data
    ]

    request = DietRequest(
        food_selections=food_selections,
        preferences={f.name: 3 for f in food_data},
        nutrition_targets=NutritionTargets(),
        objective=objective,
    )

    print("\n[2/3] Running optimizer...")
    response = service.generate(request)

    if response.success:
        diet_plan = response.plan
        total_cost = response.total_cost

        print("\n[3/3] Processing output...")
        print("\n" + "=" * 50)
        print("GENERATED WEEKLY MEAL PLAN")
        print("=" * 50)

        for day, slots in diet_plan.items():
            print(f"\n{day.upper()}")
            for slot, foods in slots.items():
                if foods:
                    foods_str = ", ".join(f"{name} ({qty}g)" for name, qty in foods)
                else:
                    foods_str = "EMPTY"
                print(f"   {slot:12}: {foods_str}")

        print_shopping_list(diet_plan, food_data)

        print("\n" + "=" * 50)
        print(f"ESTIMATED TOTAL COST: EUR {total_cost:.2f}")
        print("=" * 50)
    else:
        print(f"\nNo solution found: {response.error_message}")
        print("Check whether targets are too strict for the current food database.")


if __name__ == "__main__":
    main()
