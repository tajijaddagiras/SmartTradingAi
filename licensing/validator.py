"""
NexusTrade AI - Client-Side License System & Hardware Fingerprinting
Enforces SaaS licensing by binding subscription keys to unique user hardware.
Allows distributed execution without central VPS compute costs.
"""

import hashlib
import platform
import uuid
import os
from typing import Dict, Any, Optional
import requests
from config.settings import AppConfig, load_config
from core.logger import logger


class LicenseValidator:
    """Manages SaaS license verification and hardware fingerprint binding."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()

    def get_hardware_fingerprint(self) -> str:
        """
        Generates a unique, non-reversible SHA-256 machine identifier
        combining OS node, machine architecture, and system GUID.
        """
        raw_components = [
            platform.node(),
            platform.machine(),
            platform.processor(),
            str(uuid.getnode()),
            os.environ.get("COMPUTERNAME", "UNKNOWN_PC"),
        ]
        raw_string = "|".join(raw_components)
        fingerprint = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()[:32]
        return fingerprint

    def verify_license(self, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Validates the license key against licensing server or offline trial rules.
        """
        license_key = key or self.config.licensing.license_key
        hw_id = self.get_hardware_fingerprint()

        # 1. Built-in Trial Key Support for Local Development / Demo
        if license_key.startswith("NEXUS-TRIAL"):
            logger.info(f"🔑 License Validated: Trial/Evaluation License ({license_key}) active on HW #{hw_id[:8]}...")
            return {
                "valid": True,
                "tier": "TRIAL",
                "hardware_id": hw_id,
                "message": "Trial license active.",
            }

        # 2. Remote SaaS Verification Endpoint
        endpoint = self.config.licensing.api_endpoint
        try:
            payload = {
                "license_key": license_key,
                "hardware_id": hw_id,
                "os": platform.system(),
                "version": "1.0.0",
            }
            resp = requests.post(endpoint, json=payload, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("valid"):
                    logger.info(f"🔑 SaaS License confirmed: Tier {data.get('tier')} for HW #{hw_id[:8]}")
                    return data
            logger.error(f"License verification rejected by server: HTTP {resp.status_code}")
            return {"valid": False, "hardware_id": hw_id, "message": "License rejected or expired."}
        except Exception as e:
            logger.warning(f"Could not reach license verification server ({e}). Operating in offline fallback mode.")
            return {"valid": True, "tier": "OFFLINE_CACHE", "hardware_id": hw_id, "message": "Offline grace mode."}


license_validator = LicenseValidator()
