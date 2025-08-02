#!/usr/bin/env python3
"""
Test runner for edge case tests.

This script runs the specific edge case tests we added to verify
they catch the issues that were fixed.
"""

import asyncio
import os
import subprocess
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_tests():
    """Run the edge case tests."""
    print("🧪 Running edge case tests...")

    # Set test environment
    os.environ["TESTING"] = "true"
    os.environ["ENVIRONMENT"] = "test"

    test_files = [
        "tests/test_environment_edge_cases.py",
        "tests/test_websocket_edge_cases.py",
        "tests/test_template_service_edge_cases.py",
    ]

    for test_file in test_files:
        print(f"\n📋 Running {test_file}...")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    test_file,
                    "-v",
                    "--tb=short",
                    "--no-header",
                ],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )

            if result.returncode == 0:
                print(f"✅ {test_file} - All tests passed!")
                print(result.stdout)
            else:
                print(f"❌ {test_file} - Some tests failed!")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)

        except Exception as e:
            print(f"💥 Error running {test_file}: {e}")

    # Also run the enhanced existing tests
    print(f"\n📋 Running enhanced existing tests...")
    enhanced_tests = [
        "tests/test_environments.py::TestEnvironmentEndpoints::test_environment_creation_resource_serialization_edge_case",
        "tests/test_environments.py::TestEnvironmentEndpoints::test_environment_creation_with_none_resources",
        "tests/test_environments.py::TestEnvironmentEndpoints::test_environment_creation_without_resources_field",
        "tests/test_api_websocket.py::TestWebSocketTerminalRegressionTests::test_websocket_terminal_tmux_session_id_unbound_error_regression",
    ]

    for test in enhanced_tests:
        print(f"\n🔍 Running {test}...")
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    test,
                    "-v",
                    "--tb=short",
                    "--no-header",
                ],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )

            if result.returncode == 0:
                print(f"✅ {test} - Passed!")
            else:
                print(f"❌ {test} - Failed!")
                print("STDERR:", result.stderr)

        except Exception as e:
            print(f"💥 Error running {test}: {e}")


if __name__ == "__main__":
    run_tests()
