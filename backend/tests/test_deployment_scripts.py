"""Tests validating deployment scripts and environment templates."""

from pathlib import Path


def test_deployment_scripts_exist_and_use_safe_shell_settings():
    """Verify all deployment scripts exist with proper shebang and -euo pipefail."""
    scripts_dir = Path(__file__).parent.parent.parent / "deploy" / "scripts"
    assert scripts_dir.exists(), f"Scripts directory not found: {scripts_dir}"

    expected_scripts = [
        "deploy.sh",
        "migrate.sh",
        "rollback.sh",
        "healthcheck.sh",
        "smoke-test.sh",
    ]

    for script_name in expected_scripts:
        script_path = scripts_dir / script_name
        assert script_path.exists(), f"Expected script {script_name} not found"

        content = script_path.read_text(encoding="utf-8")
        assert content.startswith("#!/usr/bin/env bash"), f"{script_name} must start with bash shebang"
        assert "set -euo pipefail" in content, f"{script_name} must use set -euo pipefail for safe execution"


def test_rollback_script_database_safety():
    """Verify rollback.sh explicitly warns against automatic database downgrades."""
    rollback_script = Path(__file__).parent.parent.parent / "deploy" / "scripts" / "rollback.sh"
    content = rollback_script.read_text(encoding="utf-8")

    assert "DOES NOT automatically downgrade database migrations" in content
    assert "expand/contract" in content
    assert "PREVIOUS_IMAGE_TAG" in content or "PREVIOUS_TAG" in content


def test_smoke_test_script_coverage():
    """Verify smoke-test.sh checks core endpoints and safety gates."""
    smoke_script = Path(__file__).parent.parent.parent / "deploy" / "scripts" / "smoke-test.sh"
    content = smoke_script.read_text(encoding="utf-8")

    assert "/health/live" in content
    assert "/health/ready" in content
    assert "/health/version" in content
    assert "/metrics" in content
    assert "Computer Control Disabled" in content
    assert "Emergency Stop Endpoint Available" in content


def test_environment_separation_templates():
    """Verify development, staging, and production environment templates."""
    env_dir = Path(__file__).parent.parent.parent / "deploy" / "environments"
    assert env_dir.exists(), f"Environments directory not found: {env_dir}"

    dev_env = (env_dir / "development.env.example").read_text(encoding="utf-8")
    stg_env = (env_dir / "staging.env.example").read_text(encoding="utf-8")
    prod_env = (env_dir / "production.env.example").read_text(encoding="utf-8")

    # Verify environment values
    assert "ENVIRONMENT=development" in dev_env
    assert "ENVIRONMENT=testing" in stg_env
    assert "ENVIRONMENT=production" in prod_env

    # Verify computer control safety in cloud environments
    assert "KAIRO_COMPUTER_ENABLED=false" in prod_env
    assert "KAIRO_COMPUTER_ENABLED=false" in stg_env

    # Verify no wildcard CORS in production
    assert "ALLOWED_ORIGINS=*" not in prod_env
    assert "ALLOWED_ORIGINS=https://app.example.com" in prod_env

    # Verify database URLs are separated
    assert "kairo_dev" in dev_env
    assert "kairo_staging" in stg_env
    assert "kairo_production" in prod_env
