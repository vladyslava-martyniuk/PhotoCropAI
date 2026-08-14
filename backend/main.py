from io import BytesIO
from pathlib import Path

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




app = FastAPI(
    title="PhotoCropAI API",
    version="0.1.0",
)

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


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/images/upload")
async def upload_image(file: UploadFile) -> dict:
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
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
            image_format = image.format
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=400,
            detail="Cannot read image",
        ) from exc

    file_id, working_path = create_working_copy(
        content,
        file.filename,
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


@app.post("/api/images/{file_id}/detect")
def detect_image_object(file_id: str) -> dict:
    try:
        image_path = get_working_path(file_id)

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
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@app.post("/api/images/{file_id}/crop")
def crop_image_endpoint(file_id: str) -> dict:
    try:
        image_path = get_working_path(file_id)

        image = read_image(
            str(image_path)
        )

        oriented_image, rotation_angle = (
            choose_best_orientation(image)
        )

        detection = detect_object_from_image(
            oriented_image
        )

        crop_box = calculate_crop_box(
            detection
        )

        x1 = crop_box["x1"]
        y1 = crop_box["y1"]
        x2 = crop_box["x2"]
        y2 = crop_box["y2"]

        cropped = oriented_image[
            y1:y2,
            x1:x2,
        ]

        original_name = image_path.name
        folder_name = image_path.stem

        output_dir = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "output"
            / folder_name
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        original_output_path = (
            output_dir
            / f"original_{original_name}"
        )

        new_output_path = (
            output_dir
            / f"new_{original_name}"
        )

        save_image(
            image,
            str(original_output_path),
        )

        save_image(
            cropped,
            str(new_output_path),
        )

        return {
            "id": file_id,
            "filename": original_name,
            "folder_name": folder_name,
            "rotation_angle": rotation_angle,
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
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@app.post("/api/images/{file_id}/rotate/{angle}")
def rotate_result(
    file_id: str,
    angle: int,
) -> dict:
    if angle not in (90, 270):
        raise HTTPException(
            status_code=400,
            detail="Angle must be 90 or 270",
        )

    try:
        image_path = get_working_path(file_id)

        folder_name = image_path.stem

        output_dir = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "output"
            / folder_name
        )

        matches = list(
            output_dir.glob("new_*")
        )

        if not matches:
            raise HTTPException(
                status_code=404,
                detail="Cropped image not found",
            )

        output_path = matches[0]

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


@app.get("/api/images/{file_id}/result")
def get_crop_result(file_id: str):
    try:
        image_path = get_working_path(file_id)

        folder_name = image_path.stem

        output_dir = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "output"
            / folder_name
        )

        matches = list(
            output_dir.glob("new_*")
        )

        if not matches:
            raise HTTPException(
                status_code=404,
                detail="Cropped image not found",
            )

        return FileResponse(
            matches[0]
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

