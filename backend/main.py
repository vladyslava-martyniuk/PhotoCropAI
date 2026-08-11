from io import BytesIO

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

from PhotoCropAI.backend.services.working_copy_service import (
    create_working_copy,
    get_working_path,
)

from PhotoCropAI.backend.services.auto_crop_service import (
    detect_object,
    calculate_crop_box,
    crop_image,
)
from fastapi.responses import FileResponse
from pathlib import Path


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

        detection = detect_object(str(image_path))
        crop = calculate_crop_box(detection)

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
def crop_image_endpoint(file_id: str):
    try:
        image_path = get_working_path(file_id)

        detection = detect_object(str(image_path))
        crop_box = calculate_crop_box(detection)

        output_dir = Path(__file__).resolve().parents[1] / "data" / "output"
        output_path = output_dir / f"{file_id}{image_path.suffix}"

        crop_image(
            str(image_path),
            crop_box,
            str(output_path),
        )

        return {
            "id": file_id,
            "crop": crop_box,
            "preview_url": f"/api/images/{file_id}/result",
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


@app.get("/api/images/{file_id}/result")
def get_crop_result(file_id: str):
    output_dir = Path(__file__).resolve().parents[1] / "data" / "output"

    matches = list(output_dir.glob(f"{file_id}.*"))

    if not matches:
        raise HTTPException(
            status_code=404,
            detail="Обрізане зображення не знайдено",
        )

    return FileResponse(matches[0])