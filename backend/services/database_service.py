import sqlite3
import sys
from datetime import datetime
from pathlib import Path


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parents[2]


DATABASE_DIR = BASE_DIR / "data"
DATABASE_PATH = DATABASE_DIR / "photocropai.db"


def get_connection():
    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_database():
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS processing_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                status TEXT NOT NULL,

                rotation_angle INTEGER DEFAULT 0,

                detection_x INTEGER,
                detection_y INTEGER,
                detection_width INTEGER,
                detection_height INTEGER,

                crop_x1 INTEGER,
                crop_y1 INTEGER,
                crop_x2 INTEGER,
                crop_y2 INTEGER,
                crop_width INTEGER,
                crop_height INTEGER,

                output_path TEXT,

                created_at TEXT NOT NULL
            )
            """
        )

        connection.commit()

    finally:
        connection.close()


def save_processing_result(
    file_id: str,
    filename: str,
    status: str,
    rotation_angle: int = 0,
    detection: dict | None = None,
    crop: dict | None = None,
    output_path: str | None = None,
):
    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO processing_history (
                file_id,
                filename,
                status,
                rotation_angle,

                detection_x,
                detection_y,
                detection_width,
                detection_height,

                crop_x1,
                crop_y1,
                crop_x2,
                crop_y2,
                crop_width,
                crop_height,

                output_path,
                created_at
            )
            VALUES (
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?
            )
            """,
            (
                file_id,
                filename,
                status,
                rotation_angle,

                detection.get("x")
                if detection
                else None,

                detection.get("y")
                if detection
                else None,

                detection.get("width")
                if detection
                else None,

                detection.get("height")
                if detection
                else None,

                crop.get("x1")
                if crop
                else None,

                crop.get("y1")
                if crop
                else None,

                crop.get("x2")
                if crop
                else None,

                crop.get("y2")
                if crop
                else None,

                crop.get("width")
                if crop
                else None,

                crop.get("height")
                if crop
                else None,

                output_path,

                datetime.now().isoformat(
                    timespec="seconds"
                ),
            ),
        )

        connection.commit()

    finally:
        connection.close()


def get_processing_history(
    limit: int = 100,
) -> list[dict]:
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM processing_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        connection.close()


def update_rotation(
    file_id: str,
    angle: int,
):
    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE processing_history
            SET rotation_angle = ?
            WHERE file_id = ?
            """,
            (
                angle,
                file_id,
            ),
        )

        connection.commit()

    finally:
        connection.close()