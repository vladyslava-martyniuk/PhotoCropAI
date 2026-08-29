# PhotoCropAI – Testing

## Test environment

- Operating system: Windows 11
- Application: PhotoCropAI
- Backend: Python + FastAPI
- Frontend: React
- Image processing: OpenCV
- Database: SQLite

## Test cases

| # | Test | Expected result | Result |
|---|------|-----------------|--------|
| 1 | Start PhotoCropAI | Application opens in browser and backend works | PASS |
| 2 | No output folder selected | Processing is disabled | PASS |
| 3 | Select output folder | Selected folder is displayed and saved | PASS |
| 4 | Add one JPG image | Image appears in the application | PASS |
| 5 | Add several images | Images are added to the batch, maximum 20 | PASS |
| 6 | Drag & drop images | Images are added successfully | PASS |
| 7 | Process valid image | Cropped JPG is saved to selected output folder | PASS |
| 8 | Automatic detection fails | Original image is saved as failed_*.jpg | PASS |
| 9 | Cancel processed image | Result is removed and cancelled_*.jpg is created | PASS |
| 10 | Rotate result | Processed image rotates correctly | PASS |
| 11 | Clear all | Images are removed from the current application view | PASS |
| 12 | Restart application | Previously selected output folder is restored | PASS |
| 13 | Confidential image processing | Image is processed locally and is not uploaded to cloud | PASS |
| 14 | Temporary working copy | Working image is stored only in Windows temporary storage | PASS |
| 15 | Unsupported file | Application rejects unsupported file type without crashing | PASS |

## Known limitations

- Automatic object detection does not work perfectly with every image.
- The current detection algorithm is based on OpenCV and image contours.
- Manual rotation may be needed for some images.
- Further improvement of automatic cropping accuracy is planned.

## Conclusion

The application was tested with different image-processing scenarios.
The main workflow works correctly, including batch processing, output folder
selection, cropping, rotation, cancellation, error handling and local file
processing.