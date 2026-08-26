from fastapi.staticfiles import StaticFiles
from io import BytesIO
from pathlib import Path
import json
import sys
import tkinter as tk
from tkinter import filedialog

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from services.working_copy_service import (
    create_working_copy,
    get_working_path,
)

from services.auto_crop_service import (
    detect_object,
    detect_object_from_image,
    calculate_crop_box,
    save_image,
    read_image,
)

from services.orientation_service import (
    choose_best_orientation,
    rotate_image,
)

from services.database_service import (
    init_database,
    save_processing_result,
    get_processing_history,
    update_rotation,
)


app = FastAPI(
    title="PhotoCropAI API",
    version="0.1.0",
)


if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(sys.executable).resolve().parent
else:
    RESOURCE_DIR = Path(__file__).resolve().parents[1]
    APP_DIR = RESOURCE_DIR


SETTINGS_PATH = APP_DIR / "data" / "settings.json"


def load_output_dir() -> Path | None:
    if not SETTINGS_PATH.exists():
        return None

    try:
        settings = json.loads(
            SETTINGS_PATH.read_text(
                encoding="utf-8"
            )
        )

        saved_path = settings.get(
            "output_folder"
        )

        if not saved_path:
            return None

        folder = Path(saved_path)

        if (
            folder.exists()
            and folder.is_dir()
        ):
            return folder

    except (
        OSError,
        json.JSONDecodeError,
    ):
        pass

    return None


CURRENT_OUTPUT_DIR = load_output_dir()


