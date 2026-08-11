import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [backendStatus, setBackendStatus] = useState("Перевірка backend...");
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [uploadStatus, setUploadStatus] = useState("");
  const [imageInfo, setImageInfo] = useState(null);
  const [detectedBox, setDetectedBox] = useState(null);

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
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  function handleFileChange(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setUploadStatus("");
    setImageInfo(null);
    setDetectedBox(null);
  }

  async function handleUpload() {
    if (!selectedFile) {
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    setUploadStatus("Loading...");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/images/upload",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Loading error");
      }

      setImageInfo(data);

      const detectResponse = await fetch(
        `http://127.0.0.1:8000/api/images/${data.id}/detect`,
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

      setDetectedBox(detectData);
      setUploadStatus("Object detected");
    } catch (error) {
      setUploadStatus(error.message);
    }
  }

  return (
    <main className="app">
      <h1>PhotoCropAI</h1>
      <p>{backendStatus}</p>

      <section className="panel">
        <label className="fileButton">
          Choose image
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp,image/bmp,image/tiff"
            onChange={handleFileChange}
            hidden
          />
        </label>

        <button
          type="button"
          onClick={handleUpload}
          disabled={!selectedFile}
        >
          Submit for detection
        </button>
      </section>

      {previewUrl && (
        <section className="previewPanel">
          <div className="imageWrapper">
            <img
              src={previewUrl}
              alt="Preview"
              className="previewImage"
            />

           {detectedBox && (
  <>
    <div
      className="detectedBox"
      style={{
        left: `${(
          detectedBox.detection.x /
          detectedBox.detection.image_width
        ) * 100}%`,

        top: `${(
          detectedBox.detection.y /
          detectedBox.detection.image_height
        ) * 100}%`,

        width: `${(
          detectedBox.detection.width /
          detectedBox.detection.image_width
        ) * 100}%`,

        height: `${(
          detectedBox.detection.height /
          detectedBox.detection.image_height
        ) * 100}%`,
      }}
    />

    <div
      className="cropBox"
      style={{
        left: `${(
          detectedBox.crop.x1 /
          detectedBox.detection.image_width
        ) * 100}%`,

        top: `${(
          detectedBox.crop.y1 /
          detectedBox.detection.image_height
        ) * 100}%`,

        width: `${(
          detectedBox.crop.width /
          detectedBox.detection.image_width
        ) * 100}%`,

        height: `${(
          detectedBox.crop.height /
          detectedBox.detection.image_height
        ) * 100}%`,
      }}
    />
  </>
)}
          </div>
        </section>
      )}

      {uploadStatus && <p>{uploadStatus}</p>}

      {imageInfo && (
        <section className="imageInfo">
          <p>File: {imageInfo.filename}</p>
          <p>
            Size: {imageInfo.width} × {imageInfo.height} px
          </p>
          <p>Format: {imageInfo.format}</p>
          <p>Amount: {imageInfo.size_bytes} bytes</p>
        </section>
      )}

      {detectedBox && (
        <section className="imageInfo">
          <p>
            Found area: {detectedBox.width} ×{" "}
            {detectedBox.height} px
          </p>
        </section>
      )}
    </main>
  );
}

export default App;