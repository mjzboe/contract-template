import json
import os
from datetime import datetime


async def write_audit_log(record: dict) -> None:
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_dir = os.path.join("logs", "audit")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{date_str}.jsonl")
    line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)
