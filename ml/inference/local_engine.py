import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

class LocalInferenceEngine:
    def __init__(self, base_model_name="Qwen/Qwen2.5-1.5B-Instruct", adapter_path=None):
        """
        Initializes the 4-bit local inference engine.
        adapter_path: Path to the downloaded LoRA adapter folder from Colab.
        """
        print(f"Loading Base Model ({base_model_name}) in 4-bit precision...")
        
        # 4-bit configuration for laptop GPU
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True
        )

        # Set CPU threads for maximum multi-core performance if running on CPU
        if not torch.cuda.is_available():
            num_threads = max(1, min(os.cpu_count() or 4, 8))
            torch.set_num_threads(num_threads)
            print(f"Configured PyTorch CPU threads: {num_threads}")

        self.tokenizer = AutoTokenizer.from_pretrained(base_model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            quantization_config=bnb_config,
            device_map="auto" # Automatically offloads to GPU (if available) or CPU
        )

        # Snap on the LoRA adapter if provided
        if adapter_path and os.path.exists(adapter_path):
            print(f"Loading LoRA Adapter from {adapter_path}...")
            self.model = PeftModel.from_pretrained(self.model, adapter_path)
            print("Adapter successfully loaded!")
        else:
            print("Warning: No valid adapter path provided. Running purely on base model.")

    def generate_sql(self, schema: str, question: str, history: str = "") -> str:
        """
        Generates a SQL query based on the schema and question.
        """
        prompt = f"""<|im_start|>system
You are an expert Text-to-SQL generator for MySQL. Given a database schema and a question, generate the correct SQL query.
Rules:
1. For simple listing, fetching, or counting records from a table (e.g., "list all doctors", "count students"), use a simple SELECT from that table WITHOUT any JOINs.
2. Only JOIN tables when the question explicitly requires data from multiple tables.
3. Use ONLY columns that exist in the Schema.
4. When searching text/names, use LIKE '%keyword%'.
Do not explain, output only the SQL query.
<|im_end|>
<|im_start|>user
{f'Conversation Context:\n{history}\n\n' if history else ''}Schema:
{schema}

Question:
{question}
<|im_end|>
<|im_start|>assistant
"""
        return self._generate(prompt)

    def correct_sql(self, schema: str, question: str, failed_sql: str, error_msg: str) -> str:
        """
        Self-correction: Generates a fixed SQL query given a previous failure and database error.
        """
        prompt = f"""<|im_start|>system
You are a Text-to-SQL assistant. The previous MySQL query failed with an error. Fix the query so it is valid and executes successfully.
Rules:
1. Do not use undeclared table aliases.
2. Only reference valid columns from the Schema.
3. Do not join unnecessary tables.
Do not explain, output only the corrected SQL query.
<|im_end|>
<|im_start|>user
Schema:
{schema}

Question:
{question}

Failed SQL:
{failed_sql}

Error:
{error_msg}
<|im_end|>
<|im_start|>assistant
"""
        return self._generate(prompt)

    def _generate(self, prompt: str) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=65,
                temperature=0.01,   # Deterministic greedy generation
                do_sample=False,
                use_cache=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        try:
            sql_output = generated_text.split("assistant\n")[-1].strip()
            # If the model added markdown blocks like ```sql ... ```, clean them up
            if sql_output.startswith("```sql"):
                sql_output = sql_output[6:]
            elif sql_output.startswith("```"):
                sql_output = sql_output[3:]
            if sql_output.endswith("```"):
                sql_output = sql_output[:-3]
            # Take only the first complete SQL query line if extra text was emitted
            first_stmt = sql_output.split(";")[0].strip()
            return (first_stmt + ";") if first_stmt else sql_output.strip()
        except Exception:
            return generated_text.strip()


# Quick test stub if executed directly
if __name__ == "__main__":
    print("Testing Local Inference Engine Initialization...")
    engine = LocalInferenceEngine()
    test_schema = "students(id, name, branch, cgpa)"
    test_q = "Show students with CGPA greater than 8.5"
    print("Test Input:", test_q)
    print("Generated SQL:", engine.generate_sql(test_schema, test_q))
