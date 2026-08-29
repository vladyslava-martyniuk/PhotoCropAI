from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4


WORKING_DIR = (
    Path(gettempdir())
    / "PhotoCropAI"
    / "working"
)


def create_working_copy(
    content: bytes,
    original_filename: str,
) -> tuple[str, Path]:
    WORKING_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_id = str(uuid4())

    original_name = Path(
        original_filename
    ).name

    working_dir = (
        WORKING_DIR
        / file_id
    )

    working_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    working_path = (
        working_dir
        / original_name
    )

    working_path.write_bytes(
        content
    )

    return file_id, working_path


def get_working_path(
    file_id: str,
) -> Path:
    working_dir = (
        WORKING_DIR
        / file_id
    )

    if not working_dir.exists():
        raise FileNotFoundError(
            "Working directory not found"
        )

    files = [
        path
        for path in working_dir.iterdir()
        if path.is_file()
    ]

    if not files:
        raise FileNotFoundError(
            "Working copy not found"
        )

    return files[0]