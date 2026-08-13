import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [backendStatus, setBackendStatus] = useState("Loading...");
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [items, setItems] = useState([]);
  const [uploadStatus, setUploadStatus] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Backend error");
        }

        return response.json();
      })
      .then(() => setBackendStatus("Backend is working"))
      .catch(() => setBackendStatus("Backend error"));
  }, []);

  useEffect(() => {
    return () => {
      items.forEach((item) => {
        if (item.previewUrl) {
          URL.revokeObjectURL(item.previewUrl);
        }
      });
    };
  }, [items]);

  function handleFileChange(event) {
    const files = Array.from(
      event.target.files || []
    ).slice(0, 20);

    items.forEach((item) => {
      if (item.previewUrl) {
        URL.revokeObjectURL(item.previewUrl);
      }
    });

    const newItems = files.map((file, index) => ({
      localId: `${Date.now()}-${index}`,
      file,
      fileId: null,
      previewUrl: URL.createObjectURL(file),
      croppedUrl: "",
      detection: null,
      crop: null,
      status: "Waiting",
      error: "",
    }));

    setSelectedFiles(files);
    setItems(newItems);
    setUploadStatus("");
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
    formData.append("file", item.file);

    const uploadResponse = await fetch(
      "http://127.0.0.1:8000/api/images/upload",
      {
        method: "POST",
        body: formData,
      }
    );

    const uploadData = await uploadResponse.json();

    if (!uploadResponse.ok) {
      throw new Error(
        uploadData.detail || "Loading error"
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

    const detectData = await detectResponse.json();

    if (!detectResponse.ok) {
      throw new Error(
        detectData.detail || "Object detection error"
      );
    }

    updateItem(item.localId, {
      detection: detectData.detection,
      crop: detectData.crop,
      status: "Cropping...",
    });

    const cropResponse = await fetch(
      `http://127.0.0.1:8000/api/images/${uploadData.id}/crop`,
      {
        method: "POST",
      }
    );

    const cropData = await cropResponse.json();

    if (!cropResponse.ok) {
      throw new Error(
        cropData.detail || "Cropping error"
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
    if (selectedFiles.length === 0) {
      return;
    }

    setIsProcessing(true);
    setUploadStatus(
      `Processing 0 / ${selectedFiles.length}`
    );

    let completed = 0;

    for (const item of items) {
      try {
        await processSingleImage(item);
      } catch (error) {
        updateItem(item.localId, {
          status: "Error",
          error: error.message,
        });
      }

      completed += 1;

      setUploadStatus(
        `Processing ${completed} / ${selectedFiles.length}`
      );
    }

    setUploadStatus(
      `Finished: ${completed} / ${selectedFiles.length}`
    );

    setIsProcessing(false);
  }

  async function handleRotate(item, angle) {
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

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Rotation error"
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
            selectedFiles.length === 0 ||
            isProcessing
          }
        >
          {isProcessing
            ? "Processing..."
            : "Process all"}
        </button>
      </section>

      {selectedFiles.length > 0 && (
        <p>
          Selected: {selectedFiles.length} image
          {selectedFiles.length !== 1 ? "s" : ""}
        </p>
      )}

      {uploadStatus && (
        <p>{uploadStatus}</p>
      )}

      <section className="batchGrid">
        {items.map((item, index) => (
          <article
            className="batchItem"
            key={item.localId}
          >
            <h2>
              {index + 1}. {item.file.name}
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

                  {item.detection && item.crop && (
                    <>
                      <div
                        className="detectedBox"
                        style={{
                          left: `${
                            (
                              item.detection.x /
                              item.detection.image_width
                            ) * 100
                          }%`,
                          top: `${
                            (
                              item.detection.y /
                              item.detection.image_height
                            ) * 100
                          }%`,
                          width: `${
                            (
                              item.detection.width /
                              item.detection.image_width
                            ) * 100
                          }%`,
                          height: `${
                            (
                              item.detection.height /
                              item.detection.image_height
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
                              item.detection.image_width
                            ) * 100
                          }%`,
                          top: `${
                            (
                              item.crop.y1 /
                              item.detection.image_height
                            ) * 100
                          }%`,
                          width: `${
                            (
                              item.crop.width /
                              item.detection.image_width
                            ) * 100
                          }%`,
                          height: `${
                            (
                              item.crop.height /
                              item.detection.image_height
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
                    alt="Cropped result"
                    className="previewImage"
                  />

                  <div className="rotateControls">
                    <button
                      type="button"
                      onClick={() =>
                        handleRotate(item, 270)
                      }
                    >
                      Rotate left
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        handleRotate(item, 90)
                      }
                    >
                      Rotate right
                    </button>
                  </div>
                </div>
              )}
            </div>

            <p>Status: {item.status}</p>

            {item.error && (
              <p className="errorMessage">
                {item.error}
              </p>
            )}
          </article>
        ))}
      </section>
    </main>
  );
}

export default App;