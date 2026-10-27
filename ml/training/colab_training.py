# ============================================================
# QLoRA Fine-Tuning: Text-to-SQL
# Model   : Qwen/Qwen2.5-1.5B-Instruct
# Dataset : b-mc2/sql-create-context
# Samples : 15,000
# GPU     : NVIDIA Tesla T4
# ============================================================

# ------------------------------------------------------------
# 1. INSTALL DEPENDENCIES
# ------------------------------------------------------------

!pip install -q -U transformers peft accelerate bitsandbytes datasets trl


# ------------------------------------------------------------
# 2. IMPORTS
# ------------------------------------------------------------

import torch

from datasets import load_dataset

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig
)

from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training
)

from trl import (
    SFTTrainer,
    SFTConfig
)


# ------------------------------------------------------------
# 3. CHECK ENVIRONMENT
# ------------------------------------------------------------

print("=" * 60)
print("ENVIRONMENT")
print("=" * 60)

print("PyTorch :", torch.__version__)
print("CUDA    :", torch.version.cuda)
print("GPU     :", torch.cuda.get_device_name(0))
print("BF16    :", torch.cuda.is_bf16_supported())

print("=" * 60)


# ------------------------------------------------------------
# 4. LOAD DATASET
# ------------------------------------------------------------

print("\nLoading dataset...")

dataset = load_dataset(
    "b-mc2/sql-create-context",
    split="train"
)

print("Original dataset size:", len(dataset))

# Shuffle and select 15,000 examples
dataset = dataset.shuffle(seed=42).select(range(15000))

print("Training examples:", len(dataset))


# ------------------------------------------------------------
# 5. FORMAT DATASET
# ------------------------------------------------------------

def format_instruction(example):

    prompt = f"""<|im_start|>system
You are a Text-to-SQL assistant. Given a database schema and a question, generate the correct SQL query. Do not explain, just output the SQL.
<|im_end|>
<|im_start|>user
Schema:
{example['context']}

Question:
{example['question']}
<|im_end|>
<|im_start|>assistant
{example['answer']}<|im_end|>"""

    return {
        "text": prompt
    }


print("\nFormatting dataset...")

formatted_dataset = dataset.map(
    format_instruction,
    remove_columns=dataset.column_names
)

print("Dataset formatting complete.")


# ------------------------------------------------------------
# 6. LOAD QWEN MODEL IN 4-BIT
# ------------------------------------------------------------

model_name = "Qwen/Qwen2.5-1.5B-Instruct"

print("\nLoading model:", model_name)

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,

    bnb_4bit_quant_type="nf4",

    bnb_4bit_use_double_quant=True,

    # Use BF16 consistently
    bnb_4bit_compute_dtype=torch.bfloat16
)

model = AutoModelForCausalLM.from_pretrained(
    model_name,

    quantization_config=bnb_config,

    device_map="auto",

    torch_dtype=torch.bfloat16
)

# Disable cache during training
model.config.use_cache = False

print("Model loaded successfully.")


# ------------------------------------------------------------
# 7. LOAD TOKENIZER
# ------------------------------------------------------------

tokenizer = AutoTokenizer.from_pretrained(
    model_name
)

tokenizer.pad_token = tokenizer.eos_token

print("Tokenizer loaded.")


# ------------------------------------------------------------
# 8. PREPARE MODEL FOR QLORA
# ------------------------------------------------------------

print("\nPreparing model for k-bit training...")

model = prepare_model_for_kbit_training(model)

print("Model prepared.")


# ------------------------------------------------------------
# 9. CONFIGURE LoRA
# ------------------------------------------------------------

lora_config = LoraConfig(

    r=16,

    lora_alpha=32,

    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj"
    ],

    lora_dropout=0.05,

    bias="none",

    task_type="CAUSAL_LM"
)

model = get_peft_model(
    model,
    lora_config
)

print("\nLoRA configuration complete.")

model.print_trainable_parameters()


# ============================================================
# TRAINING CONFIGURATION 
# ============================================================

training_args = SFTConfig(

    output_dir="./results",

    # Batch size
    per_device_train_batch_size=4,

    # Effective batch size = 4 × 4 = 16
    gradient_accumulation_steps=4,

    # Optimizer
    optim="paged_adamw_32bit",

    # Learning rate
    learning_rate=2e-4,

    # One epoch
    num_train_epochs=1,

    # BF16
    bf16=True,
    fp16=False,

    # IMPORTANT:
    # Disable gradient checkpointing because your
    # current TRL/Transformers combination has an
    # incompatible "offload" argument.
    gradient_checkpointing=False,

    max_grad_norm=0.3,

    lr_scheduler_type="constant",

    logging_steps=10,

    save_steps=100,

    max_length=512,

    dataset_text_field="text",

    seed=42
)


# ============================================================
# CREATE TRAINER
# ============================================================

trainer = SFTTrainer(
    model=model,
    train_dataset=formatted_dataset,
    processing_class=tokenizer,
    args=training_args
)

print("Trainer created successfully.")

print("\n")
print("=" * 60)
print("STARTING FINE-TUNING")
print("=" * 60)
print("\n")

trainer.train()

print("\n")
print("=" * 60)
print("TRAINING COMPLETE")
print("=" * 60)


# ============================================================
# SAVE LoRA ADAPTER
# ============================================================

new_model_name = "text-to-sql-lora-adapter"

trainer.model.save_pretrained(new_model_name)
tokenizer.save_pretrained(new_model_name)

print("\nLoRA adapter saved to:")
print(new_model_name)
