import cv2

from services.auto_crop_service import (
    detect_object_from_image,
)


def rotate_image(image, angle: int):
    if angle == 90:
        return cv2.rotate(
            image,
            cv2.ROTATE_90_CLOCKWISE,
        )

    if angle == 180:
        return cv2.rotate(
            image,
            cv2.ROTATE_180,
        )

    if angle == 270:
        return cv2.rotate(
            image,
            cv2.ROTATE_90_COUNTERCLOCKWISE,
        )

    return image


def choose_best_orientation(image):
    best_image = image
    best_angle = 0
    best_score = -1

    # Поки не використовуємо 180° і 270° автоматично,
    # бо геометрія об'єкта не дозволяє надійно визначити,
    # де у предмета верх.
    for angle in (0, 90):
        rotated = rotate_image(
            image,
            angle,
        )

        try:
            detection = detect_object_from_image(
                rotated
            )
        except ValueError:
            continue

        image_height, image_width = (
            rotated.shape[:2]
        )

        object_area = (
            detection["width"]
            * detection["height"]
        )

        image_area = (
            image_width
            * image_height
        )

        area_score = (
            object_area / image_area
        )

        center_x = (
            detection["x"]
            + detection["width"] / 2
        )

        center_y = (
            detection["y"]
            + detection["height"] / 2
        )

        distance_x = abs(
            center_x - image_width / 2
        ) / image_width

        distance_y = abs(
            center_y - image_height / 2
        ) / image_height

        center_score = 1 - (
            distance_x + distance_y
        )

        score = (
            area_score
            + center_score
        )

        if score > best_score:
            best_score = score
            best_image = rotated
            best_angle = angle

    return best_image, best_angle