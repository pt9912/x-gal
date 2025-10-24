"""
Shared pytest fixtures for E2E tests.
"""

import os
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def generate_test_keys():
    """Generate JWT keys and tokens before running any tests."""
    keygen_dir = Path(__file__).parent / "docker" / "tools" / "keygen"
    keys_dir = keygen_dir / "keys"

    # Skip if keys already exist (generated manually)
    if keys_dir.exists() and (keys_dir / "private_key.pem").exists():
        print(f"\n🔑 Using existing JWT keys from {keys_dir}")
        return

    print(f"\n🔑 Generating JWT keys and tokens for E2E tests...")

    # Run generate_local.py to create keys at runtime
    generate_script = keygen_dir / "generate_local.py"
    if generate_script.exists():
        result = subprocess.run(
            ["python3", str(generate_script)], cwd=str(keygen_dir), capture_output=True, text=True
        )

        if result.returncode == 0:
            print("✅ JWT keys and tokens generated successfully")
        else:
            print(f"⚠️ Warning: Failed to generate JWT keys: {result.stderr}")
    else:
        print(f"⚠️ Warning: generate_local.py not found at {generate_script}")


@pytest.fixture(scope="session")
def docker_cleanup():
    """Ensure all test containers are cleaned up after test session."""
    yield

    # Cleanup after all tests
    print("\n🧹 Final Docker cleanup...")
    subprocess.run(["docker", "ps", "-aq", "--filter", "label=gal-test"], capture_output=True)


@pytest.fixture(scope="session")
def ensure_docker():
    """Ensure Docker and Docker Compose are available."""
    # Check Docker
    result = subprocess.run(["docker", "--version"], capture_output=True, text=True)

    if result.returncode != 0:
        pytest.skip("Docker is not available")

    # Check Docker Compose
    result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)

    if result.returncode != 0:
        # Try docker compose (v2)
        result = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
        if result.returncode != 0:
            pytest.skip("Docker Compose is not available")


@pytest.fixture
def clean_start():
    """Ensure clean state before each test."""
    # Can be used to clear specific test data
    yield
    # Cleanup after test if needed


@pytest.fixture
def test_id():
    """Generate unique test ID for correlation."""
    import uuid

    return str(uuid.uuid4())


@pytest.fixture
def timestamp():
    """Get current timestamp for log filtering."""
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) - timedelta(seconds=2)).strftime("%Y-%m-%dT%H:%M:%S")


# Markers for test categorization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "docker: marks tests that require docker")
    config.addinivalue_line("markers", "mirroring: marks tests for request mirroring feature")
    config.addinivalue_line("markers", "routing: marks tests for advanced routing feature")
    config.addinivalue_line("markers", "provider(name): marks tests for specific provider")
