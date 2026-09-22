import os
import subprocess
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]


def _get_project_root() -> Path:
    return Path(__file__).parent.parent.parent


def test_docker_compose_structure_and_security_isolation() -> None:
    root = _get_project_root()
    compose_path = root / "deploy" / "vm" / "docker-compose.yml"
    assert compose_path.exists(), f"Compose file not found at {compose_path}"

    with compose_path.open("r", encoding="utf-8") as f:
        config: dict[str, Any] = cast(dict[str, Any], yaml.safe_load(f))

    assert "services" in config, "Missing 'services' block in docker-compose.yml"
    services: dict[str, Any] = config["services"]

    required_services = {"caddy", "frontend", "api", "postgres", "falkordb", "redis"}
    assert set(services.keys()) == required_services, (
        f"Expected services {required_services}, but found {set(services.keys())}"
    )

    # Security verification: only Caddy should have host ports mapped
    assert "ports" in services["caddy"], "Caddy must map ports for public ingress (80 and 443)"
    caddy_ports = services["caddy"]["ports"]
    assert "80:80" in caddy_ports
    assert "443:443" in caddy_ports

    # Crucial security assertion: databases and API MUST NOT expose ports on host
    internal_services = ["postgres", "falkordb", "redis", "api", "frontend"]
    for service_name in internal_services:
        assert "ports" not in services[service_name], (
            f"Security violation: Service '{service_name}' must not expose ports to host. "
            "It must only communicate over the internal Docker network."
        )

    # Healthcheck verification
    for service_name in ["postgres", "falkordb", "redis", "api", "frontend"]:
        assert "healthcheck" in services[service_name], (
            f"Service '{service_name}' is missing a healthcheck block"
        )

    # Persistence verification: verify volume mounts
    assert any("postgres" in str(v) for v in services["postgres"]["volumes"])
    assert any("falkordb" in str(v) for v in services["falkordb"]["volumes"])
    assert any("redis" in str(v) for v in services["redis"]["volumes"])
    assert any("storage" in str(v) for v in services["api"]["volumes"])
    assert any("credentials" in str(v) for v in services["api"]["volumes"])
    assert any("caddy_data" in str(v) for v in services["caddy"]["volumes"])

    # Network verification
    assert "networks" in config
    assert "substrate_net" in config["networks"]
    for s_name, s_conf in services.items():
        assert "networks" in s_conf, f"Service '{s_name}' is not attached to networks"
        assert "substrate_net" in s_conf["networks"], (
            f"Service '{s_name}' must join 'substrate_net'"
        )


def test_caddyfile_configuration_and_routes() -> None:
    root = _get_project_root()
    caddyfile_path = root / "deploy" / "vm" / "Caddyfile"
    assert caddyfile_path.exists(), f"Caddyfile not found at {caddyfile_path}"

    content = caddyfile_path.read_text(encoding="utf-8")

    # TLS / ACME email placeholder
    assert "email {$ACME_EMAIL" in content

    # Domain binding placeholder
    assert "{$DOMAIN_NAME:localhost}" in content

    # Compression
    assert "encode zstd gzip" in content

    # API and docs reverse proxy routes
    assert "handle /api/*" in content
    assert "reverse_proxy api:8000" in content
    assert "handle /docs*" in content
    assert "handle /openapi.json" in content

    # Frontend SPA reverse proxy route
    assert "reverse_proxy frontend:80" in content

    # Forwarding headers
    assert "X-Forwarded-Proto" in content
    assert "X-Real-IP" in content


def test_env_example_contains_all_required_settings() -> None:
    root = _get_project_root()
    env_example_path = root / "deploy" / "vm" / ".env.example"
    assert env_example_path.exists(), f".env.example not found at {env_example_path}"

    content = env_example_path.read_text(encoding="utf-8")

    required_vars = [
        "ENVIRONMENT=production",
        "DOMAIN_NAME=",
        "ACME_EMAIL=",
        "POSTGRES_HOST=postgres",
        "POSTGRES_PORT=5432",
        "POSTGRES_USER=postgres",
        "POSTGRES_PASSWORD=",
        "POSTGRES_DB=agentic_substrate",
        "FALKORDB_HOST=falkordb",
        "FALKORDB_PORT=6379",
        "REDIS_HOST=redis",
        "REDIS_PORT=6379",
        "STORAGE_TYPE=local",
        "STORAGE_LOCAL_BASE_DIR=/app/data/storage",
        "OPENROUTER_API_KEY=",
        "GEMINI_API_KEY=",
        "GOOGLE_APPLICATION_CREDENTIALS=",
    ]

    for var_entry in required_vars:
        assert var_entry in content, f"Missing expected variable configuration: {var_entry}"


def test_setup_script_syntax_and_permissions() -> None:
    root = _get_project_root()
    setup_script = root / "deploy" / "vm" / "setup.sh"
    assert setup_script.exists(), f"setup.sh not found at {setup_script}"

    # Verify script is executable
    assert os.access(setup_script, os.X_OK), (
        "deploy/vm/setup.sh must have executable permissions (chmod +x)"
    )

    # Verify bash syntax without executing
    result = subprocess.run(
        ["bash", "-n", str(setup_script)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"setup.sh syntax error: {result.stderr}"
