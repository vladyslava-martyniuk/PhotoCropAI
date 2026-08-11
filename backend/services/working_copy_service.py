from pathlib import Path
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parents[2]
WORKING_DIR = BASE_DIR / "data" / "working"


def create_working_copy(
    content: bytes,
    original_filename: str,
) -> tuple[str, Path]:
    WORKING_DIR.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid4())
    suffix = Path(original_filename).suffix.lower()

    working_path = WORKING_DIR / f"{file_id}{suffix}"
    working_path.write_bytes(content)

    return file_id, working_path


def get_working_path(file_id: str) -> Path:
    matches = list(WORKING_DIR.glob(f"{file_id}.*"))

    if not matches:
        raise FileNotFoundError("Робочу копію не знайдено")

    return matches[0]