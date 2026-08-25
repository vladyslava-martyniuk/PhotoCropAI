import { useEffect, useRef, useState } from "react";
import "./App.css";

const MAX_IMAGES = 20;

const ALLOWED_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/bmp",
  "image/tiff",
]);

function App() {
  const [backendStatus, setBackendStatus] = useState("Loading...");
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [items, setItems] = useState([]);
  const [uploadStatus, setUploadStatus] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [outputFolder, setOutputFolder] = useState("");
  const [isSelectingOutputFolder, setIsSelectingOutputFolder] =
    useState(false);

  const dragCounter = useRef(0);

  useEffect(() => {
    fetch("/api/health")
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

    fetch("/api/settings/output-folder")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Cannot get output folder");
        }

        return response.json();
      })
      .then((data) => {
        setOutputFolder(data.path || "");
      })
      .catch(() => {
        setOutputFolder("");
      });
  }, []);

  function addFiles(files) {
    const newFiles = Array.from(files || []);

    if (newFiles.length === 0) {
      return;
    }

    const validFiles = newFiles.filter((file) =>
      ALLOWED_TYPES.has(file.type)
    );

    if (validFiles.length === 0) {
      setUploadStatus("No supported image files found");
      return;
    }

    const remainingSlots =
      MAX_IMAGES - selectedFiles.length;

    if (remainingSlots <= 0) {
      setUploadStatus("Maximum 20 images");
      return;
    }

    const filesToAdd = validFiles.slice(
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

    const messages = [];

    if (validFiles.length < newFiles.length) {
      messages.push(
        `${
          newFiles.length - validFiles.length
        } unsupported file(s) skipped`
      );
    }

    if (validFiles.length > remainingSlots) {
      messages.push(
        `Only ${filesToAdd.length} image(s) added. Maximum is 20`
      );
    }

    setUploadStatus(messages.join(". "));
  }

  function handleFileChange(event) {
    addFiles(event.target.files);
    event.target.value = "";
  }

  function handleDragEnter(event) {
    event.preventDefault();
    event.stopPropagation();

    dragCounter.current += 1;
    setIsDragging(true);
  }

  function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();

    event.dataTransfer.dropEffect = "copy";
  }

  function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();

    dragCounter.current -= 1;

    if (dragCounter.current <= 0) {
      dragCounter.current = 0;
      setIsDragging(false);
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();

    dragCounter.current = 0;
    setIsDragging(false);

    addFiles(event.dataTransfer.files);
  }

  function updateItem(localId, changes) {
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
      "/api/images/upload",
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
      `/api/images/${uploadData.id}/detect`,
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
      detection: detectData.detection,
      crop: detectData.crop,
      status: "Cropping...",
    });

    const cropResponse = await fetch(
      `/api/images/${uploadData.id}/crop`,
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
        `${cropData.preview_url}?t=${Date.now()}`,
      status: "Completed",
    });
  }

  async function handleProcessAll() {
    if (
      items.length === 0 ||
      !outputFolder
    ) {
      return;
    }

    setIsProcessing(true);

    let completed = 0;
    let failed = 0;

    setUploadStatus(
      `Processing 0 / ${items.length}`
    );

    for (const item of items) {
      if (item.status === "cancelled") {
        completed += 1;

        setUploadStatus(
          `Processing ${completed} / ${items.length}`
        );

        continue;
      }

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
        `/api/images/${item.fileId}/rotate/${angle}`,
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
          `${data.preview_url}?t=${Date.now()}`,
        status: "Completed",
      });
    } catch (error) {
      updateItem(item.localId, {
        status: "Error",
        error: error.message,
      });
    }
  }

  async function handleCancel(item) {
    if (!item.fileId) {
      return;
    }

    try {
      updateItem(item.localId, {
        status: "Cancelling...",
        error: "",
      });

      const response = await fetch(
        `/api/images/${item.fileId}/cancel`,
        {
          method: "POST",
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Cancel failed"
        );
      }

      updateItem(item.localId, {
        status: "cancelled",
        croppedUrl: "",
        detection: null,
        crop: null,
        error: "",
      });
    } catch (error) {
      updateItem(item.localId, {
        status: "Error",
        error: error.message,
      });
    }
  }

  async function handleChooseOutputFolder() {
    try {
      setIsSelectingOutputFolder(true);

      const response = await fetch(
        "/api/settings/output-folder/select",
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Cannot select output folder"
        );
      }

      setOutputFolder(
        data.path || ""
      );

      if (data.selected) {
        setUploadStatus(
          "Output folder selected"
        );
      }
    } catch (error) {
      setUploadStatus(
        error.message
      );
    } finally {
      setIsSelectingOutputFolder(false);
    }
  }

  async function handleClearOutputFolder() {
    try {
      const response = await fetch(
        "/api/settings/output-folder/clear",
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Cannot clear output folder"
        );
      }

      setOutputFolder("");
      setUploadStatus(
        "Output folder cleared"
      );
    } catch (error) {
      setUploadStatus(
        error.message
      );
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

  return (
    <main className="app">
      <h1>PhotoCropAI</h1>

      <p>{backendStatus}</p>

      <section className="outputFolderPanel">
        <div>
          <strong>Output folder:</strong>

          <p
            className={
              outputFolder
                ? "outputFolderPath"
                : "outputFolderPath outputFolderMissing"
            }
          >
            {outputFolder || "Not selected"}
          </p>
        </div>

        <div className="outputFolderActions">
          <button
            type="button"
            onClick={handleChooseOutputFolder}
            disabled={
              isProcessing ||
              isSelectingOutputFolder
            }
          >
            {isSelectingOutputFolder
              ? "Selecting..."
              : "Choose output folder"}
          </button>

          <button
            type="button"
            onClick={handleClearOutputFolder}
            disabled={
              !outputFolder ||
              isProcessing ||
              isSelectingOutputFolder
            }
          >
            Clear output folder
          </button>
        </div>
      </section>

      {!outputFolder && (
        <p className="outputFolderWarning">
          Choose an output folder before processing images.
        </p>
      )}

      <section
        className={`dropZone ${
          isDragging ? "dragging" : ""
        }`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <p className="dropZoneTitle">
          Drag & drop images here
        </p>

        <p className="dropZoneText">
          or
        </p>

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
      </section>

      <section className="panel">
        <button
          type="button"
          onClick={handleProcessAll}
          disabled={
            items.length === 0 ||
            isProcessing ||
            !outputFolder
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
          {selectedFiles.length} / 20 images
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
                      src={item.previewUrl}
                      alt={item.file.name}
                      className="previewImage"
                    />

                    {item.detection &&
                      item.crop &&
                      item.status !==
                        "cancelled" && (
                        <>
                          <div
                            className="detectedBox"
                            style={{
                              left: `${
                                (
                                  item.detection.x /
                                  item.detection
                                    .image_width
                                ) * 100
                              }%`,
                              top: `${
                                (
                                  item.detection.y /
                                  item.detection
                                    .image_height
                                ) * 100
                              }%`,
                              width: `${
                                (
                                  item.detection.width /
                                  item.detection
                                    .image_width
                                ) * 100
                              }%`,
                              height: `${
                                (
                                  item.detection.height /
                                  item.detection
                                    .image_height
                                ) * 100
                              }%`,
                            }}
                          />

                          <div
                            className="cropBox"
                            style={{
                              left: `${
                                (
                                  item.crop.x1 /
                                  item.detection
                                    .image_width
                                ) * 100
                              }%`,
                              top: `${
                                (
                                  item.crop.y1 /
                                  item.detection
                                    .image_height
                                ) * 100
                              }%`,
                              width: `${
                                (
                                  item.crop.width /
                                  item.detection
                                    .image_width
                                ) * 100
                              }%`,
                              height: `${
                                (
                                  item.crop.height /
                                  item.detection
                                    .image_height
                                ) * 100
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
                      src={item.croppedUrl}
                      alt={`Processed ${item.file.name}`}
                      className="previewImage"
                    />
                  </div>
                )}
              </div>

              <div className="itemActions">
                <button
                  type="button"
                  onClick={() =>
                    handleRotate(
                      item,
                      270
                    )
                  }
                  disabled={
                    !item.croppedUrl ||
                    item.status ===
                      "cancelled" ||
                    item.status ===
                      "Cancelling..."
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
                  disabled={
                    !item.croppedUrl ||
                    item.status ===
                      "cancelled" ||
                    item.status ===
                      "Cancelling..."
                  }
                >
                  Rotate right
                </button>

                <button
                  type="button"
                  onClick={() =>
                    handleCancel(item)
                  }
                  disabled={
                    !item.fileId ||
                    item.status ===
                      "cancelled" ||
                    item.status ===
                      "Cancelling..."
                  }
                >
                  Cancel
                </button>
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