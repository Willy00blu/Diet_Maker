# Axioma — Diet Solver

**Live app:** [dietmaker-gsdlqnfz4rb4dcuq4fzftx.streamlit.app](https://dietmaker-gsdlqnfz4rb4dcuq4fzftx.streamlit.app/)

A Streamlit application that generates personalized weekly meal plans using **Mixed Integer Linear Programming (MILP)**. The solver respects nutritional targets, meal composition rules, food frequency constraints, and optional chrono-nutrition principles — all configurable from the GUI without touching any code.

---

## Table of Contents

1. [Requirements & Setup](#1-requirements--setup)
2. [Project Structure](#2-project-structure)
3. [How to Run](#3-how-to-run)
4. [Streamlit Interface](#4-streamlit-interface)
   - [Sidebar — Logic & Targets](#41-sidebar--logic--targets)
   - [Food Matrix](#42-food-matrix)
   - [Results & Shopping List](#43-results--shopping-list)
5. [The Solver Pipeline](#5-the-solver-pipeline)
6. [MILP Formulation](#6-milp-formulation)
7. [The Tag System](#7-the-tag-system)
8. [Axiom Reference](#8-axiom-reference)
   - [Meal Composition (meal_validity)](#81-meal-composition-meal_validity)
   - [Daily Frequency (daily_frequency)](#82-daily-frequency-daily_frequency)
   - [Diet Frequency (diet_frequency)](#83-diet-frequency-diet_frequency)
   - [Nutrition (nutrition)](#84-nutrition-nutrition)
   - [Sport Nutrition (sport_nutrition)](#85-sport-nutrition-sport_nutrition)
9. [Optimization Objectives](#9-optimization-objectives)
10. [Food Database Format](#10-food-database-format)
11. [Configuration Files](#11-configuration-files)
12. [Extending the System](#12-extending-the-system)

---

## 1. Requirements & Setup

**Python version:** 3.11+

**Dependencies:**
```
streamlit
pulp
pandas
```

Install them with:
```bash
pip install streamlit pulp pandas
```

The CBC solver (used by PuLP) is bundled with PuLP and requires no separate installation.

---

## 2. Project Structure

```
Progetto_dieta/
│
├── frontend/                        # Streamlit GUI
│   ├── app.py                       # Entry point: orchestrates all UI + pipeline
│   ├── state.py                     # session_state initialization
│   ├── styles.py                    # Custom CSS
│   └── components/
│       ├── sidebar.py               # Axiom toggles, targets, objective, generate button
│       ├── food_matrix.py           # Food selection grid (enable/portions/rating)
│       └── results.py               # Diet plan display + shopping list
│
├── backend/
│   ├── optimizer.py                 # Core: builds and solves the MILP problem
│   ├── data_loader.py               # Loads food_db.csv -> list[FoodItem]
│   ├── core/
│   │   ├── definitions.py           # FoodItem dataclass, TAGS dict, SLOTS, DAYS_NAMES
│   │   ├── objective_functions.py   # minimize_cost, maximize_preference
│   │   └── axioms/
│   │       ├── meal_validity.py     # Breakfast/Lunch/Snack/Dinner composition
│   │       ├── daily_frequency.py   # Vegetables, fruit, daily anti-repetition
│   │       ├── diet_frequency.py    # Meat/fish/legumes, weekly variety, meal prep
│   │       ├── nutrition.py         # Daily kcal + macro targets, meal distribution
│   │       └── nutrizione_sportiva.py  # Chrono-nutrition (carb/protein/fat timing)
│   └── config/
│       ├── axioms.py                # AXIOMS_CONFIG: default values for all axioms
│       ├── nutrition.py             # N_DAYS, TARGET_KCAL, PCT_*, DELTA_*
│       ├── food.py                  # FOODS_CONFIG: per-food enabled/preference defaults
│       ├── objectives.py            # OBJECTIVES_CONFIG, SOLVER_CONFIG (timeout, gap)
│       └── constants.py             # All shared numeric constants
│
├── pipeline/
│   ├── contracts.py                 # DietRequest, DietResponse, NutritionTargets, etc.
│   ├── diet_service.py              # DietService: frontend <-> backend bridge
│   ├── validators.py                # Input validation before solving
│   └── __init__.py                  # Public exports
│
├── data/
│   └── food_db.csv                  # Food database (69 items)
│
├── lista_della_spesa.py             # Shopping list aggregation utility
└── test_solver.py                   # 33-scenario automated test suite
```

---

## 3. How to Run

From the project root:
```bash
streamlit run frontend/app.py
```

The app opens in the browser at `http://localhost:8501`.

---

## 4. Streamlit Interface

### 4.1 Sidebar — Logic & Targets

The sidebar is the main control panel. It is divided into four areas:

#### Generate Button
At the top of the sidebar. Disabled when the macro split does not sum to 100%. Clicking it triggers diet generation.

#### Meal Composition (Axioms)
Five collapsible expanders — one per axiom group — each containing toggle switches and a gear icon (`⚙️`) that opens a parameter popover for fine-tuning. Full details in the [Axiom Reference](#8-axiom-reference) section.

#### Optimization Objective
A radio button to choose the solver's optimization strategy:

| Option | Description |
|--------|-------------|
| **Quick Solution** | Find any valid plan (fastest, no optimization) |
| **Minimize Cost** | Find the cheapest plan that satisfies all constraints |
| **Maximize Preferences** | Prioritize foods with higher star ratings |

#### Daily Targets
All nutritional parameters the solver must satisfy:

| Parameter | Default | Description |
|-----------|---------|-------------|
| **Duration (Days)** | 5 | Number of days to plan (1–7) |
| **Energy (kcal)** | 2000 | Daily calorie target |
| **Protein %** | 20 | Percentage of daily kcal from protein |
| **Carbohydrates %** | 55 | Percentage of daily kcal from carbohydrates |
| **Fat %** | 25 | Percentage of daily kcal from fat |
| **Calorie tolerance ±%** | 10 | Allowed deviation on the daily kcal target |
| **Macro tolerance ±%** | 10 | Allowed deviation on each macronutrient target |

The three macro sliders must sum to exactly 100% — otherwise the generate button is disabled and a warning is shown.

**How tolerances work:** If the target is 2000 kcal with a 10% tolerance, the solver accepts any plan between 1800 and 2200 kcal per day. A 50% macro tolerance gives the solver much more flexibility and usually leads to faster solutions.

---

### 4.2 Food Matrix

A collapsible panel (`Food Database & Matrix`) showing all 69 foods in the database, grouped by category (Carbohydrates, Proteins, Vegetables, Fruit, Fats) and sorted alphabetically within each group.

Each row has four columns:

| Column | Control | Description |
|--------|---------|-------------|
| **Sel** | Checkbox | Enables/disables the food for the solver. Unchecked foods are completely ignored. |
| **Ingredient** | Static label | Food name and primary tag |
| **Min/Max Portion (g)** | Range slider | Minimum and maximum grams per serving. The solver picks a quantity within this range when the food is selected. |
| **Enjoyment Rating** | Star feedback (1–5) | User preference. Used by the "Maximize Preferences" objective. |

**Portion slider steps:**
- Foods with `portion_min < 50g` (oils, butter, nuts) use a 5g step, max 100g
- All other foods use a 10g step, max 500g

**Minimum active foods:** The solver requires at least 10 enabled foods to attempt generation.

---

### 4.3 Results & Shopping List

After a successful generation, two sections appear below the food matrix:

**Generated Meal Plan** — One expander per day. Each day shows four meals (Breakfast, Lunch, Snack, Dinner) with food names and gram quantities, e.g.:
```
Monday
  Breakfast: Greek Yogurt (150g), Muesli (50g), Walnuts (15g)
  Lunch: Chicken Breast (150g), Brown Rice (80g), Broccoli (200g), Olive Oil (10g)
  Snack: Apple (150g)
  Dinner: Salmon (130g), Whole Wheat Pasta (80g), Zucchini (200g), Olive Oil (10g)
```
An estimated total cost (EUR) is shown at the bottom.

**Shopping List** — All foods aggregated across the entire diet period, grouped by category (Carbohydrates, Proteins, Vegetables, Fruit, Fats, Other) and displayed in three columns. Quantities shown in grams.

---

## 5. The Solver Pipeline

Generation follows a strict sequence:

```
GUI (Streamlit)
    |
    | DietRequest (food selections, nutrition targets, axiom config, objective)
    v
DietService.generate()
    |
    |-- validate_request() --> returns error if invalid
    |-- build enabled FoodItem list (with custom portions)
    |-- check >= 10 enabled foods
    |
    v
generate_diet_plan() [backend/optimizer.py]
    |
    |-- Create MILP problem (PuLP / CBC)
    |-- Create decision variables
    |-- Apply semi-continuity constraints
    |-- Apply diet frequency axioms (global, across all days)
    |-- For each day:
    |       Apply meal validity axioms
    |       Apply daily frequency axioms
    |       Apply nutrition axioms
    |       Apply sport nutrition axioms
    |-- Set objective function
    |-- Solve (CBC, timeout=60s, gap=10%)
    |
    v
DietResponse (success=True/False, plan, total_cost, error_message)
    |
    v
GUI renders results
```

**Data contracts** (`pipeline/contracts.py`):
- `DietRequest` — carries all user inputs from the GUI to the service
- `DietResponse` — carries the result (or error) back to the GUI
- `NutritionTargets` — typed container for kcal, macro percentages, tolerances, n_days
- `FoodSelection` — per-food enabled flag, rating, custom portions
- `AxiomConfig` — per-axiom enabled flag + parameters dict

---

## 6. MILP Formulation

The solver uses **Mixed Integer Linear Programming** via [PuLP](https://coin-or.github.io/pulp/) with the open-source **CBC** solver.

### Decision Variables

For each combination of `(food_id, day, slot)`:

| Variable | Type | Domain | Meaning |
|----------|------|--------|---------|
| `is_selected[f, d, s]` | Binary | {0, 1} | 1 if food `f` is included in meal `s` on day `d` |
| `quantity_grams[f, d, s]` | Continuous | [0, +inf) | Grams of food `f` in meal `s` on day `d` |

With 69 foods × 7 days × 4 slots = **1932 binary + 1932 continuous variables** at maximum.

### Semi-Continuity Constraints

These constraints link the two variable types. If a food is not selected, its quantity must be zero. If it is selected, the quantity must be within the user-defined portion range:

```
quantity[f,d,s] >= is_selected[f,d,s] * portion_min[f]
quantity[f,d,s] <= is_selected[f,d,s] * portion_max[f]
```

This prevents the solver from assigning 0.001g of a food (technically "selected" but nutritionally meaningless).

### Objective Functions

| Objective | Expression |
|-----------|-----------|
| `cost` | Minimize `sum( price_per_100g[f] / 100 * quantity_grams[f,d,s] )` for all `f,d,s` |
| `preference` | Maximize `sum( rating[f] * is_selected[f,d,s] )` for all `f,d,s` |
| `none` | `0` (feasibility only — fastest) |

### Solver Settings

Configured in `backend/config/objectives.py`:

| Setting | Value | Description |
|---------|-------|-------------|
| `timeout` | 60 s | Maximum time before CBC returns best-found solution |
| `gap_rel` | 0.10 | Stop when within 10% of the optimal bound |
| `msg` | 0 | Silent output |

---

## 7. The Tag System

Every food item carries one or more **tags** that determine:
1. Its nutritional category (protein source, carbohydrate, fat, etc.)
2. Which meal slots it may appear in

### Tag Structure

```
TAGS[CATEGORY][SUBCATEGORY][KEY]
```

Where `KEY` is:
- `ROOT` — general category tag (e.g. `"carne"`)
- `COL` — allowed at Breakfast (e.g. `"carne_col"`)
- `PRA` — allowed at Lunch (e.g. `"carne_pra"`)
- `SNA` — allowed at Snack (e.g. `"carne_sna"`)
- `CEN` — allowed at Dinner (e.g. `"carne_cen"`)

### Complete Tag Map

| Category | Subcategory | ROOT tag | Slot tags |
|----------|-------------|----------|-----------|
| Proteins | Meat | `carne` | `carne_col`, `carne_pra`, `carne_sna`, `carne_cen` |
| Proteins | Fish | `pesce` | `pesce_col`, `pesce_pra`, `pesce_sna`, `pesce_cen` |
| Proteins | Legumes | `legumi` | `legumi_col`, `legumi_pra`, `legumi_sna`, `legumi_cen` |
| Proteins | Eggs | `uova` | `uova_col`, `uova_pra`, `uova_sna`, `uova_cen` |
| Proteins | Sweet dairy | `latte_dolce` | `latte_dolce_col`, `latte_dolce_pra`, `latte_dolce_sna`, `latte_dolce_cen` |
| Proteins | Savory dairy | `latte_salato` | `latte_salato_col`, `latte_salato_pra`, `latte_salato_sna`, `latte_salato_cen` |
| Carbohydrates | Savory complex | `carbo_salati` | `carbo_salati_col`, `carbo_salati_pra`, `carbo_salati_sna`, `carbo_salati_cen` |
| Carbohydrates | Sweet breakfast | `carbo_dolci` | `carbo_dolci_col`, `carbo_dolci_pra`, `carbo_dolci_sna`, `carbo_dolci_cen` |
| Fats | Pure fats | `grassi` | `grassi_col`, `grassi_pra`, `grassi_sna`, `grassi_cen` |
| Others | Vegetables | `verdure` | `verdure_col`, `verdure_pra`, `verdure_sna`, `verdure_cen` |
| Others | Fruit | `frutta` | `frutta_col`, `frutta_pra`, `frutta_sna`, `frutta_cen` |
| Technical | Jolly | `alimento_jolly` | — (no slot suffix) |

### The Jolly Tag

Foods tagged `alimento_jolly` (e.g. Greek Yogurt, olive oil, egg whites) are exempt from anti-repetition constraints. They can appear multiple times per day and many times per diet without triggering variety limits. This models condiments and base ingredients that are naturally used frequently.

### How Meal Validity Axioms Use Tags

When the breakfast axiom runs for a given day, it:
1. Forces to zero all `is_selected` variables for foods that do not have any `*_col` tag
2. Collects `is_selected` variables for each allowed food group (sweet proteins, savory carbs, etc.)
3. Applies count constraints (exact / min-max) on the resulting sums

This means a food only participates in the constraint for the slot it is tagged for. A chicken breast tagged only `carne_pra` and `carne_cen` is automatically excluded from Breakfast and Snack, even if it is enabled by the user.

---

## 8. Axiom Reference

Axioms are MILP constraints. Each axiom can be **toggled on/off** from the sidebar. Most have **tunable parameters** accessible via the gear icon popover.

The axioms are organized into five groups, applied at different logical levels:

| Group | Level | Scope |
|-------|-------|-------|
| `meal_validity` | Micro-logic | Single meal |
| `daily_frequency` | Meso-logic | Single day |
| `diet_frequency` | Macro-logic | Entire diet period |
| `nutrition` | — | Single day (quantities) |
| `sport_nutrition` | — | Single day (quantities, per slot) |

---

### 8.1 Meal Composition (`meal_validity`)

Defines the required structure of each meal. When a meal is **disabled**, its slot is forced entirely empty — no food can appear in it — and all other axioms that reference that slot automatically skip it.

#### Breakfast

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `proteine` | `{"exact": N}` | `{"exact": 1}` | Required number of protein items (sweet or savory dairy, eggs) |
| `carboidrati` | `{"exact": N}` | `{"exact": 1}` | Required number of carbohydrate items |
| `grassi` | `{"min": N, "max": M}` | `{"min": 0, "max": 1}` | Allowed fat items |
| `frutta` | `{"min": N, "max": M}` | `{"min": 0, "max": 1}` | Allowed fruit items |
| `xor_dolce_salato` | boolean | `true` | Prevents mixing sweet and savory: if a sweet protein is chosen (yogurt), a savory carb (whole wheat bread) is forbidden and vice versa. Encoded as two linear constraints: `sweet_protein + savory_carb <= 1` and `savory_protein + sweet_carb <= 1`. |

Allowed food types at Breakfast: sweet dairy, savory dairy, eggs, meat (rare), fish (rare), sweet carbs (cereals/muesli), savory carbs (whole wheat bread), fats, fruit.

#### Lunch

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `proteine` | `{"exact": N}` | `{"exact": 1}` | Exactly N protein items (meat, fish, eggs, legumes, savory dairy) |
| `carboidrati` | `{"exact": N}` | `{"exact": 1}` | Exactly N savory carb items (pasta, rice, bread, potatoes) |
| `verdure` | `{"exact": N}` | `{"exact": 1}` | Exactly N vegetable items |
| `grassi` | `{"exact": N}` | `{"exact": 1}` | Exactly N fat items (dressing/condiment) |
| `frutta` | `{"min": N, "max": M}` | `{"min": 0, "max": 1}` | Optional fruit |

Lunch is always savory — no XOR constraint needed.

#### Snack

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `proteine` | `{"min": N, "max": M}` | `{"min": 0, "max": 1}` | Optional protein item |
| `carboidrati` | `{"min": N, "max": M}` | `{"min": 0, "max": 1}` | Optional carb item |
| `grassi` | `{"min": N, "max": M}` | `{"min": 0, "max": 1}` | Optional fat item |
| `frutta` | `{"min": N, "max": M}` | `{"min": 0, "max": 1}` | Optional fruit item |
| `min_totale` | integer | `1` | The snack must contain at least this many items total (cannot be empty) |
| `xor_dolce_salato` | boolean | `true` | Same sweet/savory XOR as breakfast |

#### Dinner

Identical structure to Lunch (same parameters, same defaults). Uses `*_cen` slot tags.

---

### 8.2 Daily Frequency (`daily_frequency`)

Controls how often certain food groups appear within a **single day**, summed across all four meal slots.

#### Daily Vegetables (`daily_vegetables`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min` | 1 | Minimum vegetable servings per day |
| `max` | 2 | Maximum vegetable servings per day |

The minimum constraint is automatically skipped if both Lunch and Dinner are disabled, since vegetables only appear in those slots in the current database.

#### Daily Fruit (`daily_fruit`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min` | 0 | Minimum fruit servings per day (0 = fruit is optional) |
| `max` | 1 | Maximum fruit servings per day |

The minimum constraint is only added to the problem when `min > 0`.

#### Daily Variety (`daily_variety`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_per_food` | 1 | Each food can appear at most this many times on the same day |

Foods tagged `alimento_jolly` are exempt. Setting `max_per_food = 2` allows the same food at two different meals on the same day (e.g. olive oil at both lunch and dinner).

---

### 8.3 Diet Frequency (`diet_frequency`)

Controls how often certain food groups appear across the **entire diet period**.

#### Meat Limit (`diet_meat`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min` | 2 | Minimum meat servings over the whole diet |
| `max` | 4 | Maximum meat servings over the whole diet |

These limits span the full N_DAYS. For a 5-day diet, `min=2, max=4` means 2–4 meat meals total.

#### Fish Requirement (`diet_fish`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min` | 2 | Minimum fish servings over the whole diet |
| `max` | 4 | Maximum fish servings over the whole diet |

#### Legume Centrality (`diet_legumes`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min` | 2 | Minimum legume servings over the whole diet |
| `max` | 5 | Maximum legume servings over the whole diet |

#### Weekly Variety (`diet_variety`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_normal` | 3 | Maximum times any regular food appears across the entire diet |
| `max_jolly` | 14 | Maximum times a jolly food appears across the entire diet |

This is a key parameter for avoiding monotonous diets. With a 5-day diet and 4 meals/day = 20 total meal slots, `max_normal=3` means no single food dominates the plan. If you extend to 7 days, increase this to 4–5 to maintain feasibility.

**Interaction with Meal Prep:** `max_normal` and `meal_prep.min_if_used` must be compatible. If `min_if_used=4` and `max_normal=3`, the solver is infeasible because meal prep requires each used food to appear at least 4 times, but variety caps it at 3.

#### Meal Prep (`meal_prep`)

Applies to foods that require advance preparation: **meat, fish, legumes, savory carbohydrates**. Jolly foods are excluded.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_if_used` | 2 | If a food is used at all, it must appear at least this many times |
| `max_total` | 14 | Upper bound on appearances (also acts as Big-M coefficient) |

**Mathematical implementation** using a binary indicator variable `z[f]` per food:
```
sum(is_selected[f,d,s] for all d,s) <= max_total * z[f]    -- if z=0, food is not used
sum(is_selected[f,d,s] for all d,s) >= min_if_used * z[f]  -- if z=1, at least min_if_used
```

This models the real-world logic: it is not worth buying and cooking a food item for just one meal. Setting `min_if_used=1` effectively disables this constraint.

---

### 8.4 Nutrition (`nutrition`)

Applies to daily **quantities** (continuous variables) rather than selections.

#### Kcal / Macro Targets (`daily_nutrition`)

No parameters in the axiom config itself — targets come from the **Daily Targets** section of the sidebar.

For each day, the solver enforces:
```
target_kcal * (1 - delta_kcal) <= total_daily_kcal  <= target_kcal * (1 + delta_kcal)
target_prot * (1 - delta_macro) <= total_daily_prot <= target_prot * (1 + delta_macro)
target_carb * (1 - delta_macro) <= total_daily_carb <= target_carb * (1 + delta_macro)
target_fat  * (1 - delta_macro) <= total_daily_fat  <= target_fat  * (1 + delta_macro)
```

**Macro gram targets** are derived from the caloric percentages:
```
target_prot_g = (kcal * prot_pct/100) / 4    (protein: 4 kcal/g)
target_carb_g = (kcal * carb_pct/100) / 4    (carbs: 4 kcal/g)
target_fat_g  = (kcal * fat_pct/100)  / 9    (fat: 9 kcal/g)
```

**Active fraction scaling:** When a meal is disabled (e.g. Breakfast off), its slot is forced empty. The daily targets are automatically scaled down by the expected caloric contribution of the disabled slot (derived from the midpoints of the Meal Distribution ranges). This prevents the remaining meals from being forced to cover an impossible caloric target.

#### Meal Distribution (`meal_distribution`)

Enforces that each active meal contributes an appropriate fraction of the daily calorie target.

| Meal | Min % | Max % |
|------|-------|-------|
| Breakfast | 15% | 25% |
| Lunch | 35% | 40% |
| Snack | 5% | 10% |
| Dinner | 30% | 35% |

These are configurable from the sidebar popover (as decimal fractions: `0.35` = 35%).

Each slot's constraint uses the **original** `target_kcal` as the reference, meaning the bounds are absolute (e.g. lunch must provide between 700 and 800 kcal when target is 2000). Disabled slots are simply skipped.

---

### 8.5 Sport Nutrition (`sport_nutrition`)

Chrono-nutrition constraints that control the **temporal distribution of macronutrients** across the day. All parameters are decimal fractions in `[0.0, 1.0]` representing a percentage of the daily macro target.

#### Carb Timing (`chrono_carb`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `lunch_min_pct` | 0.35 | Lunch must provide at least 35% of the daily carbohydrate target |
| `dinner_max_pct` | 0.25 | Dinner must provide at most 25% of the daily carbohydrate target |
| `delta` | 0.05 | Flexibility margin subtracted/added to both constraints |

**Effective constraints:**
```
carbs_at_lunch  >= target_carb_g * (lunch_min_pct - delta)   = target_carb_g * 0.30
carbs_at_dinner <= target_carb_g * (dinner_max_pct + delta)  = target_carb_g * 0.30
```

The lunch minimum is skipped when Lunch is disabled.

**Rationale:** Carbohydrates provide quick energy. Loading them at lunch supports afternoon activity while reducing evening intake prevents excess energy storage before sleep.

#### Protein Timing (`chrono_protein`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_pct_per_meal` | 0.20 | Each main meal must provide at least 20% of the daily protein target |
| `delta` | 0.05 | Flexibility margin |

**Effective constraint** (applied to Breakfast, Lunch, Dinner — not Snack):
```
protein_at_meal >= target_prot_g * (min_pct_per_meal - delta)  = target_prot_g * 0.15
```

Only applied to active (non-disabled) meal slots.

**Rationale:** Distributing protein evenly across main meals maximizes muscle protein synthesis throughout the day.

#### Fat Timing (`chrono_fat`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `breakfast_min_pct` | 0.15 | Breakfast must provide at least 15% of the daily fat target |
| `max_pct_per_meal` | 0.35 | No single meal may exceed 35% of the daily fat target |
| `delta` | 0.05 | Flexibility margin |

**Effective constraints:**
```
fat_at_breakfast >= target_fat_g * (breakfast_min_pct - delta)  = target_fat_g * 0.10
fat_at_any_meal  <= target_fat_g * (max_pct_per_meal + delta)   = target_fat_g * 0.40
```

The breakfast minimum is skipped when Breakfast is disabled. The per-meal maximum applies to all four slots.

**Rationale:** Fat slows gastric emptying and provides prolonged satiety. A minimum at breakfast prevents mid-morning hunger; the per-meal cap avoids heavy, slow-digesting meals.

---

## 9. Optimization Objectives

### `none` — Quick Solution (default)

The objective function is set to zero: `problem += 0`. The CBC solver finds the first feasible solution it encounters. Always the fastest option. Use it when you just want a valid plan.

### `cost` — Minimize Cost

Minimizes the total grocery cost across the entire diet:
```
minimize: sum( price[f] / 100 * quantity_grams[f,d,s] )  for all f, d, s
```
`price[f]` is the price per 100g in EUR, stored in the food database. This objective requires more solver time (up to the 60s timeout) because it must explore more of the feasible region.

### `preference` — Maximize Preferences

Maximizes the total weighted selection score:
```
maximize: sum( rating[f] * is_selected[f,d,s] )  for all f, d, s
```
`rating[f]` is the 1–5 star rating assigned by the user in the food matrix. Since PuLP only supports minimization internally, this is converted to: `minimize: -sum(...)`. The solver favors 5-star foods and avoids 1-star foods when multiple valid combinations exist.

---

## 10. Food Database Format

Located at `data/food_db.csv`. Each row is one food item.

| Column | Type | Description |
|--------|------|-------------|
| `id` | integer | Unique identifier (used as MILP variable index) |
| `name` | string | Display name shown in the UI |
| `kcal_100g` | float | Calories per 100g |
| `prot_100g` | float | Protein grams per 100g |
| `carb_100g` | float | Carbohydrate grams per 100g |
| `fat_100g` | float | Fat grams per 100g |
| `portion_min` | float | Minimum portion size in grams |
| `portion_max` | float | Maximum portion size in grams |
| `tags` | string | Semicolon-separated tag list (e.g. `carne;carne_pra;carne_cen`) |
| `price` | float | Price per 100g in EUR |

**Example rows:**
```csv
id,name,kcal_100g,prot_100g,carb_100g,fat_100g,portion_min,portion_max,tags,price
1,Greek Yogurt,57,10,4,0,125,200,latte_dolce;latte_dolce_col;latte_dolce_sna;alimento_jolly,1.20
2,Whole Eggs,155,13,1,11,60,120,uova;uova_col;uova_cen,0.60
```

**Tag ordering convention:** The ROOT tag (e.g. `carne`) should appear before slot-specific tags (e.g. `carne_pra`). The code scans all tags and does not rely on position, but this ordering improves readability.

**Non-selectable foods:** Some foods have `"selectable": false` in `backend/config/food.py`. These appear in the food matrix unchecked by default. The user can still enable them manually by ticking the checkbox.

---

## 11. Configuration Files

### `backend/config/nutrition.py`

Default nutritional targets (used when the GUI is not present or targets are not set):

```python
N_DAYS       = 5       # Diet duration in days
TARGET_KCAL  = 2000    # Daily calorie target
PCT_PROT     = 0.20    # 20% protein
PCT_CARB     = 0.55    # 55% carbohydrates
PCT_FAT      = 0.25    # 25% fat
DELTA_KCAL   = 0.10    # ±10% calorie tolerance
DELTA_MACRO  = 0.10    # ±10% macro tolerance
```

### `backend/config/objectives.py`

CBC solver settings:
```python
SOLVER_CONFIG = {
    "timeout": 60,    # seconds before CBC returns best-found solution
    "gap_rel": 0.10,  # accept solution within 10% of proven optimum
    "msg": 0,         # 0 = silent, 1 = verbose CBC output
}
```

### `backend/config/food.py`

Per-food overrides. Uses food `id` as the string key:
```python
FOODS_CONFIG = {
    "1": {"preference": 4, "selectable": True},    # Greek Yogurt: rating 4 stars
    "5": {"preference": 3, "selectable": False},   # disabled by default
}
```
If a food is not listed here, its default rating is 3 and it is selectable.

### `backend/config/constants.py`

Single source of truth for all numeric constants:

| Constant | Value | Used for |
|----------|-------|---------|
| `KCAL_PER_GRAM_PROTEIN` | 4 | Macro gram calculations |
| `KCAL_PER_GRAM_CARBOHYDRATE` | 4 | Macro gram calculations |
| `KCAL_PER_GRAM_FAT` | 9 | Macro gram calculations |
| `MIN_DIET_DAYS` | 1 | Validation |
| `MAX_DIET_DAYS` | 7 | Validation |
| `MIN_DAILY_KCAL` | 1000 | Validation |
| `MAX_DAILY_KCAL` | 5000 | Validation |
| `MIN_ENABLED_FOODS` | 10 | Minimum active foods for generation |
| `PORTION_STEP_THRESHOLD` | 50g | Determines slider step |
| `PORTION_STEP_SMALL` | 5g | Slider step for small-portion foods |
| `PORTION_STEP_LARGE` | 10g | Slider step for standard foods |
| `PORTION_SLIDER_MAX_SMALL` | 100g | Max slider range for small-portion foods |
| `PORTION_SLIDER_MAX_LARGE` | 500g | Max slider range for standard foods |
| `DEFAULT_FOOD_RATING` | 3 | Default star rating |
| `AXIOM_PARAMETER_MAX_RANGE` | 15 | Max value for axiom range sliders |
| `MAX_MEAL_COMPONENTS` | 3 | Max value for meal composition sliders |

---

## 12. Extending the System

### Adding a new food

1. Add a row to `data/food_db.csv` with a unique `id`, nutritional values, portion range, and tags.
2. Assign the correct tags. Include the ROOT tag and the `*_col/pra/sna/cen` tags for each meal the food is appropriate for.
3. Optionally add an entry in `backend/config/food.py` to set a non-default rating or mark it as non-selectable by default.

### Adding a new axiom

1. Add the axiom definition to the appropriate section of `backend/config/axioms.py` (or create a new group).
2. Implement the constraint logic in the corresponding module under `backend/core/axioms/`.
3. Call the new function from `backend/optimizer.py` — either inside `_apply_daily_axioms` for per-day constraints, or at the top level for diet-wide constraints.
4. The sidebar will automatically render the new axiom's toggle and parameters because `sidebar.py` iterates over `AXIOMS_CONFIG` dynamically.

### Changing the solver timeout

Edit `SOLVER_CONFIG["timeout"]` in `backend/config/objectives.py`. Increase it if you frequently hit the timeout on complex configurations (7 days, tight tolerances, all axioms on). Decrease it for faster responses at the cost of solution quality.

### Running the test suite

```bash
python test_solver.py
```

33 scenarios covering: single-day diets, 7-day diets, disabled meal slots, extreme calorie targets, axiom contradictions, all three objective functions, and chrono-nutrition edge cases. Expected result: `33/33 as expected`.
