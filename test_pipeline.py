#!/usr/bin/env python3
"""
test_pipeline.py
----------------
Test script for the complete analysis pipeline.
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.database import db
from app.services.pipeline import pipeline
from app.core.logging import logger


def test_pipeline():
    """Test the complete analysis pipeline."""
    logger.info("=" * 60)
    logger.info("Testing Fake Medicine Detector Pipeline")
    logger.info("=" * 60)
    
    # Test 1: Check database
    logger.info("\n[TEST 1] Database Connection")
    if db.is_healthy():
        logger.info("✅ Database is healthy")
    else:
        logger.error("❌ Database connection failed")
        return
    
    # Test 2: Lookup a known drug
    logger.info("\n[TEST 2] Drug Lookup")
    test_reg = "134108"  # From CSV: Axaleo 400mg
    record = db.lookup_by_registration(test_reg)
    if record:
        logger.info(f"✅ Found drug: {record.get('product_name')}")
        logger.info(f"   Company: {record.get('company_name')}")
    else:
        logger.warning(f"⚠️ Drug not found: {test_reg}")
    
    # Test 3: Analyze with registration number
    logger.info("\n[TEST 3] Analysis - With Registration Number")
    result = pipeline.analyze({"registration_number": test_reg})
    logger.info(f"Verdict: {result.get('verdict')}")
    logger.info(f"Score: {result.get('score')}")
    logger.info(f"Status: {result.get('status')}")
    
    # Test 4: Analyze with text input
    logger.info("\n[TEST 4] Analysis - With Text Input")
    result = pipeline.analyze("Check registration 134108 for Axaleo 400mg")
    logger.info(f"Verdict: {result.get('verdict')}")
    logger.info(f"Status: {result.get('status')}")
    
    # Test 5: Analyze with invalid registration
    logger.info("\n[TEST 5] Analysis - With Invalid Registration")
    result = pipeline.analyze({"registration_number": "999999"})
    logger.info(f"Verdict: {result.get('verdict')}")
    logger.info(f"Score: {result.get('score')}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Pipeline testing complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        test_pipeline()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
