from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional


class log_activity:
    def __init__(
        self,
        action_type: Optional[str] = None,
        details: Optional[str] = None,
        log_file: Optional[str | Path] = None,
        encoding: str = "utf-8",
    ) -> None:
        self.encoding = encoding
        self.log_file = Path(log_file) if log_file is not None else Path(__file__).with_name("apex_security_log.txt")
        self.action_type = action_type
        self.details = details

        if action_type is not None and details is not None:
            self.log(action_type, details)

    def format_entry(self, action_type: str, details: str) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{now}] - {action_type}: {details}\n"

    def write_entry(self, entry: str) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.log_file.open("a", encoding=self.encoding) as handle:
            handle.write(entry)

    def log(self, action_type: Optional[str] = None, details: Optional[str] = None) -> None:
        resolved_action = action_type if action_type is not None else self.action_type
        resolved_details = details if details is not None else self.details

        if resolved_action is None or resolved_details is None:
            raise ValueError("Both action_type and details are required to write a log entry.")

        try:
            entry = self.format_entry(resolved_action, resolved_details)
            self.write_entry(entry)
        except Exception as exc:
            print(f"Error writing log: {exc}")

    def __call__(self, action_type: Optional[str] = None, details: Optional[str] = None) -> None:
        self.log(action_type, details)