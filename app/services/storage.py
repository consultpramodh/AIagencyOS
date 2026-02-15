from pathlib import Path
import os
import shutil
import uuid

from fastapi import UploadFile


def upload_root() -> Path:
    root = os.getenv("UPLOAD_ROOT", "data/uploads")
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def store_tenant_file(tenant_id: int, file: UploadFile) -> tuple[str, int]:
    tenant_dir = upload_root() / f"tenant_{tenant_id}"
    tenant_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename or "upload.bin").name
    disk_name = f"{uuid.uuid4().hex}_{safe_name}"
    final_path = tenant_dir / disk_name

    with final_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size = final_path.stat().st_size
    return str(final_path), size
