import os
import json
import pandas as pd
from datasets import load_dataset

def export_15k_dataset():
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
    print(f"Loading b-mc2/sql-create-context from Hugging Face...")
    
    # Load dataset
    raw_dataset = load_dataset("b-mc2/sql-create-context", split="train")
    print(f"Total dataset records: {len(raw_dataset)}")
    
    # Shuffle with seed 42 and pick 15,000 samples
    print("Shuffling with seed=42 and extracting 15,000 samples...")
    sampled_dataset = raw_dataset.shuffle(seed=42).select(range(15000))
    print(f"Sampled records: {len(sampled_dataset)}")
    
    # Convert to list of dicts
    samples = [item for item in sampled_dataset]
    
    # 1. Save as JSON
    json_path = os.path.join(output_dir, "train_15k.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False)
    print(f"Saved: {json_path} ({os.path.getsize(json_path) / (1024*1024):.2f} MB)")
    
    # 2. Save as JSONL (standard for fine-tuning / LLM training)
    jsonl_path = os.path.join(output_dir, "train_15k.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for item in samples:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Saved: {jsonl_path} ({os.path.getsize(jsonl_path) / (1024*1024):.2f} MB)")
    
    # 3. Save as CSV
    csv_path = os.path.join(output_dir, "train_15k.csv")
    df = pd.DataFrame(samples)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"Saved: {csv_path} ({os.path.getsize(csv_path) / (1024*1024):.2f} MB)")

    # 4. Save metadata summary
    summary_path = os.path.join(output_dir, "README.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"""# Text-to-SQL Dataset (15,000 Samples)

- **Source:** [`b-mc2/sql-create-context`](https://huggingface.co/datasets/b-mc2/sql-create-context)
- **Total Records Extracted:** 15,000
- **Random Seed:** 42
- **Formats Available:**
  - `train_15k.json`: JSON Array format
  - `train_15k.jsonl`: JSON Lines format (for LLM training pipelines)
  - `train_15k.csv`: Tabular CSV format

## Schema Fields:
1. `context`: The SQL `CREATE TABLE` DDL statement providing schema context.
2. `question`: Natural language English question.
3. `answer`: Corresponding executable SQL query.

## Sample Record:
```json
{json.dumps(samples[0], indent=2)}
```
""")
    print(f"Saved: {summary_path}")
    print("\nAll 15,000 samples successfully saved to ml/dataset/!")

if __name__ == "__main__":
    export_15k_dataset()
