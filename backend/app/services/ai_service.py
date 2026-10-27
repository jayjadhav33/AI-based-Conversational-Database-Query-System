import os
import re
from sqlalchemy.orm import Session
import sys
from typing import List, Tuple, Any, Dict, Optional

# Ensure ml directory can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.models.database_conn import DatabaseConn
from app.models.query_history import QueryHistory
from app.services.schema_service import extract_schema
from app.services.query_service import execute_safe_query
from app.security.encryption import decrypt_db_password
from app.schemas.ai import ChatMessage

# Singleton for inference engine
_inference_engine = None

def get_inference_engine():
    global _inference_engine
    if _inference_engine is None:
        from ml.inference.local_engine import LocalInferenceEngine
        print("Lazy loading AI model into memory...")
        adapter_path = os.path.join(os.path.dirname(__file__), "../../../ml/models/text-to-sql-lora-adapter")
        if not os.path.exists(adapter_path):
            adapter_path = None
        _inference_engine = LocalInferenceEngine(adapter_path=adapter_path)
    return _inference_engine


def extract_name_entity(question: str, schema_info: list = None) -> Optional[str]:
    """
    Extracts named person/entity from questions like:
    'is there Dr. Amit Joshi in database', 'find Dr. Anil Mehta', 'about presence of amit joshi'
    Avoids matching generic table queries like 'show suppliers from Pune'.
    """
    if not question:
        return None
    q_clean = re.sub(r'\s+in\s+(?:the\s+)?database\b|\s+present\b|\s+available\b|\?|\.', '', question, flags=re.IGNORECASE).strip()
    
    # 1. Check for explicit titles (Dr., Mr., Mrs., Prof., etc.)
    title_match = re.search(r'\b(?:Dr\.|Dr|Mr\.|Mr|Mrs\.|Mrs|Prof\.|Prof)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)', q_clean, re.IGNORECASE)
    if title_match:
        return title_match.group(1).strip()
        
    # 2. Check for explicit entity search phrasing: "is there X in database", "about presence of X"
    presence_match = re.search(r'(?:is\s+there|about\s+presence\s+of|check\s+if\s+there\s+is)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)', q_clean, re.IGNORECASE)
    if presence_match:
        entity = presence_match.group(1).strip()
        stopwords = {'a', 'an', 'the', 'all', 'any', 'some', 'many', 'anyone', 'someone'}
        if schema_info:
            for tbl in schema_info:
                stopwords.add(tbl['table_name'].lower())
                stopwords.add(tbl['table_name'].lower()[:-1] if tbl['table_name'].lower().endswith('s') else tbl['table_name'].lower())
        if entity.lower() not in stopwords:
            return entity

    return None

def select_relevant_schema(schema_info: list, question: str) -> list:
    """
    Intelligently filters schema to only the tables relevant to the user question.
    If a question asks about doctors or a doctor's name (e.g. 'is there Dr. Amit Joshi'),
    it isolates the 'doctors' table schema and avoids hallucinating joins with 'appointments'.
    """
    if not schema_info:
        return schema_info
        
    clean_q = re.sub(r'[^\w\s]', ' ', question.lower())
    q_tokens = set(clean_q.split())
    
    # Check if a doctor/title is mentioned
    is_doctor_query = any(t in q_tokens for t in ['dr', 'doctor', 'doctors', 'physician', 'surgeon', 'dermatologist', 'cardiologist', 'specialist', 'specialization'])
    
    # Keywords indicating a multi-table relational query
    multi_table_intent_words = {
        'with', 'joined', 'having', 'booked', 'visited', 'scheduled', 'appointment', 
        'appointments', 'patient', 'patients', 'order', 'orders', 'item', 'items',
        'per', 'each', 'most', 'highest', 'top', 'between', 'connect'
    }
    
    has_multi_intent = any(w in q_tokens for w in multi_table_intent_words)
    
    matched_tables = []
    
    for table_data in schema_info:
        tbl_name = table_data['table_name'].lower()
        singular = tbl_name[:-1] if tbl_name.endswith('s') else tbl_name
        plural = tbl_name if tbl_name.endswith('s') else tbl_name + 's'
        
        is_matched = (tbl_name in q_tokens or singular in q_tokens or plural in q_tokens)
        
        if not is_matched and is_doctor_query and ('doctor' in tbl_name or 'dr' in tbl_name):
            is_matched = True
            
        # Check column names
        if not is_matched:
            for col in table_data['columns']:
                c_name = col['name'].lower()
                if c_name in q_tokens and len(c_name) > 2:
                    is_matched = True
                    break
                    
        if is_matched:
            matched_tables.append(table_data)
            
    # If a specific person name is detected, find the table with a 'name' column
    entity_name = extract_name_entity(question, schema_info)
    if entity_name and not matched_tables:
        for table_data in schema_info:
            for col in table_data['columns']:
                if col['name'].lower() in {'name', 'doctor_name', 'patient_name', 'supplier_name', 'student_name', 'customer_name', 'product_name', 'full_name'}:
                    matched_tables.append(table_data)
                    break
            if matched_tables:
                break
            
    # If exactly ONE table was matched and no explicit multi-table keywords are present, restrict to that table
    if len(matched_tables) == 1 and not has_multi_intent:
        print(f"Schema pruned to single relevant table: {[t['table_name'] for t in matched_tables]}")
        return matched_tables
        
    if len(matched_tables) > 1:
        return matched_tables
        
    return schema_info

