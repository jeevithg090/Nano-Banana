(() => {
    "use strict";

    const form = document.getElementById("imageForm");
    const fileInput = document.getElementById("images");
    const dropZone = document.getElementById("dropZone");
    const preview = document.getElementById("filePreview");
    const loading = document.getElementById("loading");
    const resultContainer = document.getElementById("resultContainer");
    const resultTitle = document.getElementById("resultTitle");
    const resultImage = document.getElementById("resultImage");
    const resultText = document.getElementById("resultText");
    const downloadBtn = document.getElementById("downloadBtn");
    const generateBtn = document.getElementById("generateBtn");
    const errorMessage = document.getElementById("errorMessage");
    const promptInput = document.getElementById("prompt");

    const maxImages = Number(form.dataset.maxImages) || 5;
    const maxBytes = (Number(form.dataset.maxUploadMb) || 16) * 1024 * 1024;
    const allowedTypes = new Set(fileInput.accept.split(","));
    const EXTENSIONS = { "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif" };

    let selectedFiles = [];
    let previewUrls = [];
    let resultUrl = null;

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.hidden = false;
    }

    function clearError() {
        errorMessage.hidden = true;
        errorMessage.textContent = "";
    }

    function renderPreview() {
        previewUrls.forEach((url) => URL.revokeObjectURL(url));
        previewUrls = [];
        preview.replaceChildren();

        selectedFiles.forEach((file, index) => {
            const url = URL.createObjectURL(file);
            previewUrls.push(url);

            const item = document.createElement("li");
            item.className = "file-preview-item";

            const img = document.createElement("img");
            img.src = url;
            img.alt = file.name;

            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "remove-file";
            remove.textContent = "×";
            remove.setAttribute("aria-label", `Remove ${file.name}`);
            remove.addEventListener("click", () => {
                selectedFiles.splice(index, 1);
                renderPreview();
                fileInput.focus();
            });

            item.append(img, remove);
            preview.append(item);
        });
    }

    function addFiles(fileList) {
        clearError();
        const incoming = Array.from(fileList);
        const rejected = incoming.filter((f) => !allowedTypes.has(f.type));
        const accepted = incoming.filter((f) => allowedTypes.has(f.type));

        let combined = selectedFiles.concat(accepted);
        if (combined.length > maxImages) {
            showError(`You can add at most ${maxImages} images; extra images were ignored.`);
            combined = combined.slice(0, maxImages);
        } else if (rejected.length) {
            showError(`Skipped unsupported file(s): ${rejected.map((f) => f.name).join(", ")}`);
        }

        const totalBytes = combined.reduce((sum, f) => sum + f.size, 0);
        if (totalBytes > maxBytes) {
            showError(`Selected images exceed the ${maxBytes / 1024 / 1024} MB upload limit.`);
            return;
        }
        selectedFiles = combined;
        renderPreview();
    }

    fileInput.addEventListener("change", () => {
        addFiles(fileInput.files);
        fileInput.value = "";
    });

    ["dragenter", "dragover"].forEach((name) =>
        dropZone.addEventListener(name, (e) => {
            e.preventDefault();
            dropZone.classList.add("dragover");
        })
    );
    ["dragleave", "drop"].forEach((name) =>
        dropZone.addEventListener(name, (e) => {
            e.preventDefault();
            dropZone.classList.remove("dragover");
        })
    );
    dropZone.addEventListener("drop", (e) => addFiles(e.dataTransfer.files));

    function setLoading(isLoading) {
        loading.hidden = !isLoading;
        generateBtn.disabled = isLoading;
        generateBtn.textContent = isLoading ? "Generating…" : "Generate image";
        form.setAttribute("aria-busy", String(isLoading));
    }

    function base64ToBlob(b64, mimeType) {
        const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
        return new Blob([bytes], { type: mimeType });
    }

    function showResult(data, prompt) {
        if (resultUrl) URL.revokeObjectURL(resultUrl);
        resultUrl = URL.createObjectURL(base64ToBlob(data.image, data.mime_type));

        resultImage.src = resultUrl;
        resultImage.alt = `Generated image for prompt: ${prompt}`;
        downloadBtn.href = resultUrl;
        downloadBtn.download = `nano-banana-${Date.now()}.${EXTENSIONS[data.mime_type] || "png"}`;

        resultText.textContent = data.text || "";
        resultText.hidden = !data.text;

        resultContainer.hidden = false;
        resultTitle.focus();
        resultContainer.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearError();

        const prompt = promptInput.value.trim();
        if (!prompt) {
            showError("Please enter a prompt.");
            promptInput.focus();
            return;
        }

        const formData = new FormData();
        formData.append("prompt", prompt);
        selectedFiles.forEach((file) => formData.append("images", file, file.name));

        setLoading(true);
        resultContainer.hidden = true;

        try {
            const response = await fetch("/generate", { method: "POST", body: formData });
            let data;
            try {
                data = await response.json();
            } catch {
                throw new Error(`Server returned an unexpected response (HTTP ${response.status}).`);
            }
            if (response.ok && data.success) {
                showResult(data, prompt);
            } else {
                showError(data.error || "Failed to generate image.");
            }
        } catch (err) {
            showError(err instanceof Error && err.message.startsWith("Server")
                ? err.message
                : "Network error. Please check your connection and try again.");
        } finally {
            setLoading(false);
        }
    });
})();
