#!/usr/bin/env python3
"""
Offline Test Runner for Crusader Kings 3 Auto Translator

This script verifies that the test suite can run completely offline
by mocking network dependencies before importing the main module.
"""

import sys
import os
from unittest.mock import MagicMock

def run_offline_tests():
    """Run tests in offline mode by pre-mocking network dependencies"""

    print("🔌 Setting up offline test environment...")

    # Mock deep_translator module before any imports
    sys.modules['deep_translator'] = MagicMock()
    sys.modules['deep_translator.GoogleTranslator'] = MagicMock()

    print("✅ Network dependencies mocked")

    # Now we can safely import and run tests
    try:
        import subprocess
        import pytest

        print("🚀 Running tests in offline mode...")

        # Run pytest programmatically
        result = pytest.main([
            'tests/',
            '--tb=short',
            '--quiet',
            '-x'  # Stop on first failure
        ])

        if result == 0:
            print("✅ All tests passed in offline mode!")
            print("🎉 Test suite is fully offline-compatible!")
            return True
        else:
            print("❌ Some tests failed in offline mode")
            return False

    except Exception as e:
        print(f"❌ Error running offline tests: {e}")
        return False

if __name__ == "__main__":
    success = run_offline_tests()
    sys.exit(0 if success else 1)