def format_schema_ddl(schema_info: list) -> str:
    """
    Converts schema metadata into standard SQL CREATE TABLE DDL statements.
    This exactly matches the training format of b-mc2/sql-create-context.
    """
    statements = []
    for table_data in schema_info:
        table_name = table_data['table_name']
        col_defs = [f"{col['name']} {col['type']}" for col in table_data['columns']]
        
        if table_data.get('primary_keys'):
            col_defs.append(f"PRIMARY KEY ({', '.join(table_data['primary_keys'])})")
            
        if table_data.get('foreign_keys'):
            for fk in table_data['foreign_keys']:
                col_defs.append(
                    f"FOREIGN KEY ({', '.join(fk['constrained_columns'])}) REFERENCES {fk['referred_table']}({', '.join(fk['referred_columns'])})"
                )
                
        statements.append(f"CREATE TABLE {table_name} ({', '.join(col_defs)});")
    return "\n".join(statements)

def sanitize_and_heal_sql(sql: str, schema_info: list, question: str = "") -> str:
    """
    Cleans up syntax discrepancies common in small model outputs:
    1. Replaces ILIKE with MySQL-compatible LIKE.
    2. Heals undeclared alias hallucinations (e.g. T3.col when only T1 is declared).
    3. Handles title prefixes and wildcards in string matches.
    4. Automatically binds search entities (e.g. 'Dr. Amit Joshi') to the target name column.
    """
    if not sql:
        return sql
        
    cleaned_sql = sql.strip()
    
    # Remove markdown code fences if present
    if cleaned_sql.startswith("```sql"):
        cleaned_sql = cleaned_sql[6:]
    elif cleaned_sql.startswith("```"):
        cleaned_sql = cleaned_sql[3:]
    if cleaned_sql.endswith("```"):
        cleaned_sql = cleaned_sql[:-3]
    cleaned_sql = cleaned_sql.strip()

    # 1. Replace ILIKE with LIKE
    cleaned_sql = re.sub(r'\bILIKE\b', 'LIKE', cleaned_sql, flags=re.IGNORECASE)

    # 2. Entity Name Search Guarantee:
    entity = extract_name_entity(question, schema_info)
    if entity:
        entity_wildcard = re.sub(r'[\s\-_]+', '%', entity)
        first_word = entity.split()[0].lower()
        if first_word not in cleaned_sql.lower():
            target_tbl = None
            col_name = "name"
            for tbl in schema_info:
                for col in tbl['columns']:
                    if col['name'].lower() in {'name', 'doctor_name', 'patient_name', 'student_name', 'supplier_name', 'customer_name', 'full_name'}:
                        target_tbl = tbl['table_name']
                        col_name = col['name']
                        break
                if target_tbl:
                    break
            if target_tbl:
                print(f"Entity detected ('{entity}') but missing in model SQL -> Reconstructing filter on {target_tbl}.{col_name}")
                return f"SELECT * FROM {target_tbl} WHERE {col_name} LIKE '%{entity_wildcard}%'"

    # 3. Prune unrequested JOINs for simple 'list all / show all' queries without extra filters
    q_lower = question.lower() if question else ""
    is_simple_list_query = any(k in q_lower for k in ['list all', 'show all', 'get all', 'all doctors', 'all students', 'all customers', 'all patients', 'all suppliers'])
    
    if is_simple_list_query and 'JOIN' in cleaned_sql.upper() and not any(k in q_lower for k in ['appointment', 'order', 'booking', 'with', 'having', 'count', 'where', 'from', 'in']):
        from_match = re.search(r'FROM\s+`?(\w+)`?(?:\s+(?:AS\s+)?(\w+))?', cleaned_sql, flags=re.IGNORECASE)
        if from_match:
            main_table = from_match.group(1)
            print(f"Pruning hallucinated JOIN from simple listing query -> SELECT * FROM {main_table}")
            return f"SELECT * FROM {main_table}"

    # 4. Fix Alias Hallucinations
    declared_aliases = set(re.findall(r'(?:FROM|JOIN)\s+`?(\w+)`?(?:\s+(?:AS\s+)?(\w+))?', cleaned_sql, flags=re.IGNORECASE))
    active_aliases = set()
    for tbl, alias in declared_aliases:
        if alias:
            active_aliases.add(alias.upper())
        elif tbl:
            active_aliases.add(tbl.upper())
            
    referenced_aliases = re.findall(r'\b(T\d+)\.', cleaned_sql)
    for ref_alias in referenced_aliases:
        if ref_alias.upper() not in active_aliases:
            fallback_alias = next(iter(active_aliases), "")
            if fallback_alias and fallback_alias != ref_alias.upper():
                cleaned_sql = re.sub(rf'\b{ref_alias}\.', f"{fallback_alias}.", cleaned_sql)
            else:
                cleaned_sql = re.sub(rf'\b{ref_alias}\.', "", cleaned_sql)

    # 5. Wildcard optimization for flexible name/text search
    def make_flexible_match(match):
        col = match.group(1)
        val = match.group(2).strip()
        val_cleaned = re.sub(r'^(?:Dr\.|Dr|Mr\.|Mr|Mrs\.|Mrs|Prof\.|Prof)\s+', '', val, flags=re.IGNORECASE)
        flexible_val = re.sub(r'[\s\-_]+', '%', val_cleaned)
        return f"{col} LIKE '%{flexible_val}%'"
        
    cleaned_sql = re.sub(r'([\w\.]+)\s*=\s*[\'"]([^\'"]+)[\'"]', make_flexible_match, cleaned_sql)
    
    return cleaned_sql

