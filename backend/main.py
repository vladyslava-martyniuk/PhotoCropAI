from fastapi.staticfiles import StaticFiles
from io import BytesIO
from pathlib import Path
import shutil
import sys

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
    output_dir = (
        APP_DIR
        / "data"
        / "output"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return output_dir


def save_failed_image(
    file_id: str,
) -> Path:
    image_path = get_working_path(file_id)
    output_dir = get_output_dir()

    failed_output_path = (
        output_dir
        / f"failed_{image_path.name}"
    )

    shutil.copy2(
        image_path,
        failed_output_path,
    )

    save_processing_result(
        file_id=file_id,
        filename=image_path.name,
        status="failed",
        output_path=str(failed_output_path),
    )

    return failed_output_path


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.post("/api/images/upload")
async def upload_image(
    file: UploadFile,
) -> dict:
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

        output_dir = (
            get_output_dir()
        )

        new_output_path = (
            output_dir
            / f"new_{original_name}"
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

        output_dir = (
            get_output_dir()
        )

        new_output_path = (
            output_dir
            / f"new_{image_path.name}"
        )

        failed_output_path = (
            output_dir
            / f"failed_{image_path.name}"
        )

        if new_output_path.exists():
            new_output_path.unlink()

        if failed_output_path.exists():
            failed_output_path.unlink()

        cancelled_output_path = (
            output_dir
            / f"cancelled_{image_path.name}"
        )

        shutil.copy2(
            image_path,
            cancelled_output_path,
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

        output_dir = (
            get_output_dir()
        )

        output_path = (
            output_dir
            / f"new_{image_path.name}"
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
            get_output_dir()
            / f"new_{image_path.name}"
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