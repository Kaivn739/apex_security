from __future__ import annotations

import argparse
import hashlib
import hmac
import ipaddress
import json
import os
import re
import shutil
import sqlite3

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit


class APEXCyberShield:
    """
    APEX Cyber Shield - Controlled Integrity Protection

    Features:
    1. Local endpoint validation.
    2. SHA-256 integrity verification.
    3. HMAC manifest validation.
    4. Append-only audit logging (application-level).
    5. Protected SQLite snapshots.
    6. Explicit baseline initialization/replacement.

    IMPORTANT:
    This module does not enforce system-wide network isolation.
    """

    VERSION = "2.0.0"
    MANIFEST_VERSION = 2

    def __init__(
        self,
        project_root: Optional[Path] = None,
        db_name: str = "apex_security.db",
    ) -> None:

        self.project_root = (
            project_root or Path(__file__).resolve().parent
        ).resolve()

        self.db_path = self.project_root / db_name

        self.vault_dir = self.project_root / ".apex_shield_vault"

        self.manifest_path = (
            self.vault_dir / "integrity_manifest.json"
        )

        self.audit_log_path = (
            self.vault_dir / "shield_audit.log"
        )

        self.backup_dir = (
            self.vault_dir / "db_snapshots"
        )

        self._machine_key = self._derive_local_machine_key()

        self._ensure_vault_structure()

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def _ensure_vault_structure(self) -> None:

        self.vault_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.backup_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _derive_local_machine_key(self) -> bytes:
        """
        Preserve compatibility with the previous manifest format.

        NOTE:
        This deterministic key is NOT a hardware-backed secret.
        It protects against accidental manifest corruption, but
        cannot guarantee protection against an attacker who can
        modify the application and read its source.
        """

        raw_identity = (
            f"{os.name}|{self.project_root}|"
            "APEX_STEEL_SHIELD_2026"
        ).encode("utf-8")

        return hashlib.sha256(raw_identity).digest()

    # =========================================================
    # AUDIT LOG
    # =========================================================

    def _log_security_event(
        self,
        level: str,
        message: str,
    ) -> None:

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Prevent forged additional log lines.
        safe_message = str(message).replace(
            "\r", " "
        ).replace(
            "\n", " "
        )

        line = (
            f"[{timestamp}] [{level}] "
            f"{safe_message}\n"
        )

        try:

            with open(
                self.audit_log_path,
                "a",
                encoding="utf-8",
            ) as file:

                file.write(line)
                file.flush()
                os.fsync(file.fileno())

        except OSError:
            # Never silently claim that the event was logged.
            raise

    # =========================================================
    # HASHING
    # =========================================================

    @staticmethod
    def compute_file_sha256(
        file_path: Path,
    ) -> str:

        hasher = hashlib.sha256()

        with open(file_path, "rb") as file:

            for chunk in iter(
                lambda: file.read(65536),
                b"",
            ):

                hasher.update(chunk)

        return hasher.hexdigest()

    def _sign_payload(
        self,
        payload_text: str,
    ) -> str:

        return hmac.new(
            self._machine_key,
            payload_text.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    # =========================================================
    # MANIFEST VALIDATION
    # =========================================================

    def _load_manifest(self) -> Dict[str, Any]:

        with open(
            self.manifest_path,
            "r",
            encoding="utf-8",
        ) as file:

            envelope = json.load(file)

        if not isinstance(envelope, dict):
            raise ValueError("Manifest must be a JSON object.")

        stored_files = envelope.get("files")

        if not isinstance(stored_files, dict):
            raise ValueError("Manifest files field is invalid.")

        for filename, file_hash in stored_files.items():

            if not isinstance(filename, str):
                raise ValueError("Invalid filename in manifest.")

            if not isinstance(file_hash, str):
                raise ValueError("Invalid file hash in manifest.")

            # Only root-level Python filenames are accepted.
            if (
                Path(filename).name != filename
                or filename in ("", ".", "..")
                or not filename.endswith(".py")
            ):
                raise ValueError(
                    f"Unsafe manifest filename: {filename}"
                )

            if not re.fullmatch(
                r"[a-fA-F0-9]{64}",
                file_hash,
            ):
                raise ValueError(
                    f"Invalid SHA-256 value for: {filename}"
                )

        return envelope

    # =========================================================
    # BASELINE CREATION
    # =========================================================

    def build_integrity_baseline(
        self,
        replace_existing: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a baseline only through an explicit operation.

        Existing baselines cannot be replaced accidentally.
        """

        if self.manifest_path.exists() and not replace_existing:

            raise FileExistsError(
                "Existing integrity baseline detected. "
                "Explicit replacement is required."
            )

        hashes: Dict[str, str] = {}

        for py_file in sorted(
            self.project_root.glob("*.py")
        ):

            if not py_file.is_file():
                continue

            hashes[py_file.name] = (
                self.compute_file_sha256(py_file)
            )

        raw_json = json.dumps(
            hashes,
            sort_keys=True,
        )

        envelope = {
            "manifest_version": self.MANIFEST_VERSION,
            "shield_version": self.VERSION,
            "updated_at": datetime.now().isoformat(),
            "file_count": len(hashes),
            "files": hashes,
            "signature": self._sign_payload(raw_json),
        }

        # Write atomically.
        temporary_path = self.manifest_path.with_suffix(
            ".json.tmp"
        )

        try:

            with open(
                temporary_path,
                "w",
                encoding="utf-8",
            ) as file:

                json.dump(
                    envelope,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

                file.flush()
                os.fsync(file.fileno())

            os.replace(
                temporary_path,
                self.manifest_path,
            )

        finally:

            if temporary_path.exists():
                temporary_path.unlink()

        self._log_security_event(
            "INFO",
            (
                f"Integrity baseline created. "
                f"Files={len(hashes)}, "
                f"Replacement={replace_existing}"
            ),
        )

        return envelope

    # =========================================================
    # INTEGRITY VERIFICATION
    # =========================================================

    def verify_integrity(self) -> Dict[str, Any]:

        if not self.manifest_path.exists():

            self._log_security_event(
                "WARNING",
                "Integrity manifest is missing. No baseline created.",
            )

            return {
                "status": "BASELINE_MISSING",
                "signature_valid": False,
                "tampered_files": [],
                "missing_files": [],
                "new_unverified_files": [],
                "protected_count": 0,
            }

        try:

            envelope = self._load_manifest()

        except Exception as error:

            self._log_security_event(
                "CRITICAL",
                f"Manifest validation failed: {error}",
            )

            return {
                "status": "MANIFEST_INVALID",
                "signature_valid": False,
                "tampered_files": [],
                "missing_files": [],
                "new_unverified_files": [],
                "protected_count": 0,
            }

        stored_files: Dict[str, str] = envelope["files"]

        raw_json = json.dumps(
            stored_files,
            sort_keys=True,
        )

        expected_signature = self._sign_payload(
            raw_json
        )

        signature_valid = hmac.compare_digest(
            expected_signature,
            str(envelope.get("signature", "")),
        )

        tampered: List[str] = []
        missing: List[str] = []
        new_files: List[str] = []

        # Check previously protected files.
        for filename, old_hash in stored_files.items():

            target = self.project_root / filename

            if not target.is_file():

                missing.append(filename)
                continue

            try:

                current_hash = (
                    self.compute_file_sha256(target)
                )

                if not hmac.compare_digest(
                    current_hash,
                    old_hash,
                ):

                    tampered.append(filename)

            except OSError:

                missing.append(filename)

        # Detect newly added Python files.
        for py_file in sorted(
            self.project_root.glob("*.py")
        ):

            if py_file.name not in stored_files:

                new_files.append(py_file.name)

        if not signature_valid:

            status = "SIGNATURE_INVALID"

        elif tampered or missing:

            status = "ALERT_TAMPER_DETECTED"

        elif new_files:

            status = "NEW_FILES_UNVERIFIED"

        else:

            status = "SECURE"

        if status != "SECURE":

            self._log_security_event(
                "CRITICAL",
                (
                    f"Integrity status={status}; "
                    f"SigValid={signature_valid}; "
                    f"Tampered={tampered}; "
                    f"Missing={missing}; "
                    f"NewFiles={new_files}"
                ),
            )

        return {
            "status": status,
            "signature_valid": signature_valid,
            "tampered_files": tampered,
            "missing_files": missing,
            "new_unverified_files": new_files,
            "protected_count": len(stored_files),
        }

    # =========================================================
    # OFFLINE ENDPOINT VALIDATION
    # =========================================================

    def validate_offline_endpoint(
        self,
        endpoint: str,
    ) -> bool:
        """
        Validate a local endpoint.

        This function validates addresses only.
        It does not perform network connections.
        """

        endpoint = str(endpoint).strip()

        if not endpoint:
            return False

        clean = endpoint.lower()

        # Camera indexes.
        if clean.isdigit():
            return True

        # Existing local files.
        try:

            if Path(endpoint).expanduser().is_file():
                return True

        except OSError:
            pass

        # Only RTSP URLs are accepted as network endpoints.
        if not clean.startswith("rtsp://"):

            self._log_security_event(
                "BLOCKED",
                f"Unsupported endpoint scheme blocked: {endpoint}",
            )

            return False

        try:

            parsed = urlsplit(endpoint)

            if parsed.scheme.lower() != "rtsp":
                return False

            hostname = parsed.hostname

            if not hostname:
                return False

            if hostname.lower() == "localhost":
                return True

            ip = ipaddress.ip_address(hostname)

            allowed = (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
            )

            if allowed:
                return True

        except ValueError:
            pass

        self._log_security_event(
            "BLOCKED",
            f"Unauthorized external endpoint blocked: {endpoint}",
        )

        return False

    # =========================================================
    # INPUT SANITIZATION
    # =========================================================

    @staticmethod
    def sanitize_text_input(
        raw_text: str,
        max_length: int = 120,
    ) -> str:

        if max_length < 0:
            raise ValueError("max_length cannot be negative.")

        cleaned = re.sub(
            r"[;\"'\\<>]",
            "",
            str(raw_text),
        ).strip()

        return cleaned[:max_length]

    # =========================================================
    # DATABASE SNAPSHOT
    # =========================================================

    def create_protected_db_snapshot(
        self,
    ) -> Optional[str]:

        if not self.db_path.is_file():
            return None

        stamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        destination = (
            self.backup_dir
            / f"apex_db_shield_{stamp}.db"
        )

        try:

            source = sqlite3.connect(
                f"file:{self.db_path.as_posix()}?mode=ro",
                uri=True,
            )

            target = sqlite3.connect(destination)

            try:

                source.backup(target)

            finally:

                target.close()
                source.close()

            self._log_security_event(
                "INFO",
                f"Protected DB snapshot created: {destination.name}",
            )

            return str(destination)

        except Exception as error:

            self._log_security_event(
                "ERROR",
                f"DB snapshot failed: {error}",
            )

            try:

                if destination.exists():
                    destination.unlink()

            except OSError:
                pass

            return None

    # =========================================================
    # SECURITY AUDIT
    # =========================================================

    def audit_security_posture(
        self,
    ) -> Dict[str, Any]:

        integrity = self.verify_integrity()

        weak_points: List[str] = []

        if integrity["status"] != "SECURE":

            weak_points.append(
                "Integrity verification requires attention."
            )

        database_status = "NOT_PRESENT"

        if self.db_path.exists():

            conn = None

            try:

                conn = sqlite3.connect(
                    f"file:{self.db_path.as_posix()}?mode=ro",
                    uri=True,
                )

                cur = conn.cursor()

                cur.execute(
                    "PRAGMA integrity_check;"
                )

                db_check = cur.fetchone()

                if db_check and db_check[0] == "ok":

                    database_status = "SECURE"

                else:

                    database_status = "ERROR"

                    weak_points.append(
                        "SQLite database integrity check failed."
                    )

            except Exception:

                database_status = "ERROR"

                weak_points.append(
                    "Database inspection failed."
                )

            finally:

                if conn is not None:
                    conn.close()

        score = max(
            0,
            100 - (len(weak_points) * 25),
        )

        return {
            "shield_version": self.VERSION,
            "shield_active": True,

            # This application does not enforce
            # system-wide air-gapped networking.
            "offline_air_gapped": False,

            "endpoint_validation_available": True,

            "security_score": score,

            "integrity_status": integrity["status"],

            "protected_files": integrity["protected_count"],

            "tampered_files": integrity["tampered_files"],

            "missing_files": integrity["missing_files"],

            "new_unverified_files": integrity[
                "new_unverified_files"
            ],

            "signature_valid": integrity[
                "signature_valid"
            ],

            "database_status": database_status,

            "weak_points": weak_points,
        }


# =============================================================
# COMMAND LINE
# =============================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description="APEX Cyber Shield"
    )

    parser.add_argument(
        "--initialize-baseline",
        action="store_true",
        help="Create a baseline only if one does not exist.",
    )

    parser.add_argument(
        "--refresh-baseline",
        action="store_true",
        help="Replace the existing baseline.",
    )

    parser.add_argument(
        "--confirm-baseline-replacement",
        action="store_true",
        help="Explicit confirmation for baseline replacement.",
    )

    args = parser.parse_args()

    shield = APEXCyberShield()

    if args.initialize_baseline:

        try:

            result = shield.build_integrity_baseline(
                replace_existing=False
            )

            print(
                f"Baseline created: {result['file_count']} files."
            )

        except FileExistsError as error:

            print(f"BLOCKED: {error}")

        return

    if args.refresh_baseline:

        if not args.confirm_baseline_replacement:

            print(
                "BLOCKED: Baseline replacement requires "
                "--confirm-baseline-replacement"
            )

            return

        result = shield.build_integrity_baseline(
            replace_existing=True
        )

        print(
            "Baseline replaced after explicit confirmation."
        )

        print(
            f"Protected files: {result['file_count']}"
        )

        return

    report = shield.audit_security_posture()

    print("\n" + "=" * 55)

    print("          APEX CYBER SHIELD")

    print("=" * 55)

    print(
        f"Version: {report['shield_version']}"
    )

    print(
        f"Security Score: {report['security_score']}%"
    )

    print(
        f"Integrity Status: {report['integrity_status']}"
    )

    print(
        f"Protected Files: {report['protected_files']}"
    )

    print(
        f"Database Status: {report['database_status']}"
    )

    print(
        f"Signature Valid: {report['signature_valid']}"
    )

    print(
        f"System Air-Gapped: {report['offline_air_gapped']}"
    )

    if report["tampered_files"]:

        print("\nTampered Files:")

        for filename in report["tampered_files"]:
            print(f"  - {filename}")

    if report["missing_files"]:

        print("\nMissing Files:")

        for filename in report["missing_files"]:
            print(f"  - {filename}")

    if report["new_unverified_files"]:

        print("\nNew Unverified Files:")

        for filename in report["new_unverified_files"]:
            print(f"  - {filename}")

    if report["weak_points"]:

        print("\nWarnings:")

        for warning in report["weak_points"]:
            print(f"  - {warning}")

    print("\n" + "=" * 55)


if __name__ == "__main__":
    main()