def try_generate_fast_sql(schema_info: list, question: str) -> Optional[str]:
    """
    Instant rule-based fast path for high-frequency queries.
    Returns SQL immediately (in <5ms) without calling the LLM.
    """
    if not schema_info or not question:
        return None

    q_lower = question.lower().strip()
    clean_q = re.sub(r'[^\w\s]', ' ', q_lower)
    tokens = set(clean_q.split())
    
    # -------------------------------------------------------------
    # 0. High-Priority Aggregations (SUM, AVG, MIN, MAX)
    # -------------------------------------------------------------
    table_map = {t['table_name'].lower(): t for t in schema_info}
    
    # A. Total Items / Units Sold -> SUM(quantity_sold) FROM sales
    if any(p in q_lower for p in [
        'items sold', 'item sold', 'quantity sold', 'units sold', 'unit sold', 
        'products sold', 'product sold', 'number of items sold', 'total items sold', 
        'total units sold', 'total sold', 'how many items sold', 'how many units sold',
        'sum of quantity sold', 'total quantity sold'
    ]):
        if 'sales' in table_map:
            cols = {c['name'].lower(): c['name'] for c in table_map['sales']['columns']}
            q_col = cols.get('quantity_sold') or cols.get('quantity')
            if q_col:
                return f"SELECT SUM({q_col}) FROM sales"

    # B. Total Revenue / Sales Amount -> SUM(total_amount) FROM sales
    if any(p in q_lower for p in [
        'total sales revenue', 'total revenue', 'sales revenue', 'total sales amount', 
        'total amount of sales', 'total money from sales', 'total sales value', 
        'sum of total_amount', 'sum of sales', 'revenue generated'
    ]):
        if 'sales' in table_map:
            cols = {c['name'].lower(): c['name'] for c in table_map['sales']['columns']}
            amt_col = cols.get('total_amount') or cols.get('amount') or cols.get('price')
            if amt_col:
                return f"SELECT SUM({amt_col}) FROM sales"

    # C. Total Stock Quantity -> SUM(quantity) FROM products
    if any(p in q_lower for p in [
        'total stock quantity', 'total stock', 'total inventory', 'total quantity in stock',
        'stock quantity', 'total quantity of products', 'sum of quantity'
    ]):
        if 'products' in table_map:
            cols = {c['name'].lower(): c['name'] for c in table_map['products']['columns']}
            if 'quantity' in cols:
                return f"SELECT SUM({cols['quantity']}) FROM products"

    # D. Average Price -> AVG(price) FROM products
    if any(p in q_lower for p in ['average price', 'avg price', 'mean price']):
        if 'products' in table_map:
            cols = {c['name'].lower(): c['name'] for c in table_map['products']['columns']}
            if 'price' in cols:
                return f"SELECT AVG({cols['price']}) FROM products"

    # E. Average Quantity Sold / Sale Amount
    if any(p in q_lower for p in ['average quantity sold', 'avg quantity sold']):
        if 'sales' in table_map:
            cols = {c['name'].lower(): c['name'] for c in table_map['sales']['columns']}
            if 'quantity_sold' in cols:
                return f"SELECT AVG({cols['quantity_sold']}) FROM sales"

    if any(p in q_lower for p in ['average sales amount', 'average sale amount', 'avg total amount', 'average total amount']):
        if 'sales' in table_map:
            cols = {c['name'].lower(): c['name'] for c in table_map['sales']['columns']}
            if 'total_amount' in cols:
                return f"SELECT AVG({cols['total_amount']}) FROM sales"

    # F. Most / Least Expensive Product
    if any(p in q_lower for p in ['most expensive product', 'highest price product', 'product with highest price', 'max price product']):
        if 'products' in table_map:
            return "SELECT * FROM products ORDER BY price DESC LIMIT 1"

    # G. Average Age of Patients
    if any(p in q_lower for p in ['average age', 'avg age', 'mean age']):
        if 'patients' in table_map:
            cols = {c['name'].lower(): c['name'] for c in table_map['patients']['columns']}
            if 'age' in cols:
                return f"SELECT AVG({cols['age']}) FROM patients"

    # -------------------------------------------------------------
    # 1. Identify Target Table
    # -------------------------------------------------------------
    target_table = None
    target_table_name = None
    for table in schema_info:
        tbl_name = table['table_name'].lower()
        singular = tbl_name[:-1] if tbl_name.endswith('s') else tbl_name
        plural = tbl_name if tbl_name.endswith('s') else tbl_name + 's'
        if tbl_name in tokens or singular in tokens or plural in tokens:
            target_table = table
            target_table_name = table['table_name']
            break

    # If no exact table name match, check synonyms
    if not target_table:
        synonym_map = [
            ('doctors', ['dr', 'doctor', 'physician', 'surgeon']),
            ('patients', ['patient']),
            ('appointments', ['appointment']),
            ('medical_records', ['record', 'records', 'medical_record', 'medical_records', 'diagnosis', 'treatment']),
            ('sales', ['sale', 'sales', 'transaction', 'transactions']),
            ('products', ['product', 'item', 't-shirt', 'shirt', 'clothes', 'goods']),
            ('suppliers', ['supplier', 'vendor', 'dealer', 'merchant']),
            ('customers', ['customer', 'client', 'buyer']),
            ('orders', ['order', 'purchase']),
            ('categories', ['category', 'categories']),
            ('students', ['student', 'pupil']),
        ]
        for alias, keywords in synonym_map:
            if any(k in tokens for k in keywords):
                for table in schema_info:
                    if alias in table['table_name'].lower() or any(k in table['table_name'].lower() for k in keywords):
                        target_table = table
                        target_table_name = table['table_name']
                        break
            if target_table:
                break

    # 2. Direct Named Entity Search (e.g. "is there Dr. Amit Joshi in database")
    entity = extract_name_entity(question, schema_info)
    if entity:
        entity_wildcard = re.sub(r'[\s\-_]+', '%', entity)
        candidate_tables = [target_table] if target_table else schema_info
        for table in candidate_tables:
            for col in table['columns']:
                if col['name'].lower() in {'name', 'doctor_name', 'patient_name', 'student_name', 'customer_name', 'supplier_name', 'product_name', 'full_name'}:
                    return f"SELECT * FROM {table['table_name']} WHERE {col['name']} LIKE '%{entity_wildcard}%'"

    if not target_table:
        return None

    # Check multi-table join intent (only when multiple tables are actually involved)
    multi_intent = any(w in tokens for w in ['joined', 'connect'])
    if multi_intent:
        return None

    where_conds = []
    
    # 1. Location / Department / Category filters (e.g., "from Pune", "in Pune", "in Cardiology", "in Dermatology")
    loc_match = re.search(
        r'\b(?:are\s+from|is\s+from|from|located\s+in|based\s+in|living\s+in|staying\s+in|in|at)\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)*)',
        question,
        re.IGNORECASE
    )
    if loc_match:
        loc_val = loc_match.group(1).strip()
        loc_val_clean = re.sub(r'[\?\.]$', '', loc_val).strip()
        stopwords = {'the', 'a', 'an', 'database', 'db', 'there', 'all', 'any', 'some', 'many', 'table', 'system', 'here', target_table_name.lower()}
        if loc_val_clean.lower() not in stopwords:
            loc_col = None
            for col in target_table['columns']:
                c_name = col['name'].lower()
                if c_name in {'city', 'location', 'state', 'country', 'address', 'branch', 'place', 'town', 'region', 'district', 'department', 'specialization', 'category', 'category_name'}:
                    loc_col = col['name']
                    break
            if loc_col:
                where_conds.append(f"{loc_col} LIKE '%{loc_val_clean}%'")

    # 2. Explicit column mention (e.g., "where city is Pune", "with color Black", "size is XL", "with size L")
    if not where_conds:
        for col in target_table['columns']:
            c_name = col['name'].lower()
            col_match = re.search(
                rf'\b(?:where|whose|with|having)?\s*{re.escape(c_name)}\s*(?:is|=|:|\s+is\s+|\s+of\s+|\s+as\s+|\s+)?\s*[\'"`]?([A-Za-z0-9_\-]+)[\'"`]?',
                question,
                re.IGNORECASE
            )
            if col_match:
                val = col_match.group(1).strip()
                stopwords = {'the', 'a', 'an', 'database', 'db', 'there', 'all', 'any', 'is', 'are', 'in', 'of', 'for', target_table_name.lower()}
                if val.lower() not in stopwords:
                    where_conds.append(f"{col['name']} LIKE '%{val}%'")
                    break

    # 3. Numeric comparisons (e.g. "price > 500", "price greater than 500", "quantity < 10")
    if not where_conds:
        num_match = re.search(
            r'\b(\w+)\s*(?:>=|<=|!=|>|<|=|(?:greater\s+than|more\s+than|above|over)\s*|(?:less\s+than|below|under)\s*|(?:equal\s+to|equals)\s*)\s*(\d+(?:\.\d+)?)\b',
            question,
            re.IGNORECASE
        )
        if num_match:
            col_cand = num_match.group(1).lower()
            val_cand = num_match.group(2)
            op = ">"
            if re.search(r'<=|(?:less\s+than\s+or\s+equal)', question, re.IGNORECASE):
                op = "<="
            elif re.search(r'>=|(?:greater\s+than\s+or\s+equal)', question, re.IGNORECASE):
                op = ">="
            elif re.search(r'<|(?:less\s+than|below|under)', question, re.IGNORECASE):
                op = "<"
            elif re.search(r'>|(?:greater\s+than|more\s+than|above|over)', question, re.IGNORECASE):
                op = ">"
            elif re.search(r'!=|not\s+equal', question, re.IGNORECASE):
                op = "!="
            elif re.search(r'=|(?:equal\s+to|equals)', question, re.IGNORECASE):
                op = "="
                
            for col in target_table['columns']:
                if col['name'].lower() == col_cand:
                    where_conds.append(f"{col['name']} {op} {val_cand}")
                    break

    # 4. Fuzzy Category / Specialization / Status / Role / Color / Size filter
    if not where_conds:
        cat_match = re.search(
            r'\b(?:are|is)\s+([A-Za-z0-9_\-]+)',
            question,
            re.IGNORECASE
        )
        if cat_match:
            cat_val = cat_match.group(1).strip()
            stopwords = {'the', 'a', 'an', 'database', 'db', 'there', 'all', 'any', 'some', 'many', 'from', 'table', 'present', 'available', target_table_name.lower()}
            if cat_val.lower() not in stopwords:
                for col in target_table['columns']:
                    c_name = col['name'].lower()
                    if c_name in {'color', 'size', 'specialization', 'department', 'status', 'role', 'category', 'category_name', 'type', 'designation', 'gender', 'city', 'branch', 'address', 'diagnosis', 'treatment'}:
                        where_conds.append(f"{col['name']} LIKE '%{cat_val}%'")
                        break

    where_clause = " AND ".join(where_conds) if where_conds else ""

    # Check query intent: Count vs List vs Select
    is_count = any(k in q_lower for k in ['how many', 'count of', 'count ', 'total ', 'number of'])
    
    if is_count:
        if where_clause:
            return f"SELECT COUNT(*) FROM {target_table_name} WHERE {where_clause}"
        # If no where clause, verify if question is purely asking for total count without unrecognized criteria
        pure_count_stopwords = {
            'how', 'many', 'count', 'total', 'number', 'of', 'are', 'is', 'there', 
            'in', 'the', 'database', 'db', 'all', 'a', 'an', 'present', 'available', 
            'records', 'record', target_table_name.lower(), 
            target_table_name.lower()[:-1] if target_table_name.lower().endswith('s') else target_table_name.lower()
        }
        for sub_word in target_table_name.lower().replace('_', ' ').split():
            pure_count_stopwords.add(sub_word)
        remaining_words = tokens - pure_count_stopwords
        if not remaining_words:
            return f"SELECT COUNT(*) FROM {target_table_name}"
        # If unknown criteria exist, return None so LLM handles it accurately
        return None

    # Listing / Fetching intent
    is_list = any(phrase in q_lower for phrase in [
        'list all', 'show all', 'get all', 'fetch all', 'display all', 
        'all ' + target_table_name.lower(), 'list ' + target_table_name.lower(),
        'show ' + target_table_name.lower(), 'get ' + target_table_name.lower(),
        'find ' + target_table_name.lower(), 'display ' + target_table_name.lower(),
        'list', 'show', 'get', 'fetch', 'display', 'find'
    ])
    
    if where_clause:
        return f"SELECT * FROM {target_table_name} WHERE {where_clause}"

    if is_list:
        pure_list_stopwords = {
            'list', 'show', 'get', 'fetch', 'display', 'find', 'all', 'the', 'a', 'an',
            'in', 'database', 'db', 'records', 'record', 'data', 'details', 'info',
            target_table_name.lower(),
            target_table_name.lower()[:-1] if target_table_name.lower().endswith('s') else target_table_name.lower()
        }
        for sub_word in target_table_name.lower().replace('_', ' ').split():
            pure_list_stopwords.add(sub_word)
        remaining_words = tokens - pure_list_stopwords
        if not remaining_words:
            return f"SELECT * FROM {target_table_name}"
        return None

    return None

