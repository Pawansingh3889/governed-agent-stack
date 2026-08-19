"""
Benchmark different OpenAI-compatible models on FloorMind SQL generation tasks.

Usage:
    python scripts/benchmark_models.py

Prerequisites:
    export OPENAI_API_KEY=sk-...
    python scripts/seed_demo_db.py

Compares accuracy, response time, and SQL quality across models.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from openai import OpenAI
from sqlalchemy import create_engine

from config import DATABASE_URL, OPENAI_API_KEY, OPENAI_BASE_URL

# Test questions with known correct SQL patterns
BENCHMARK_QUESTIONS = [
    {
        "question": "How much of Product A did we process this week?",
        "expected_tables": ["ProductionBatch", "Products"],
        "expected_pattern": "SELECT",
    },
    {
        "question": "Which product had the highest waste percentage last month?",
        "expected_tables": ["ProductionBatch", "Products"],
        "expected_pattern": "ORDER BY",
    },
    {
        "question": "Show me all temperature excursions above 5 degrees",
        "expected_tables": ["TemperatureLogs"],
        "expected_pattern": "WHERE",
    },
    {
        "question": "What is the total revenue from orders this month?",
        "expected_tables": ["SalesOrders"],
        "expected_pattern": "SUM",
    },
    {
        "question": "List employees who worked more than 48 hours this week",
        "expected_tables": ["Employees"],
        "expected_pattern": "WHERE",
    },
    {
        "question": "What is the yield percentage by product line?",
        "expected_tables": ["ProductionBatch"],
        "expected_pattern": "GROUP BY",
    },
    {
        "question": "Show raw materials expiring in the next 7 days",
        "expected_tables": ["RawMaterialIntake"],
        "expected_pattern": "WHERE",
    },
    {
        "question": "Compare production output between day and night shifts",
        "expected_tables": ["ProductionBatch"],
        "expected_pattern": "GROUP BY",
    },
    {
        "question": "Which supplier delivered the most raw material last month?",
        "expected_tables": ["RawMaterialIntake"],
        "expected_pattern": "ORDER BY",
    },
    {
        "question": "What is the average yield percentage across all products?",
        "expected_tables": ["ProductionBatch"],
        "expected_pattern": "AVG",
    },
]

SYSTEM_PROMPT = """You are a SQL assistant for a food manufacturing database.
Generate ONLY the SQL query, nothing else. Use SQLite syntax.

Tables:
Products: ProductCode, ProductName, Species, Category, CostPerKg, SellPricePerKg, Allergens
ProductionBatch: BatchID, BatchNo, ProductCode, ProductionDate, InputKg, OutputKg, WasteKg, YieldPct, LineNo, Shift, OperatorName
SalesOrders: OrderID, CustomerCode, ProductCode, QuantityKg, OrderDate, DeliveryDate, Status, PricePerKg
Customers: CustomerCode, CustomerName
TemperatureLogs: LogID, LocationName, Temperature, RecordedAt, RecordedBy
RawMaterialIntake: IntakeID, ProductCode, BatchNo, SupplierCode, QuantityKg, IntakeDate, ExpiryDate, TempOnArrival
Employees: EmployeeID, FullName, Role, ShiftPattern, WeeklyHours, HourlyRate
WasteRecords: WasteID, BatchID, WasteType, QuantityKg, Reason, WasteDate"""


def benchmark_model(client, model_name):
    """Run all benchmark questions against a model and score results."""
    print(f"\n{'='*60}")
    print(f"  Benchmarking: {model_name}")
    print(f"{'='*60}")

    results = []
    engine = create_engine(DATABASE_URL, echo=False)

    # Warmup
    try:
        client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "SELECT 1"}],
            max_tokens=10,
        )
    except Exception as e:
        print(f"  ERROR: Model '{model_name}' not available: {e}")
        return None

    for i, test in enumerate(BENCHMARK_QUESTIONS, 1):
        print(f"\n  Q{i}: {test['question']}")

        start = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": test["question"]},
                ],
            )
            elapsed = time.perf_counter() - start
            sql = (response.choices[0].message.content or "").strip()

            # Clean markdown
            if sql.startswith("```"):
                sql = sql.split("\n", 1)[1] if "\n" in sql else sql[3:]
            if sql.endswith("```"):
                sql = sql[:-3]
            sql = sql.strip()
            if sql.lower().startswith("sql"):
                sql = sql[3:].strip()

            # Score: does it contain expected pattern?
            has_pattern = test["expected_pattern"].upper() in sql.upper()

            # Score: does it reference expected tables?
            tables_found = sum(1 for t in test["expected_tables"] if t.lower() in sql.lower())
            tables_expected = len(test["expected_tables"])

            # Score: does it execute?
            executes = False
            try:
                if sql.upper().startswith(("SELECT", "WITH")):
                    pd.read_sql(sql, engine)
                    executes = True
            except Exception:
                pass

            score = (
                (1 if has_pattern else 0) +
                (1 if tables_found == tables_expected else 0) +
                (2 if executes else 0)
            )

            print(f"      Time: {elapsed:.1f}s | Pattern: {'Y' if has_pattern else 'N'} | "
                  f"Tables: {tables_found}/{tables_expected} | Executes: {'Y' if executes else 'N'} | "
                  f"Score: {score}/4")

            results.append({
                "question": test["question"],
                "time": elapsed,
                "has_pattern": has_pattern,
                "tables_correct": tables_found == tables_expected,
                "executes": executes,
                "score": score,
                "sql": sql[:100],
            })

        except Exception as e:
            elapsed = time.perf_counter() - start
            print(f"      ERROR: {e} ({elapsed:.1f}s)")
            results.append({
                "question": test["question"],
                "time": elapsed,
                "has_pattern": False,
                "tables_correct": False,
                "executes": False,
                "score": 0,
                "sql": f"ERROR: {e}",
            })

    engine.dispose()
    return results


def print_summary(all_results):
    """Print comparison summary across models."""
    print(f"\n{'='*60}")
    print("  COMPARISON SUMMARY")
    print(f"{'='*60}\n")

    print(f"{'Model':<20} {'Avg Time':>10} {'Accuracy':>10} {'Executes':>10} {'Score':>10}")
    print("-" * 62)

    for model, results in all_results.items():
        if results is None:
            print(f"{model:<20} {'N/A':>10} {'N/A':>10} {'N/A':>10} {'N/A':>10}")
            continue

        avg_time = sum(r["time"] for r in results) / len(results)
        accuracy = sum(1 for r in results if r["has_pattern"]) / len(results) * 100
        exec_rate = sum(1 for r in results if r["executes"]) / len(results) * 100
        total_score = sum(r["score"] for r in results)
        max_score = len(results) * 4

        print(f"{model:<20} {avg_time:>8.1f}s {accuracy:>9.0f}% {exec_rate:>9.0f}% "
              f"{total_score:>5}/{max_score}")

    print("\nScoring: pattern match (1pt) + correct tables (1pt) + executes (2pt) = 4pt max per question")


if __name__ == "__main__":
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY is not set.")
        print("Set it: export OPENAI_API_KEY=sk-...")
        sys.exit(1)

    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    models = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"]

    print("FloorMind Model Benchmark")
    print(f"Testing {len(BENCHMARK_QUESTIONS)} questions across {len(models)} models\n")

    all_results = {}
    for model in models:
        all_results[model] = benchmark_model(client, model)

    print_summary(all_results)
