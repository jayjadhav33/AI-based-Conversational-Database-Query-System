# 🧠 AI-Based Conversational Database Query System
### *Enterprise Natural Language to SQL Assistant with QLoRA Fine-Tuned LLM & Self-Healing Query Execution*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2+-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-8.2+-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.14+-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org)
[![HuggingFace PEFT](https://img.shields.io/badge/PEFT-QLoRA%204--bit-FFD21E?style=flat&logo=huggingface&logoColor=black)](https://github.com/huggingface/peft)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=flat&logo=mysql&logoColor=white)](https://www.mysql.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An intelligent, full-stack database exploration platform that transforms natural language questions into accurate, executable MySQL queries in real time. Powered by a custom **QLoRA fine-tuned Qwen 2.5 (1.5B)** language model, an **AST-based SQL security validator**, and an **automatic self-correction feedback loop**, this system allows technical and non-technical stakeholders alike to converse directly with complex relational databases.

---

## 📑 Table of Contents
1. [Key Features](#-key-features)
2. [System Architecture](#-system-architecture)
3. [Technology Stack](#-technology-stack)
4. [Machine Learning Pipeline](#-machine-learning-pipeline)
5. [Repository Structure](#-repository-structure)
6. [Getting Started & Installation](#-getting-started--installation)
   - [Prerequisites](#prerequisites)
   - [1. Backend Setup](#1-backend-setup)
   - [2. Database Configuration](#2-database-configuration)
   - [3. Frontend Setup](#3-frontend-setup)
7. [Running the Application](#-running-the-application)
8. [API Reference](#-api-reference)
9. [Security & Safe Execution](#-security--safe-execution)
10. [Sample Queries & Benchmarks](#-sample-queries--benchmarks)
11. [License](#-license)

---

## ✨ Key Features

- **🗣️ Conversational Text-to-SQL**: Ask questions in everyday conversational English (e.g., *"Find all patients diagnosed with Hypertension older than 50"*, *"What is our total revenue from electronics this month?"*) and receive accurate SQL instantly.
- **⚡ Two-Tier Hybrid Query Engine**:
  - **Tier 1 (Instant Fast-Path)**: Sub-10ms rule-based engine resolving high-frequency queries, aggregations (`SUM`, `AVG`, `COUNT`), entity searches, and column filters.
  - **Tier 2 (Fine-Tuned LLM)**: Specialized 4-bit quantized `Qwen2.5-1.5B` LoRA model for complex multi-table relationships and join inference.
- **🔄 Self-Healing / Self-Correction Loop**: If a generated query encounters a database execution error (e.g., column mismatch or invalid grouping), the system catches the error, passes the error stack and DDL back into the correction model, and repairs the SQL on the fly before returning results to the user.
- **🛡️ AST-Level Read-Only Security Guardrails**: Built-in AST parser (`sqlparse`) guarantees only non-destructive `SELECT` statements are executed. Blocks all multi-statement SQL injection attacks and mutations (`DROP`, `DELETE`, `UPDATE`, `ALTER`).
- **🗄️ Multi-Database Connection Hub**: Connect, test, and switch between multiple MySQL databases effortlessly. Passwords are encrypted at rest using **Fernet AES-128** encryption.
- **📊 Automatic Dynamic Schema Extraction**: Automatically inspects table definitions, column types, primary keys, and foreign-key constraints with an in-memory TTL cache.
- **🔐 Secure Authentication**: Includes email/password authentication using **Bcrypt** hashing and **JWT** session tokens, plus native **Google OAuth 2.0** Single Sign-On.
- **💻 Modern Glassmorphism Dashboard**: React 19 single-page app with interactive data tables, SQL syntax highlighting, query history logger, and database switching.

---

## 🏛️ System Architecture

```
                    ┌────────────────────────────────────────┐
                    │      React 19 + Vite Frontend UI       │
                    │   (Authentication, Dashboard, Chat)    │
                    └───────────────────┬────────────────────┘
                                        │ REST API (JWT)
                                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Backend Service                          │
│                                                                            │
│  ┌───────────────────────┐   ┌───────────────────┐   ┌───────────────────┐ │
│  │   Auth & Security     │   │ Dynamic Database  │   │ Schema Extractor  │ │
│  │ (JWT, Bcrypt, Fernet) │   │  Connection Pool  │   │  & In-Memory TTL  │ │
│  └───────────────────────┘   └───────────────────┘   └───────────────────┘ │
│                                                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                     Hybrid Text-to-SQL Engine                         │ │
│  │                                                                       │ │
│  │  1. Fast-Path Engine (<10ms)  ───► High-Frequency Aggregations/Filters │ │
│  │                                                                       │ │
│  │  2. Local ML Inference Engine ───► Qwen2.5-1.5B + LoRA (NF4 4-bit)    │ │
│  │                                                                       │ │
│  │  3. AST SQL Validator        ───► sqlparse Strict Read-Only (SELECT) │ │
│  │                                                                       │ │
│  │  4. Self-Healing Loop         ───► Catches Error ──► Re-prompt Fix    │ │
│  └───────────────────────────────────┬───────────────────────────────────┘ │
└──────────────────────────────────────┼─────────────────────────────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
         ┌─────────────────────────┐       ┌─────────────────────────┐
         │ Application DB (MySQL)  │       │ Target DBs (Hospital,   │
         │ - users                 │       │  Inventory, E-commerce) │
         │ - databases             │       └─────────────────────────┘
         │ - query_history         │
         └─────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, Vite 8, Lucide React, Axios, React Router v7, `@react-oauth/google` |
| **Backend API** | Python 3.12, FastAPI, Uvicorn, Pydantic v2, Python-Jose (JWT), Passlib & Bcrypt |
| **Database & ORM** | MySQL 8.0, SQLAlchemy 2.0, PyMySQL, Cryptography (Fernet) |
| **Model & Inference** | PyTorch 2.14, Hugging Face Transformers, PEFT, BitsAndBytes (NF4 4-bit quantization) |
| **Fine-Tuning** | QLoRA (Rank $r=16$, Alpha $\alpha=32$), TRL `SFTTrainer`, NVIDIA Tesla T4 |
| **Dataset** | `b-mc2/sql-create-context` (15,000 curated schema-query pairs) |
| **SQL Security** | `sqlparse` (AST validation, multi-statement injection blocking) |

---

## 🔬 Machine Learning Pipeline

### Base Model & Adaptation
- **Base LLM**: `Qwen/Qwen2.5-1.5B-Instruct`
- **Method**: QLoRA (Quantized Low-Rank Adaptation)
- **Precision**: 4-bit NormalFloat (NF4) with double quantization
- **LoRA Hyperparameters**:
  - Rank ($r$): 16
  - Alpha ($\alpha$): 32
  - Dropout: 0.05
  - Target Modules: `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`

### Training Specifications
- **Dataset**: 15,000 paired natural language questions, DDL contexts, and target queries from `b-mc2/sql-create-context`.
- **Training Artifacts**: Pre-packaged under `ml/models/text-to-sql-lora-adapter/` with `adapter_model.safetensors` (~36.9 MB), ready for instant local offline loading without retraining.

---

## 📁 Repository Structure

```plaintext
.
├── backend/
│   ├── app/
│   │   ├── api/             # API route handlers (auth, databases, schema, query, ai)
│   │   ├── models/          # SQLAlchemy ORM models (User, DatabaseConn, QueryHistory)
│   │   ├── schemas/         # Pydantic validation schemas
│   │   ├── security/        # JWT handling, password hashing, Fernet encryption
│   │   ├── services/        # AI service, schema service, safe query runner, validator
│   │   ├── db.py            # Database engine and session factory
│   │   └── main.py          # FastAPI application initialization & CORS
│   ├── .env.example         # Template for backend environment variables
│   └── requirements.txt     # Python backend dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/           # Login, Register, Dashboard views
│   │   ├── App.jsx          # Protected routing setup
│   │   ├── main.jsx         # App mounting & GoogleOAuthProvider
│   │   └── index.css        # Core design system & theme tokens
│   ├── .env.example         # Template for frontend environment variables
│   ├── package.json         # Node.js dependencies
│   └── vite.config.js       # Vite build configuration
├── ml/
│   ├── dataset/             # 15K sample dataset in JSON, JSONL, and CSV formats
│   ├── evaluation/          # Automated model evaluation scripts
│   ├── inference/           # 4-bit local inference engine (local_engine.py)
│   ├── models/              # Pre-trained LoRA adapter weights (safetensors)
│   └── training/            # Colab training script for QLoRA fine-tuning
├── Database Questions.txt   # Sample natural language test prompts
└── README.md                # Project documentation
```

---

## 🚀 Getting Started & Installation

### Prerequisites
- **Python**: 3.10 to 3.12
- **Node.js**: v18.0 or higher
- **MySQL Server**: 8.0 or higher running locally or remotely

---

### 1. Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   - **Windows**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **Linux / macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install ML Inference dependencies** (for local LLM execution):
   ```bash
   pip install torch transformers peft bitsandbytes accelerate
   ```

5. **Configure Environment Variables**:
   Copy the `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your settings:
   ```ini
   # MySQL Application Database
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   DB_NAME=ai_query_db

   # JWT & Encryption
   SECRET_KEY=your_super_secret_random_key_here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=120

   # Optional Google OAuth
   GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com

   # Optional Cloud LLM Fallbacks (for ultra-fast cloud generation)
   GROQ_API_KEY=
   GEMINI_API_KEY=
   ```

---

### 2. Database Configuration

1. **Log in to MySQL** and create the application database:
   ```sql
   CREATE DATABASE IF NOT EXISTS ai_query_db;
   ```
   *(FastAPI automatically creates the `users`, `databases`, and `query_history` tables on initial startup).*

2. *(Optional)* **Set up a sample target database** (e.g., a hospital or inventory system) to test querying immediately.

---

### 3. Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd ../frontend
   ```

2. **Install Node dependencies**:
   ```bash
   npm install
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Configure `.env`:
   ```ini
   VITE_API_URL=http://localhost:8000/api
   VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   ```

---

## 🏃 Running the Application

### Option A: Running Development Servers

1. **Start the FastAPI Backend**:
   ```bash
   cd backend
   venv\Scripts\activate      # Windows (or source venv/bin/activate on Linux)
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   - Server: `http://127.0.0.1:8000`
   - Swagger Documentation: `http://127.0.0.1:8000/docs`

2. **Start the Vite Frontend** (in a separate terminal):
   ```bash
   cd frontend
   npm run dev
   ```
   - UI Interface: `http://localhost:5173`

---

## 📡 API Reference

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/auth/register` | Register a new local user account | No |
| `POST` | `/api/auth/login` | Authenticate credentials & issue JWT token | No |
| `POST` | `/api/auth/google` | Single Sign-On via Google OAuth ID token | No |
| `GET` | `/api/auth/me` | Fetch authenticated user profile | **Yes** |
| `GET` | `/api/databases/` | List all saved databases for current user | **Yes** |
| `POST` | `/api/databases/` | Add & encrypt new database credentials | **Yes** |
| `POST` | `/api/databases/test` | Test MySQL connection without saving | **Yes** |
| `DELETE`| `/api/databases/{id}` | Remove saved database and cascade query logs | **Yes** |
| `GET` | `/api/schema/{id}` | Extract schema (tables, columns, types, keys) | **Yes** |
| `POST` | `/api/query/{id}` | Execute validated read-only SQL query | **Yes** |
| `POST` | `/api/ai/ask/{id}` | Convert natural language to SQL & execute | **Yes** |
| `GET` | `/api/ai/history` | Retrieve user's previous query history | **Yes** |

---

## 🛡️ Security & Safe Execution

1. **Strict SELECT-Only Enforcement**:
   Every incoming query is parsed into an Abstract Syntax Tree (AST) using `sqlparse`. Any query containing `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, or `GRANT` is rejected before reaching the database.
2. **Multi-Statement Blocking**:
   Disallows multiple statements separated by `;` to thwart stacked SQL injection vectors (e.g., `SELECT * FROM users; DROP TABLE products;`).
3. **Encrypted Database Credentials at Rest**:
   Customer database passwords are encrypted with **Fernet (symmetric 128-bit AES)** derived from `SECRET_KEY`. Passwords are only decrypted in memory during the execution lifecycle.
4. **Isolated User Sandboxing**:
   Users can only query, modify, or view database configurations explicitly registered to their own account identity.

---

## 💡 Sample Queries & Benchmarks

| Question | Generated SQL | Latency |
| :--- | :--- | :---: |
| *"List all doctors"* | `SELECT * FROM doctors;` | **< 5ms** *(Fast-Path)* |
| *"How many patients are registered?"* | `SELECT COUNT(*) FROM patients;` | **< 5ms** *(Fast-Path)* |
| *"Find Dr. Amit Joshi"* | `SELECT * FROM doctors WHERE name LIKE '%Amit%Joshi%';` | **< 8ms** *(Fast-Path)* |
| *"Show products where quantity is less than 10"* | `SELECT * FROM products WHERE quantity < 10;` | **< 8ms** *(Fast-Path)* |
| *"Show appointments joined with doctor details"* | `SELECT T1.*, T2.name FROM appointments AS T1 JOIN doctors AS T2 ON T1.doctor_id = T2.doctor_id;` | **~1.2s** *(LoRA Model)* |

---

## 📄 License

This project is licensed under the **MIT License** — feel free to use, modify, and distribute it for academic or commercial purposes.