def try_cloud_llm_sql(schema_ddl: str, question: str, history_text: str = "") -> Optional[str]:
    """
    Optional high-speed cloud generation if GROQ_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY is configured.
    """
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path, override=True)
    load_dotenv(override=True)

    # 1. Groq (Ultra-fast ~0.15s)
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        try:
            import requests
            prompt = f"Given this MySQL Schema:\n{schema_ddl}\n\nQuestion: {question}\nGenerate only the SQL query without explanation or markdown."
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0
                },
                timeout=5
            )
            if res.status_code == 200:
                data = res.json()
                sql = data["choices"][0]["message"]["content"].strip()
                return sql
        except Exception as e:
            print(f"Groq generation error: {e}")

    # 2. Gemini API (Free ~0.4s)
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            import requests
            prompt = f"Given this MySQL Schema:\n{schema_ddl}\n\nQuestion: {question}\nGenerate ONLY valid executable MySQL query. Do not include markdown fences or explanation."
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            res = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=5
            )
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return text
        except Exception as e:
            print(f"Gemini generation error: {e}")

    return None

def ask_ai(db_conn: DatabaseConn, question: str, history: List[ChatMessage], db: Session):
    plain_password = decrypt_db_password(db_conn.encrypted_password)
    
    # 1. Extract Full Database Schema (cached in memory)
    success, schema_info = extract_schema(
        host=db_conn.host,
        port=db_conn.port,
        user=db_conn.username,
        password=plain_password,
        database=db_conn.database_name
    )
    if not success:
        return "", None, f"Schema extraction failed: {schema_info}"

    # 2. Check Instant Rule-Based Fast Path (<5ms)
    fast_sql = try_generate_fast_sql(schema_info, question)
    if fast_sql:
        print(f"[FAST-PATH] Triggered: {fast_sql}")
        exec_success, msg, data = execute_safe_query(
            host=db_conn.host,
            port=db_conn.port,
            user=db_conn.username,
            password=plain_password,
            database=db_conn.database_name,
            sql_query=fast_sql
        )
        if exec_success:
            try:
                history_record = QueryHistory(
                    user_id=db_conn.user_id,
                    database_id=db_conn.id,
                    question=question,
                    generated_sql=fast_sql
                )
                db.add(history_record)
                db.commit()
            except Exception:
                db.rollback()
            return fast_sql, data, None

    # 3. Schema Pruning: Filter to relevant tables
    relevant_schema_info = select_relevant_schema(schema_info, question)
    schema_ddl = format_schema_ddl(relevant_schema_info)

    # 4. Build History Context
    history_text = ""
    if history:
        for msg in history[-5:]:
            history_text += f"{msg.role}: {msg.content}\n"
    
    # 5. Generate Initial SQL Query (Fast Cloud or Optimized Local LLM)
    cloud_sql = try_cloud_llm_sql(schema_ddl, question, history_text)
    if cloud_sql:
        raw_sql = cloud_sql
    else:
        engine = get_inference_engine()
        raw_sql = engine.generate_sql(schema=schema_ddl, question=question, history=history_text)
        
    sanitized_sql = sanitize_and_heal_sql(raw_sql, schema_info, question)
    
    # 6. Attempt Safe Execution
    exec_success, msg, data = execute_safe_query(
        host=db_conn.host,
        port=db_conn.port,
        user=db_conn.username,
        password=plain_password,
        database=db_conn.database_name,
        sql_query=sanitized_sql
    )
    
    final_sql = sanitized_sql

    # 7. Self-Correction Retry Loop (Self-Healing Query Execution)
    if not exec_success:
        print(f"Execution attempt failed with error: {msg}. Initiating self-correction pass...")
        try:
            full_ddl = format_schema_ddl(schema_info)
            engine = get_inference_engine()
            corrected_raw = engine.correct_sql(
                schema=full_ddl,
                question=question,
                failed_sql=sanitized_sql,
                error_msg=msg
            )
            corrected_sql = sanitize_and_heal_sql(corrected_raw, schema_info, question)
            
            # Re-execute corrected query
            retry_success, retry_msg, retry_data = execute_safe_query(
                host=db_conn.host,
                port=db_conn.port,
                user=db_conn.username,
                password=plain_password,
                database=db_conn.database_name,
                sql_query=corrected_sql
            )
            
            if retry_success:
                print("Self-correction succeeded!")
                exec_success = True
                final_sql = corrected_sql
                data = retry_data
                msg = None
            else:
                msg = f"Database Error: {retry_msg}"
        except Exception as e:
            print(f"Self-correction exception: {e}")

    # 8. Save to Query History
    try:
        history_record = QueryHistory(
            user_id=db_conn.user_id,
            database_id=db_conn.id,
            question=question,
            generated_sql=final_sql
        )
        db.add(history_record)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error recording query history: {e}")
    
    if not exec_success:
        return final_sql, None, msg
        
    return final_sql, data, None