def save_output_dir(
    output_dir: Path,
) -> None:
    SETTINGS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    SETTINGS_PATH.write_text(
        json.dumps(
            {
                "output_folder": str(
                    output_dir
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def clear_saved_output_dir() -> None:
    if SETTINGS_PATH.exists():
        SETTINGS_PATH.unlink()


init_database()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_output_dir() -> Path:
    if CURRENT_OUTPUT_DIR is None:
        raise HTTPException(
            status_code=400,
            detail="Output folder is not selected",
        )

    CURRENT_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    return CURRENT_OUTPUT_DIR


def get_result_path(
    prefix: str,
    original_name: str,
) -> Path:
    output_dir = get_output_dir()

    original_stem = Path(
        original_name
    ).stem

    return (
        output_dir
        / f"{prefix}_{original_stem}.jpg"
    )


def save_failed_image(
    file_id: str,
) -> Path:
    image_path = get_working_path(
        file_id
    )

    failed_output_path = (
        get_result_path(
            "failed",
            image_path.name,
        )
    )

    image = read_image(
        str(image_path)
    )

    save_image(
        image,
        str(failed_output_path),
    )

    save_processing_result(
        file_id=file_id,
        filename=image_path.name,
        status="failed",
        output_path=str(
            failed_output_path
        ),
    )

    return failed_output_path


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.get(
    "/api/settings/output-folder"
)
def get_output_folder() -> dict:
    if CURRENT_OUTPUT_DIR is None:
        return {
            "selected": False,
            "path": "",
        }

    return {
        "selected": True,
        "path": str(
            CURRENT_OUTPUT_DIR
        ),
    }


@app.post(
    "/api/settings/output-folder/select"
)
def select_output_folder() -> dict:
    global CURRENT_OUTPUT_DIR

    root = tk.Tk()
    root.withdraw()
    root.attributes(
        "-topmost",
        True,
    )

    if CURRENT_OUTPUT_DIR is not None:
        initial_dir = str(
            CURRENT_OUTPUT_DIR
        )
    else:
        initial_dir = str(
            Path.home()
        )

    try:
        selected_folder = (
            filedialog.askdirectory(
                title="Choose output folder",
                initialdir=initial_dir,
            )
        )
    finally:
        root.destroy()

    if not selected_folder:
        return {
            "selected":
                CURRENT_OUTPUT_DIR
                is not None,
            "path":
                str(CURRENT_OUTPUT_DIR)
                if CURRENT_OUTPUT_DIR
                is not None
                else "",
        }

    output_dir = Path(
        selected_folder
    ).resolve()

    CURRENT_OUTPUT_DIR = output_dir

    save_output_dir(
        CURRENT_OUTPUT_DIR
    )

    return {
        "selected": True,
        "path": str(
            CURRENT_OUTPUT_DIR
        ),
    }


@app.post(
    "/api/settings/output-folder/clear"
)
def clear_output_folder() -> dict:
    global CURRENT_OUTPUT_DIR

    CURRENT_OUTPUT_DIR = None

    clear_saved_output_dir()

    return {
        "selected": False,
        "path": "",
    }


@app.post("/api/images/upload")
async def upload_image(
    file: UploadFile,
) -> dict:
    if CURRENT_OUTPUT_DIR is None:
        raise HTTPException(
            status_code=400,
            detail="Output folder is not selected",
        )

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/bmp",
        "image/tiff",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type",
        )

    content = await file.read()

    try:
        with Image.open(
            BytesIO(content)
        ) as image:
            width, height = image.size
            image_format = image.format

    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=400,
            detail="Cannot read image",
        ) from exc

    file_id, working_path = (
        create_working_copy(
            content,
            file.filename,
        )
    )

    return {
        "id": file_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "format": image_format,
        "width": width,
        "height": height,
        "size_bytes": len(content),
    }


@app.post(
    "/api/images/{file_id}/detect"
)
def detect_image_object(
    file_id: str,
) -> dict:
    try:
        image_path = get_working_path(
            file_id
        )

        detection = detect_object(
            str(image_path)
        )

        crop = calculate_crop_box(
            detection
        )

        return {
            "detection": detection,
            "crop": crop,
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        try:
            save_failed_image(
                file_id
            )
        except FileNotFoundError:
            pass

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@app.post(
    "/api/images/{file_id}/crop"
)
def crop_image_endpoint(
    file_id: str,
) -> dict:
    try:
        image_path = get_working_path(
            file_id
        )

        image = read_image(
            str(image_path)
        )

        oriented_image, rotation_angle = (
            choose_best_orientation(
                image
            )
        )

        detection = (
            detect_object_from_image(
                oriented_image
            )
        )

        crop_box = (
            calculate_crop_box(
                detection
            )
        )

        x1 = crop_box["x1"]
        y1 = crop_box["y1"]
        x2 = crop_box["x2"]
        y2 = crop_box["y2"]

        cropped = oriented_image[
            y1:y2,
            x1:x2,
        ]

        original_name = (
            image_path.name
        )

        new_output_path = (
            get_result_path(
                "new",
                original_name,
            )
        )

        save_image(
            cropped,
            str(new_output_path),
        )

        save_processing_result(
            file_id=file_id,
            filename=original_name,
            status="completed",
            rotation_angle=rotation_angle,
            detection=detection,
            crop=crop_box,
            output_path=str(
                new_output_path
            ),
        )

        return {
            "id": file_id,
            "filename": original_name,
            "rotation_angle":
                rotation_angle,
            "detection": detection,
            "crop": crop_box,
            "preview_url":
                f"/api/images/{file_id}/result",
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        try:
            save_failed_image(
                file_id
            )
        except FileNotFoundError:
            pass

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@app.post(
    "/api/images/{file_id}/cancel"
)
def cancel_image(
    file_id: str,
) -> dict:
    try:
        image_path = get_working_path(
            file_id
        )

        new_output_path = (
            get_result_path(
                "new",
                image_path.name,
            )
        )

        failed_output_path = (
            get_result_path(
                "failed",
                image_path.name,
            )
        )

        if new_output_path.exists():
            new_output_path.unlink()

        if failed_output_path.exists():
            failed_output_path.unlink()

        cancelled_output_path = (
            get_result_path(
                "cancelled",
                image_path.name,
            )
        )

        image = read_image(
            str(image_path)
        )

        save_image(
            image,
            str(cancelled_output_path),
        )

        save_processing_result(
            file_id=file_id,
            filename=image_path.name,
            status="cancelled",
            output_path=str(
                cancelled_output_path
            ),
        )

        return {
            "id": file_id,
            "filename":
                image_path.name,
            "status":
                "cancelled",
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@app.post(
    "/api/images/{file_id}/rotate/{angle}"
)
def rotate_result(
    file_id: str,
    angle: int,
) -> dict:
    if angle not in (
        90,
        270,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Angle must be 90 or 270"
            ),
        )

    try:
        image_path = get_working_path(
            file_id
        )

        output_path = (
            get_result_path(
                "new",
                image_path.name,
            )
        )

        if not output_path.exists():
            raise HTTPException(
                status_code=404,
                detail=(
                    "Cropped image not found"
                ),
            )

        image = read_image(
            str(output_path)
        )

        rotated = rotate_image(
            image,
            angle,
        )

        save_image(
            rotated,
            str(output_path),
        )

        update_rotation(
            file_id=file_id,
            angle=angle,
        )

        return {
            "id": file_id,
            "rotation_angle": angle,
            "preview_url":
                f"/api/images/{file_id}/result",
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@app.get("/api/history")
def processing_history() -> dict:
    history = (
        get_processing_history()
    )

    return {
        "count": len(history),
        "items": history,
    }


@app.get(
    "/api/images/{file_id}/result"
)
def get_crop_result(
    file_id: str,
):
    try:
        image_path = get_working_path(
            file_id
        )

        output_path = (
            get_result_path(
                "new",
                image_path.name,
            )
        )

        if not output_path.exists():
            raise HTTPException(
                status_code=404,
                detail=(
                    "Cropped image not found"
                ),
            )

        return FileResponse(
            output_path
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


FRONTEND_DIST = (
    RESOURCE_DIR
    / "frontend"
    / "dist"
)


if FRONTEND_DIST.exists():
    app.mount(
        "/",
        StaticFiles(
            directory=FRONTEND_DIST,
            html=True,
        ),
        name="frontend",
    )