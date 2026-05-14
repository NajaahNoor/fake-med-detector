#!/usr/bin/env python3
"""
validate_setup.py
-----------------
Validate that the project is correctly set up.
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Validating Fake Medicine Detector Setup")
print("=" * 60)

# Check 1: .env file
print("\n[CHECK 1] Configuration File")
if os.path.exists(".env"):
    print("✅ .env file found")
    from app.core.config import settings
    print(f"   App: {settings.app_name} v{settings.app_version}")
    print(f"   Primary LLM: {settings.primary_model}")
    print(f"   Database: {settings.db_path}")
    print(f"   OCR: PP-{settings.ocr_version} (OneDNN disabled: {settings.flags_use_onednn == 0})")
else:
    print("❌ .env file not found - using defaults")

# Check 2: CSV file
print("\n[CHECK 2] Data Files")
if os.path.exists("drap_smpc_output.csv"):
    import csv
    with open("drap_smpc_output.csv", "r") as f:
        count = sum(1 for _ in csv.DictReader(f))
    print(f"✅ DRAP CSV found with {count} drugs")
else:
    print("⚠️ CSV file not found - database will be empty")

# Check 3: Database
print("\n[CHECK 3] Database")
try:
    from app.services.database import db
    if db.is_healthy():
        print("✅ Database is accessible")
        cursor = db._get_connection().cursor()
        cursor.execute("SELECT COUNT(*) FROM drugs")
        count = cursor.fetchone()[0]
        print(f"   Drugs in database: {count}")
        db._get_connection().close()
    else:
        print("❌ Database connection failed")
except Exception as e:
    print(f"❌ Database error: {e}")

# Check 4: LLM Client
print("\n[CHECK 4] LLM Configuration")
try:
    from app.services.llm_client import llm_client
    print(f"✅ LLM client initialized")
    print(f"   Primary: {llm_client.models[0]}")
    print(f"   Fallbacks: {', '.join(llm_client.models[1:])}")
    if not llm_client.api_key:
        print("   ⚠️ WARNING: OpenRouter API key not set!")
except Exception as e:
    print(f"❌ LLM initialization error: {e}")

# Check 5: Agents
print("\n[CHECK 5] Agents")
try:
    from app.agents.intake_agent import intake_agent
    print("✅ Intake agent loaded")
except Exception as e:
    print(f"❌ Intake agent error: {e}")

try:
    from app.agents.ocr_agent import ocr_agent
    if ocr_agent.ocr_model:
        print("✅ OCR agent loaded with model")
    else:
        print("⚠️ OCR agent loaded but model unavailable")
except Exception as e:
    print(f"❌ OCR agent error: {e}")

try:
    from app.agents.verification_agent import verification_agent
    print("✅ Verification agent loaded")
except Exception as e:
    print(f"❌ Verification agent error: {e}")

try:
    from app.agents.router_agent import router_agent
    print("✅ Router agent loaded")
except Exception as e:
    print(f"❌ Router agent error: {e}")

# Check 6: Pipeline
print("\n[CHECK 6] Pipeline")
try:
    from app.services.pipeline import pipeline
    print("✅ Pipeline loaded")
except Exception as e:
    print(f"❌ Pipeline error: {e}")

# Check 7: FastAPI
print("\n[CHECK 7] FastAPI Application")
try:
    from app.main import app
    print("✅ FastAPI app initialized")
    print(f"   Routes: {len(app.routes)}")
except Exception as e:
    print(f"❌ FastAPI error: {e}")

print("\n" + "=" * 60)
print("Validation complete!")
print("=" * 60)
print("\nTo start the server, run:")
print("  python main.py")
print("\nTo test the pipeline, run:")
print("  python test_pipeline.py")
print("\nAPI Documentation:")
print("  http://localhost:8000/docs")
print("=" * 60)
