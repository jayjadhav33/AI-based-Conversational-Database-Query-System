# Text-to-SQL Dataset (15,000 Samples)

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
{
  "answer": "SELECT venue FROM table_name_50 WHERE away_team = \"essendon\"",
  "question": "When Essendon played away; where did they play?",
  "context": "CREATE TABLE table_name_50 (venue VARCHAR, away_team VARCHAR)"
}
```
