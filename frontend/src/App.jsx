import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [backendStatus, setBackendStatus] = useState("Loading...");

  const [selectedFiles, setSelectedFiles] = useState([]);
  const [items, setItems] = useState([]);
  const [uploadStatus, setUploadStatus] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  const [selectedZip, setSelectedZip] = useState(null);
  const [zipStatus, setZipStatus] = useState("");
  const [zipResultUrl, setZipResultUrl] = useState("");
  const [isZipProcessing, setIsZipProcessing] = useState(false);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Backend error");
        }

        return response.json();
      })
      .then(() => {
        setBackendStatus("Backend is working");
      })
      .catch(() => {
        setBackendStatus("Backend error");
      });
  }, []);

  function handleFileChange(event) {
    const newFiles = Array.from(
      event.target.files || []
    );

    if (newFiles.length === 0) {
      return;
    }

    const remainingSlots =
      20 - selectedFiles.length;

    if (remainingSlots <= 0) {
      setUploadStatus(
        "Maximum 20 images"
      );

      event.target.value = "";
      return;
    }

    const filesToAdd = newFiles.slice(
      0,
      remainingSlots
    );

    const newItems = filesToAdd.map(
      (file, index) => ({
        localId: `${Date.now()}-${index}-${file.name}`,
        file,
        fileId: null,
        previewUrl: URL.createObjectURL(file),
        croppedUrl: "",
        detection: null,
        crop: null,
        status: "Waiting",
        error: "",
      })
    );

    setSelectedFiles((currentFiles) => [
      ...currentFiles,
      ...filesToAdd,
    ]);

    setItems((currentItems) => [
      ...currentItems,
      ...newItems,
    ]);

    if (newFiles.length > remainingSlots) {
      setUploadStatus(
        `Added ${filesToAdd.length} images. Maximum is 20.`
      );
    } else {
      setUploadStatus("");
    }

    event.target.value = "";
  }

  function updateItem(
    localId,
    changes
  ) {
    setItems((currentItems) =>
      currentItems.map((item) =>
        item.localId === localId
          ? {
              ...item,
              ...changes,
            }
          : item
      )
    );
  }

  async function processSingleImage(item) {
    updateItem(item.localId, {
      status: "Uploading...",
      error: "",
    });

    const formData = new FormData();
    formData.append(
      "file",
      item.file
    );

    const uploadResponse = await fetch(
      "http://127.0.0.1:8000/api/images/upload",
      {
        method: "POST",
        body: formData,
      }
    );

    const uploadData =
      await uploadResponse.json();

    if (!uploadResponse.ok) {
      throw new Error(
        uploadData.detail ||
          "Loading error"
      );
    }

    updateItem(item.localId, {
      fileId: uploadData.id,
      status: "Detecting object...",
    });

    const detectResponse = await fetch(
      `http://127.0.0.1:8000/api/images/${uploadData.id}/detect`,
      {
        method: "POST",
      }
    );

    const detectData =
      await detectResponse.json();

    if (!detectResponse.ok) {
      throw new Error(
        detectData.detail ||
          "Object detection error"
      );
    }

    updateItem(item.localId, {
      detection:
        detectData.detection,
      crop:
        detectData.crop,
      status: "Cropping...",
    });

    const cropResponse = await fetch(
      `http://127.0.0.1:8000/api/images/${uploadData.id}/crop`,
      {
        method: "POST",
      }
    );

    const cropData =
      await cropResponse.json();

    if (!cropResponse.ok) {
      throw new Error(
        cropData.detail ||
          "Cropping error"
      );
    }

    updateItem(item.localId, {
      fileId: uploadData.id,
      croppedUrl:
        `http://127.0.0.1:8000${cropData.preview_url}` +
        `?t=${Date.now()}`,
      status: "Completed",
    });
  }

  async function handleProcessAll() {
    if (items.length === 0) {
      return;
    }

    setIsProcessing(true);

    let completed = 0;
    let failed = 0;

    setUploadStatus(
      `Processing 0 / ${items.length}`
    );

    for (const item of items) {
      try {
        await processSingleImage(item);
      } catch (error) {
        failed += 1;

        updateItem(item.localId, {
          status: "Error",
          error: error.message,
        });
      }

      completed += 1;

      setUploadStatus(
        `Processing ${completed} / ${items.length}`
      );
    }

    if (failed === 0) {
      setUploadStatus(
        `Finished: ${completed} / ${items.length}`
      );
    } else {
      setUploadStatus(
        `Finished: ${
          completed - failed
        } successful, ${failed} failed`
      );
    }

    setIsProcessing(false);
  }

  async function handleRotate(
    item,
    angle
  ) {
    if (!item.fileId) {
      return;
    }

    try {
      updateItem(item.localId, {
        status: "Rotating...",
        error: "",
      });

      const response = await fetch(
        `http://127.0.0.1:8000/api/images/${item.fileId}/rotate/${angle}`,
        {
          method: "POST",
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Rotation error"
        );
      }

      updateItem(item.localId, {
        croppedUrl:
          `http://127.0.0.1:8000${data.preview_url}` +
          `?t=${Date.now()}`,
        status: "Completed",
      });
    } catch (error) {
      updateItem(item.localId, {
        status: "Error",
        error: error.message,
      });
    }
  }

  function handleClearAll() {
    items.forEach((item) => {
      if (item.previewUrl) {
        URL.revokeObjectURL(
          item.previewUrl
        );
      }
    });

    setSelectedFiles([]);
    setItems([]);
    setUploadStatus("");
  }

  function handleZipChange(event) {
    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }

    setSelectedZip(file);
    setZipStatus("");
    setZipResultUrl("");

    event.target.value = "";
  }

  async function handleZipProcess() {
    if (!selectedZip) {
      return;
    }

    const formData =
      new FormData();

    formData.append(
      "file",
      selectedZip
    );

    setIsZipProcessing(true);
    setZipStatus(
      "Processing ZIP..."
    );
    setZipResultUrl("");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/zip/process",
        {
          method: "POST",
          body: formData,
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "ZIP processing error"
        );
      }

      setZipResultUrl(
        `http://127.0.0.1:8000${data.download_url}`
      );

      setZipStatus(
        `Completed: ${data.processed_count} processed, ${data.failed_count} failed`
      );
    } catch (error) {
      setZipStatus(
        error.message
      );
    } finally {
      setIsZipProcessing(false);
    }
  }

  return (
    <main className="app">
      <h1>PhotoCropAI</h1>

      <p>{backendStatus}</p>

      <section className="panel">
        <label className="fileButton">
          Choose images

          <input
            type="file"
            accept="image/jpeg,image/png,image/webp,image/bmp,image/tiff"
            onChange={handleFileChange}
            multiple
            hidden
          />
        </label>

        <button
          type="button"
          onClick={handleProcessAll}
          disabled={
            items.length === 0 ||
            isProcessing
          }
        >
          {isProcessing
            ? "Processing..."
            : "Process all"}
        </button>

        <button
          type="button"
          onClick={handleClearAll}
          disabled={
            items.length === 0 ||
            isProcessing
          }
        >
          Clear all
        </button>
      </section>

      {selectedFiles.length > 0 && (
        <p>
          Selected:{" "}
          {selectedFiles.length} / 20
          images
        </p>
      )}

      {uploadStatus && (
        <p>{uploadStatus}</p>
      )}

      <section className="batchGrid">
        {items.map(
          (item, index) => (
            <article
              className="batchItem"
              key={item.localId}
            >
              <h2>
                {index + 1}.{" "}
                {item.file.name}
              </h2>

              <div className="batchImages">
                <div>
                  <h3>Original</h3>

                  <div className="imageWrapper">
                    <img
                      src={
                        item.previewUrl
                      }
                      alt={
                        item.file.name
                      }
                      className="previewImage"
                    />

                    {item.detection &&
                      item.crop && (
                        <>
                          <div
                            className="detectedBox"
                            style={{
                              left: `${
                                (
                                  item
                                    .detection
                                    .x /
                                  item
                                    .detection
                                    .image_width
                                ) *
                                100
                              }%`,
                              top: `${
                                (
                                  item
                                    .detection
                                    .y /
                                  item
                                    .detection
                                    .image_height
                                ) *
                                100
                              }%`,
                              width: `${
                                (
                                  item
                                    .detection
                                    .width /
                                  item
                                    .detection
                                    .image_width
                                ) *
                                100
                              }%`,
                              height: `${
                                (
                                  item
                                    .detection
                                    .height /
                                  item
                                    .detection
                                    .image_height
                                ) *
                                100
                              }%`,
                            }}
                          />

                          <div
                            className="cropBox"
                            style={{
                              left: `${
                                (
                                  item
                                    .crop
                                    .x1 /
                                  item
                                    .detection
                                    .image_width
                                ) *
                                100
                              }%`,
                              top: `${
                                (
                                  item
                                    .crop
                                    .y1 /
                                  item
                                    .detection
                                    .image_height
                                ) *
                                100
                              }%`,
                              width: `${
                                (
                                  item
                                    .crop
                                    .width /
                                  item
                                    .detection
                                    .image_width
                                ) *
                                100
                              }%`,
                              height: `${
                                (
                                  item
                                    .crop
                                    .height /
                                  item
                                    .detection
                                    .image_height
                                ) *
                                100
                              }%`,
                            }}
                          />
                        </>
                      )}
                  </div>
                </div>

                {item.croppedUrl && (
                  <div>
                    <h3>Result</h3>

                    <img
                      src={
                        item.croppedUrl
                      }
                      alt={`Processed ${item.file.name}`}
                      className="previewImage"
                    />

                    <div className="rotateControls">
                      <button
                        type="button"
                        onClick={() =>
                          handleRotate(
                            item,
                            270
                          )
                        }
                      >
                        Rotate left
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          handleRotate(
                            item,
                            90
                          )
                        }
                      >
                        Rotate right
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <p>
                Status: {item.status}
              </p>

              {item.error && (
                <p className="errorMessage">
                  {item.error}
                </p>
              )}
            </article>
          )
        )}
      </section>
    </main>
  );
}

export default App;