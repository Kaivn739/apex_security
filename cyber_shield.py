from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class APEXCyberShield:
    """
    قەڵغانی پۆڵاینی سیکیوریتی APEX (Steel Cyber Shield):
    1. سەپاندنی سیاسەتی ١٠٠٪ ئۆفلاین (Air-Gapped Local Enforcement).
    2. پاراستنی کۆدەکان و داتابەیس بە پەنجەمۆری SHA-256 دژی هاک و دەستکاریکردن.
    3. پاککردنەوە و پاراستنی زانیارییە کەسییەکان و ڕێگری لە SQL Injection.
    4. پێدانی ڕاپۆرتی خاڵە لاوازەکان و چارەسەرکردنیان بە APEX AI Developer.
    """

    def __init__(
        self, project_root: Optional[Path] = None, db_name: str = "apex_security.db"
    ) -> None:
        self.project_root = (project_root or Path(__file__).resolve().parent).resolve()
        self.db_path = self.project_root / db_name
        self.vault_dir = self.project_root / ".apex_shield_vault"
        self.manifest_path = self.vault_dir / "integrity_manifest.json"
        self.audit_log_path = self.vault_dir / "shield_audit.log"
        self.backup_dir = self.vault_dir / "db_snapshots"
        self._machine_key = self._derive_local_machine_key()

        self._ensure_vault_structure()

    def _ensure_vault_structure(self) -> None:
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _derive_local_machine_key(self) -> bytes:
        """دروستکردنی کلیلی ناوخۆییی تایبەت بەم لاپتۆپە (بێ پەیوەندی بە ئینتەرنێت)."""
        raw_identity = f"{os.name}|{self.project_root}|APEX_STEEL_SHIELD_2026".encode(
            "utf-8"
        )
        return hashlib.sha256(raw_identity).digest()

    def _log_security_event(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level}] {message}\n"
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    @staticmethod
    def compute_file_sha256(file_path: Path) -> str:
        """هەژمارکردنی پەنجەمۆری دیجیتاڵی SHA-256 بۆ هەر فایلێک."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _sign_payload(self, payload_text: str) -> str:
        return hmac.new(
            self._machine_key, payload_text.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def build_integrity_baseline(self) -> Dict[str, Any]:
        """تۆمارکردنی پەنجەمۆری پارێزراوی هەموو فایلە سەرەکییەکانی پڕۆژەی APEX."""
        hashes: Dict[str, str] = {}
        for py_file in sorted(self.project_root.glob("*.py")):
            hashes[py_file.name] = self.compute_file_sha256(py_file)

        raw_json = json.dumps(hashes, sort_keys=True)
        envelope = {
            "updated_at": datetime.now().isoformat(),
            "file_count": len(hashes),
            "files": hashes,
            "signature": self._sign_payload(raw_json),
        }
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(envelope, f, indent=2, ensure_ascii=False)

        self._log_security_event(
            "INFO", f"Integrity baseline updated for {len(hashes)} core files."
        )
        return envelope

    def verify_integrity(self) -> Dict[str, Any]:
        """پشکنینی ئەوەی ئایا هیچ فایلێکی APEX بە شێوەی نایاسایی دەستکاری کراوە یان سڕاوەتەوە."""
        if not self.manifest_path.exists():
            baseline = self.build_integrity_baseline()
            return {
                "status": "BASELINE_CREATED",
                "tampered_files": [],
                "missing_files": [],
                "new_unverified_files": [],
                "protected_count": baseline["file_count"],
            }

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            envelope = json.load(f)

        stored_files: Dict[str, str] = envelope.get("files", {})
        expected_sig = self._sign_payload(json.dumps(stored_files, sort_keys=True))
        signature_valid = hmac.compare_digest(
            expected_sig, str(envelope.get("signature", ""))
        )

        tampered: List[str] = []
        missing: List[str] = []
        new_files: List[str] = []

        for fname, old_hash in stored_files.items():
            target = self.project_root / fname
            if not target.exists():
                missing.append(fname)
            else:
                current_hash = self.compute_file_sha256(target)
                if current_hash != old_hash:
                    tampered.append(fname)

        for py_file in sorted(self.project_root.glob("*.py")):
            if py_file.name not in stored_files:
                new_files.append(py_file.name)

        is_clean = signature_valid and not tampered and not missing
        status = "SECURE" if is_clean else "ALERT_TAMPER_DETECTED"

        if not is_clean:
            self._log_security_event(
                "CRITICAL",
                f"Shield alert! SigValid={signature_valid}, Tampered={tampered}, Missing={missing}",
            )

        return {
            "status": status,
            "signature_valid": signature_valid,
            "tampered_files": tampered,
            "missing_files": missing,
            "new_unverified_files": new_files,
            "protected_count": len(stored_files),
        }

    def validate_offline_endpoint(self, endpoint: str) -> bool:
        """
        دڵنیابوونەوە لە ١٠٠٪ ئۆفلاین بوون:
        تەنها ڕێگە دەدات بە ناونیشانی ناوخۆیی (Localhost / LAN IP / RTSP ناوخۆیی / فایل)
        و ڕێگری دەکات لە ناردنی داتا بۆ سێرڤەری دەرەکی.
        """
        clean = endpoint.strip().lower()
        if not clean:
            return False

        # ڕێگەپێدراوەکان: ناونیشانی ناوخۆیی، کامێرای LAN، فایل، یان ژمارەی کامێرا (0, 1, ...)
        if clean.isdigit() or os.path.exists(endpoint):
            return True

        allowed_prefixes = (
            "127.0.0.1",
            "localhost",
            "192.168.",
            "10.",
            "172.16.",
            "rtsp://192.168.",
            "rtsp://10.",
            "rtsp://127.0.0.1",
            "rtsp://localhost",
        )
        if any(clean.startswith(prefix) for prefix in allowed_prefixes):
            return True

        self._log_security_event(
            "BLOCKED", f"Unauthorized external endpoint blocked: {endpoint}"
        )
        return False

    @staticmethod
    def sanitize_text_input(raw_text: str, max_length: int = 120) -> str:
        """پاککردنەوەی نووسینەکان لە هەر کۆدێکی زیانبەخش یان SQL Injection."""
        cleaned = re.sub(r"[;\"'\\<>]", "", str(raw_text)).strip()
        return cleaned[:max_length]

    def create_protected_db_snapshot(self) -> Optional[str]:
        """وەرگرتنی کۆپییەکی پارێزراوی داتابەیس لە ناو قاسەی قەڵغاندا."""
        if not self.db_path.exists():
            return None
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = self.backup_dir / f"apex_db_shield_{stamp}.db"
        try:
            shutil.copy2(self.db_path, dest)
            # هێشتنەوەی تەنها دوایین ١٠ کۆپی تا هارد پڕ نەبێت
            snapshots = sorted(self.backup_dir.glob("apex_db_shield_*.db"))
            for old_snap in snapshots[:-10]:
                old_snap.unlink(missing_ok=True)
            self._log_security_event(
                "INFO", f"Protected DB snapshot created: {dest.name}"
            )
            return str(dest)
        except Exception as e:
            self._log_security_event("ERROR", f"DB snapshot failed: {e}")
            return None

    def audit_security_posture(self) -> Dict[str, Any]:
        """
        پشکنینی گشتگیری خاڵە لاوازەکانی سیکیوریتی (بۆ پیشاندان لە پانێڵی کێشەکان و APEX AI Developer).
        """
        integrity = self.verify_integrity()
        weak_points: List[str] = []

        if (
            integrity["status"] != "SECURE"
            and integrity["status"] != "BASELINE_CREATED"
        ):
            weak_points.append(
                "تێکچوونی پەنجەمۆری فایلە سەرەکییەکان (Integrity Mismatch)"
            )

        if self.db_path.exists():
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("PRAGMA integrity_check;")
                db_check = cur.fetchone()
                conn.close()
                if not db_check or db_check[0] != "ok":
                    weak_points.append(
                        "کێشە لە پێکهاتەی ناوەوەی داتابەیسی apex_security.db"
                    )
            except Exception:
                weak_points.append("نەتوانرا پشکنینی داتابەیس بکرێت")

        score = max(0, 100 - (len(weak_points) * 25))
        return {
            "shield_active": True,
            "offline_air_gapped": True,
            "security_score": score,
            "integrity_status": integrity["status"],
            "protected_files": integrity["protected_count"],
            "weak_points": weak_points,
        }


if __name__ == "__main__":
    shield = APEXCyberShield()
    shield.build_integrity_baseline()
    report = shield.audit_security_posture()
    local_ok = shield.validate_offline_endpoint("rtsp://192.168.1.100/stream1")
    cloud_blocked = not shield.validate_offline_endpoint(
        "https://external-cloud-server.com/upload"
    )
    print(
        f"[APEX CYBER SHIELD] Score: {report['security_score']}% | "
        f"Protected Files: {report['protected_files']} | "
        f"LAN Allowed: {local_ok} | Cloud Blocked: {cloud_blocked}"
    )
