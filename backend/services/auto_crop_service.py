from pathlib import Path

import cv2
import numpy as np


def read_image(image_path: str):
    image_bytes = np.fromfile(image_path, dtype=np.uint8)
    image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Cannot read image")

    return image


def detect_object_from_image(image) -> dict:
    height, width = image.shape[:2]

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(gray, 50, 150)

    kernel = np.ones((5, 5), np.uint8)

    edges = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=2,
    )

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        raise ValueError("Object not found")

    min_area = width * height * 0.01

    valid_contours = [
        contour
        for contour in contours
        if cv2.contourArea(contour) >= min_area
    ]

    if not valid_contours:
        raise ValueError("Object not found")

    largest = max(
        valid_contours,
        key=cv2.contourArea,
    )

    x, y, w, h = cv2.boundingRect(largest)

    return {
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "image_width": width,
        "image_height": height,
    }


def detect_object(image_path: str) -> dict:
    image = read_image(image_path)

    return detect_object_from_image(image)


def calculate_crop_box(
    detection: dict,
    margin_ratio: float = 0.04,
) -> dict:
    x = detection["x"]
    y = detection["y"]
    w = detection["width"]
    h = detection["height"]

    image_width = detection["image_width"]
    image_height = detection["image_height"]

    margin_x = int(w * margin_ratio)
    margin_y = int(h * margin_ratio)

    left = max(0, x - margin_x)
    top = max(0, y - margin_y)

    right = min(
        image_width,
        x + w + margin_x,
    )

    bottom = min(
        image_height,
        y + h + margin_y,
    )

    return {
        "x1": left,
        "y1": top,
        "x2": right,
        "y2": bottom,
        "width": right - left,
        "height": bottom - top,
    }


def save_image(
    image,
    output_path: str,
) -> str:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    extension = output.suffix or ".jpg"

    success, encoded = cv2.imencode(
        extension,
        image,
    )

    if not success:
        raise ValueError("Cannot save image")

    encoded.tofile(str(output))

    return str(output)


def crop_image(
    image_path: str,
    crop_box: dict,
    output_path: str,
) -> str:
    image = read_image(image_path)

    x1 = crop_box["x1"]
    y1 = crop_box["y1"]
    x2 = crop_box["x2"]
    y2 = crop_box["y2"]

    cropped = image[y1:y2, x1:x2]

    return save_image(
        cropped,
        output_path,
    )