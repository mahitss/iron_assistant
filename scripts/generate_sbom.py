#!/usr/bin/env python3
"""
Kairo Software Bill of Materials (SBOM) Generator
Generates an audit-ready SBOM for Kairo V1.1.0 across backend Python packages,
frontend npm packages, and system runtime components.

Zero secrets or environmental credentials included.
"""

import argparse
import datetime
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List


def get_system_runtime() -> Dict[str, Any]:
    return {
        "os_name": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": sys.version.split()[0],
        "python_compiler": platform.python_compiler(),
    }


def get_backend_dependencies() -> List[Dict[str, str]]:
    deps = []
    # 1. Inspect importlib.metadata if available
    try:
        import importlib.metadata as importlib_metadata
        for dist in importlib_metadata.distributions():
            deps.append({
                "name": dist.metadata["Name"],
                "version": dist.version,
                "type": "pypi"
            })
    except Exception:
        pass

    # 2. Fallback or cross-reference pyproject.toml
    pyproject_path = Path(__file__).resolve().parent.parent / "backend" / "pyproject.toml"
    if pyproject_path.exists():
        try:
            content = pyproject_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith('"') and ('==' in line or '>=' in line):
                    cleaned = line.strip('",')
                    deps.append({
                        "name": cleaned.split(">=")[0].split("==")[0],
                        "specifier": cleaned,
                        "type": "pypi_spec"
                    })
        except Exception:
            pass

    # Deduplicate by name
    seen = set()
    deduped = []
    for d in deps:
        if d["name"] not in seen:
            seen.add(d["name"])
            deduped.append(d)
    return sorted(deduped, key=lambda x: x["name"].lower())


def get_frontend_dependencies() -> List[Dict[str, str]]:
    deps = []
    package_json_path = Path(__file__).resolve().parent.parent / "frontend" / "package.json"
    if package_json_path.exists():
        try:
            data = json.loads(package_json_path.read_text(encoding="utf-8"))
            for name, ver in data.get("dependencies", {}).items():
                deps.append({"name": name, "version": str(ver), "scope": "runtime", "type": "npm"})
            for name, ver in data.get("devDependencies", {}).items():
                deps.append({"name": name, "version": str(ver), "scope": "development", "type": "npm"})
        except Exception as e:
            print(f"[WARN] Failed to parse frontend package.json: {e}")
    return sorted(deps, key=lambda x: x["name"].lower())


def generate_sbom(app_version: str = "1.1.0") -> Dict[str, Any]:
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    system_runtime = get_system_runtime()
    backend_deps = get_backend_dependencies()
    frontend_deps = get_frontend_dependencies()

    sbom = {
        "bomFormat": "CycloneDX-JSON-Subset",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:kairo-sbom-{app_version}",
        "version": 1,
        "metadata": {
            "timestamp": timestamp,
            "component": {
                "name": "kairo",
                "version": app_version,
                "description": "Kairo Autonomous AI Assistant Platform",
                "type": "application"
            },
            "system_runtime": system_runtime
        },
        "components": {
            "backend_python_packages": {
                "count": len(backend_deps),
                "packages": backend_deps
            },
            "frontend_npm_packages": {
                "count": len(frontend_deps),
                "packages": frontend_deps
            }
        }
    }
    return sbom


def main():
    parser = argparse.ArgumentParser(description="Generate Kairo V1.1.0 SBOM")
    parser.add_argument("--output", default="sbom.json", help="Output file path")
    parser.add_argument("--version", default="1.1.0", help="Application version")
    args = parser.parse_args()

    sbom = generate_sbom(app_version=args.version)
    out_path = Path(args.output)
    out_path.write_text(json.dumps(sbom, indent=2), encoding="utf-8")
    
    b_count = sbom["components"]["backend_python_packages"]["count"]
    f_count = sbom["components"]["frontend_npm_packages"]["count"]
    print(f"[OK] SBOM generated successfully -> {out_path.resolve()}")
    print(f"     Application: Kairo v{args.version}")
    print(f"     Python dependencies: {b_count}")
    print(f"     NPM dependencies:    {f_count}")
    print(f"     Runtime OS:          {sbom['metadata']['system_runtime']['os_name']} ({sbom['metadata']['system_runtime']['architecture']})")


if __name__ == "__main__":
    main()
