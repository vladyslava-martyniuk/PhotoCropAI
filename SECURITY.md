# PhotoCropAI – Security and Privacy

## Local image processing

PhotoCropAI processes images locally on the user's computer.

Images are not uploaded to cloud services or external APIs.

## Temporary files

Working copies of images are stored only in the Windows temporary directory.

Original images are not modified.

## Output files

Processed images are saved only to the output folder selected by the user.

## Supported file types

The application accepts only supported image formats:

- JPEG
- PNG
- WebP
- BMP
- TIFF

Unsupported file types are rejected.

## Data storage

SQLite is used to store processing history.

The database stores processing information such as:

- file identifier
- filename
- processing status
- crop coordinates
- rotation information
- output path

The application does not require user accounts, passwords, or authentication because it runs locally on a single user's computer.

## Network usage

The frontend communicates only with the local FastAPI backend.

The application does not intentionally send image data to external servers.

## Known security considerations

The application is designed as a local desktop tool and is not intended to be exposed publicly on the Internet.

Future improvements may include:

- automatic cleanup of temporary files
- additional file validation
- file size limits
- improved error handling