import os
import sys
import time
import json
import sqlite3
import re
from datetime import datetime
from datasets import load_dataset

# Add workspace root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from ml.inference.local_engine import LocalInferenceEngine


def clean_sql(sql: str) -> str:
    """Normalizes SQL string for fair string comparison."""
    if not sql:
        return ""
    s = sql.strip()
    # Remove markdown formatting
    if s.startswith("```sql"):
        s = s[6:]
    elif s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    s = s.strip()
    s = re.sub(r';+$', '', s).strip()
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def create_sqlite_db_from_ddl(ddl: str) -> sqlite3.Connection:
    """
    Creates an in-memory SQLite database from CREATE TABLE DDL
    and inserts dummy rows for execution accuracy testing.
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Clean and split DDL statements
    clean_ddl = re.sub(r'PRIMARY KEY\s*\([^\)]+\)', '', ddl, flags=re.IGNORECASE)
    clean_ddl = re.sub(r'FOREIGN KEY\s*\([^\)]+\)\s*REFERENCES\s*\w+\([^\)]+\)', '', clean_ddl, flags=re.IGNORECASE)
    clean_ddl = re.sub(r',\s*,', ',', clean_ddl)
    clean_ddl = re.sub(r',\s*\)', ')', clean_ddl)
    
    statements = [stmt.strip() for stmt in clean_ddl.split(";") if stmt.strip()]
    
    for stmt in statements:
        try:
            cursor.execute(stmt)
            # Find table name
            tbl_match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?', stmt, flags=re.IGNORECASE)
            if tbl_match:
                tbl_name = tbl_match.group(1)
                # Introspect created table columns
                cursor.execute(f"PRAGMA table_info({tbl_name})")
                cols = cursor.fetchall()
                if cols:
                    col_names = [c[1] for c in cols]
                    col_types = [c[2].upper() for c in cols]
                    
                    # Insert 5 representative mock rows
                    for row_idx in range(1, 6):
                        mock_vals = []
                        for col_type in col_types:
                            if any(t in col_type for t in ['INT', 'FLOAT', 'NUMERIC', 'DECIMAL', 'REAL']):
                                mock_vals.append(row_idx * 10)
                            elif 'DATE' in col_type:
                                mock_vals.append('2024-01-01')
                            else:
                                mock_vals.append(f"Val_{row_idx}")
                                
                        placeholders = ", ".join(["?"] * len(mock_vals))
                        cursor.execute(f"INSERT INTO {tbl_name} ({', '.join(col_names)}) VALUES ({placeholders})", mock_vals)
            conn.commit()
        except Exception:
            pass
            
    return conn


def test_sql_execution(conn: sqlite3.Connection, sql: str):
    """Executes SQL against in-memory DB and returns status, rows, error."""
    if not conn or not sql:
        return False, None, "No connection or empty SQL"
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        return True, rows, None
    except Exception as e:
        return False, None, str(e)


def run_evaluation(num_samples: int = 50, test_start_idx: int = 15000):
    """
    Evaluates fine-tuned model on held-out test split of b-mc2/sql-create-context.
    """
    print("=" * 75)
    print("STARTING TEXT-TO-SQL MODEL EVALUATION")
    print(f"Sample Count: {num_samples} unseen test records (Indices {test_start_idx} to {test_start_idx + num_samples})")
    print("=" * 75)
    
    # 1. Load Dataset
    print("\n[1/4] Loading unseen held-out test split from Hugging Face...")
    raw_dataset = load_dataset("b-mc2/sql-create-context", split="train")
    
    # Use fixed seed 42 to ensure records 15000+ are 100% strictly unseen
    shuffled = raw_dataset.shuffle(seed=42)
    test_split = shuffled.select(range(test_start_idx, test_start_idx + num_samples))
    print(f"Loaded {len(test_split)} held-out evaluation pairs.")

    # 2. Load Fine-Tuned Model & Adapter
    print("\n[2/4] Initializing Local Inference Engine (Qwen2.5-1.5B + LoRA Adapter)...")
    adapter_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/text-to-sql-lora-adapter"))
    engine = LocalInferenceEngine(adapter_path=adapter_path)
    print("Engine ready for evaluation.")

    # 3. Evaluation Loop
    print("\n[3/4] Running automated benchmark evaluation...")
    exact_matches = 0
    execution_matches = 0
    valid_sqls = 0
    latencies = []
    
    detailed_results = []

    for idx, sample in enumerate(test_split, 1):
        schema = sample["context"]
        question = sample["question"]
        gold_sql = clean_sql(sample["answer"])
        
        t0 = time.time()
        raw_pred = engine.generate_sql(schema=schema, question=question)
        elapsed = time.time() - t0
        latencies.append(elapsed)
        
        pred_sql = clean_sql(raw_pred)
        
        # Metric 1: Exact Match (EM)
        is_em = (pred_sql.lower() == gold_sql.lower())
        if is_em:
            exact_matches += 1
            
        # Create In-Memory DB & Test Execution
        conn = create_sqlite_db_from_ddl(schema)
        
        gold_ok, gold_rows, gold_err = test_sql_execution(conn, gold_sql)
        pred_ok, pred_rows, pred_err = test_sql_execution(conn, pred_sql)
        
        # Metric 2: Valid SQL Rate (VES)
        if pred_ok:
            valid_sqls += 1
            
        # Metric 3: Execution Accuracy (EX)
        is_ex = False
        if gold_ok and pred_ok:
            is_ex = (set(pred_rows) == set(gold_rows))
        elif is_em:
            is_ex = True
            
        if is_ex:
            execution_matches += 1

        conn.close()

        print(f"[{idx:02d}/{num_samples}] "
              f"EX: {'[PASS]' if is_ex else '[FAIL]'} | "
              f"VES: {'[VALID]' if pred_ok else '[SYNTAX_ERR]'} | "
              f"EM: {'[MATCH]' if is_em else '[DIFF]'} | "
              f"Time: {elapsed:.2f}s")
              
        if not is_ex:
            print(f"   Q: {question[:65]}...")
            print(f"   Gold: {gold_sql}")
            print(f"   Pred: {pred_sql}")
            if pred_err:
                print(f"   Err:  {pred_err}")

        detailed_results.append({
            "index": idx,
            "question": question,
            "schema": schema,
            "gold_sql": gold_sql,
            "pred_sql": pred_sql,
            "exact_match": is_em,
            "valid_sql": pred_ok,
            "execution_match": is_ex,
            "latency_seconds": round(elapsed, 2),
            "error": pred_err
        })

    # 4. Final Aggregated Metrics
    em_rate = (exact_matches / num_samples) * 100
    ex_rate = (execution_matches / num_samples) * 100
    ves_rate = (valid_sqls / num_samples) * 100
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    print("\n" + "=" * 75)
    print("FINAL EVALUATION METRICS REPORT")
    print("=" * 75)
    print(f"Evaluated Test Samples       : {num_samples} unseen queries")
    print(f"Execution Accuracy (EX)      : {ex_rate:.2f}% ({execution_matches}/{num_samples})")
    print(f"Valid SQL Syntax Rate (VES)  : {ves_rate:.2f}% ({valid_sqls}/{num_samples})")
    print(f"Exact Match Accuracy (EM)    : {em_rate:.2f}% ({exact_matches}/{num_samples})")
    print(f"Average Inference Latency    : {avg_latency:.2f} seconds / query")
    print("=" * 75)

    # 5. Export JSON
    eval_dir = os.path.dirname(__file__)
    json_path = os.path.join(eval_dir, "eval_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "model": "Qwen/Qwen2.5-1.5B-Instruct + QLoRA",
            "dataset": "b-mc2/sql-create-context (held-out test split)",
            "num_samples": num_samples,
            "execution_accuracy_pct": round(ex_rate, 2),
            "valid_sql_rate_pct": round(ves_rate, 2),
            "exact_match_pct": round(em_rate, 2),
            "avg_latency_seconds": round(avg_latency, 2),
            "samples": detailed_results
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSaved detailed evaluation JSON to: {json_path}")

    return ex_rate, ves_rate, em_rate, avg_latency

if __name__ == "__main__":
    # Run evaluation on 30 test samples for quick empirical validation
    run_evaluation(num_samples=30, test_start_idx=15000)
