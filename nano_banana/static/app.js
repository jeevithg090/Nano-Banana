(() => {
    "use strict";

    const $ = (id) => document.getElementById(id);

    const form = $("imageForm");
    if (!form) return;

    const promptInput = $("prompt");
    const promptCount = $("promptCount");
    const promptError = $("promptError");
    const fileInput = $("images");
    const dropZone = $("dropZone");
    const imagesError = $("imagesError");
    const previewWrap = $("previewWrap");
    const preview = $("filePreview");
    const imageCount = $("imageCount");
    const clearImages = $("clearImages");
    const generateBtn = $("generateBtn");
    const generateLabel = $("generateLabel");

    const resultPanel = $("resultPanel");
    const resultTitle = $("resultTitle");
    const states = {
        empty: $("stateEmpty"),
        loading: $("stateLoading"),
        error: $("stateError"),
        success: $("stateSuccess"),
    };
    const elapsed = $("elapsed");
    const errorMessage = $("errorMessage");
    const retryBtn = $("retryBtn");
    const resultImage = $("resultImage");
    const resultText = $("resultText");
    const downloadBtn = $("downloadBtn");
    const reuseBtn = $("reuseBtn");
    const liveStatus = $("liveStatus");

    const configured = !generateBtn.disabled;
    const maxImages = Number(form.dataset.maxImages) || 5;
    const maxUploadMb = Number(form.dataset.maxUploadMb) || 16;
    const maxBytes = maxUploadMb * 1024 * 1024;
    const maxPromptChars = Number(form.dataset.maxPromptChars) || 2000;
    const allowedTypes = new Set(fileInput.accept.split(","));
    const EXTENSIONS = { "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif" };

    let selectedFiles = [];
    let previewUrls = [];
    let result = null; // { url, blob, mimeType, prompt }
    let timer = null;
    let busy = false;

    /* ---------- helpers ---------- */

    function announce(message) {
        liveStatus.textContent = "";
        // A fresh text node makes screen readers announce repeated messages too.
        window.setTimeout(() => { liveStatus.textContent = message; }, 50);
    }

    function setFieldError(input, el, message) {
        el.textContent = message || "";
        el.hidden = !message;
        if (message) input.setAttribute("aria-invalid", "true");
        else input.removeAttribute("aria-invalid");
    }

    function showState(name) {
        Object.entries(states).forEach(([key, el]) => { el.hidden = key !== name; });
        resultPanel.setAttribute("aria-busy", String(name === "loading"));
    }

    function plural(n, word) {
        return `${n} ${word}${n === 1 ? "" : "s"}`;
    }

    /* ---------- prompt ---------- */

    function updateCount() {
        const length = promptInput.value.length;
        promptCount.textContent = `${length} / ${maxPromptChars}`;
        promptCount.classList.toggle("is-near-limit", length >= maxPromptChars * 0.9);
    }

    promptInput.addEventListener("input", () => {
        updateCount();
        if (promptInput.value.trim()) setFieldError(promptInput, promptError, "");
    });

    promptInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            form.requestSubmit();
        }
    });

    document.querySelectorAll(".chip[data-prompt]").forEach((chip) => {
        chip.addEventListener("click", () => {
            promptInput.value = chip.dataset.prompt.slice(0, maxPromptChars);
            updateCount();
            setFieldError(promptInput, promptError, "");
            promptInput.focus();
        });
    });

    /* ---------- images ---------- */

    const removeIcon =
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';

    function renderPreview() {
        previewUrls.forEach((url) => URL.revokeObjectURL(url));
        previewUrls = [];
        preview.replaceChildren();

        selectedFiles.forEach((file, index) => {
            const url = URL.createObjectURL(file);
            previewUrls.push(url);

            const item = document.createElement("li");
            item.className = "preview";

            const img = document.createElement("img");
            img.src = url;
            img.alt = `Image ${index + 1}: ${file.name}`;

            const badge = document.createElement("span");
            badge.className = "preview__index";
            badge.setAttribute("aria-hidden", "true");
            badge.textContent = String(index + 1);

            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "preview__remove";
            remove.innerHTML = removeIcon; // static markup, no user data
            remove.setAttribute("aria-label", `Remove image ${index + 1}, ${file.name}`);
            remove.addEventListener("click", () => {
                selectedFiles.splice(index, 1);
                renderPreview();
                announce(`Removed ${file.name}. ${plural(selectedFiles.length, "image")} selected.`);
                const buttons = preview.querySelectorAll(".preview__remove");
                (buttons[Math.min(index, buttons.length - 1)] || fileInput).focus();
            });

            item.append(img, badge, remove);
            preview.append(item);
        });

        previewWrap.hidden = selectedFiles.length === 0;
        imageCount.textContent = `${selectedFiles.length} of ${maxImages} images`;
        const full = selectedFiles.length >= maxImages;
        dropZone.classList.toggle("is-disabled", full);
        fileInput.disabled = full;
    }

    function addFiles(fileList) {
        const incoming = Array.from(fileList);
        if (!incoming.length) return;

        const accepted = incoming.filter((f) => allowedTypes.has(f.type));
        const rejected = incoming.filter((f) => !allowedTypes.has(f.type));
        const messages = [];

        let combined = selectedFiles.concat(accepted);
        if (combined.length > maxImages) {
            messages.push(`You can add up to ${maxImages} images, so ${plural(combined.length - maxImages, "image")} ${combined.length - maxImages === 1 ? "was" : "were"} left out.`);
            combined = combined.slice(0, maxImages);
        }
        if (rejected.length) {
            messages.push(`Unsupported file type: ${rejected.map((f) => f.name).join(", ")}. Use PNG, JPEG, WEBP, GIF or BMP.`);
        }

        const totalBytes = combined.reduce((sum, f) => sum + f.size, 0);
        if (totalBytes > maxBytes) {
            setFieldError(fileInput, imagesError, `These images add up to ${(totalBytes / 1048576).toFixed(1)} MB, over the ${maxUploadMb} MB limit. Try smaller or fewer images.`);
            return;
        }

        setFieldError(fileInput, imagesError, messages.join(" "));
        const added = combined.length - selectedFiles.length;
        selectedFiles = combined;
        renderPreview();
        if (added > 0) announce(`Added ${plural(added, "image")}. ${plural(selectedFiles.length, "image")} selected.`);
    }

    fileInput.addEventListener("change", () => {
        addFiles(fileInput.files);
        fileInput.value = "";
    });

    clearImages.addEventListener("click", () => {
        selectedFiles = [];
        renderPreview();
        setFieldError(fileInput, imagesError, "");
        announce("All images removed.");
        fileInput.focus();
    });

    let dragDepth = 0;
    dropZone.addEventListener("dragenter", (e) => {
        e.preventDefault();
        dragDepth += 1;
        dropZone.classList.add("is-dragover");
    });
    dropZone.addEventListener("dragover", (e) => e.preventDefault());
    dropZone.addEventListener("dragleave", () => {
        dragDepth = Math.max(0, dragDepth - 1);
        if (!dragDepth) dropZone.classList.remove("is-dragover");
    });
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dragDepth = 0;
        dropZone.classList.remove("is-dragover");
        if (selectedFiles.length >= maxImages) {
            setFieldError(fileInput, imagesError, `You already have ${maxImages} images. Remove one to add another.`);
            return;
        }
        addFiles(e.dataTransfer.files);
    });
    // Dropping a file just outside the zone should not navigate away from the page.
    window.addEventListener("dragover", (e) => e.preventDefault());
    window.addEventListener("drop", (e) => e.preventDefault());

    /* ---------- generation ---------- */

    function setLoading(isLoading) {
        busy = isLoading;
        generateBtn.disabled = isLoading || !configured;
        generateBtn.classList.toggle("is-busy", isLoading);
        generateLabel.textContent = isLoading ? "Generating…" : "Generate image";
        form.setAttribute("aria-busy", String(isLoading));

        window.clearInterval(timer);
        if (isLoading) {
            const started = Date.now();
            elapsed.textContent = "0";
            timer = window.setInterval(() => {
                elapsed.textContent = String(Math.round((Date.now() - started) / 1000));
            }, 1000);
        }
    }

    function base64ToBlob(b64, mimeType) {
        const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
        return new Blob([bytes], { type: mimeType });
    }

    function showResult(data, prompt) {
        if (result) URL.revokeObjectURL(result.url);
        const blob = base64ToBlob(data.image, data.mime_type);
        result = { url: URL.createObjectURL(blob), blob, mimeType: data.mime_type, prompt };

        resultImage.src = result.url;
        resultImage.alt = `Generated image for the prompt: ${prompt}`;
        downloadBtn.href = result.url;
        downloadBtn.download = `nano-banana-${Date.now()}.${EXTENSIONS[data.mime_type] || "png"}`;

        resultText.textContent = data.text || "";
        resultText.hidden = !data.text;

        showState("success");
        announce("Your image is ready.");
        resultTitle.focus({ preventScroll: true });
        if (window.matchMedia("(max-width: 899px)").matches) {
            resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    function showFailure(message) {
        errorMessage.textContent = message;
        showState("error");
        resultTitle.focus({ preventScroll: true });
        if (window.matchMedia("(max-width: 899px)").matches) {
            resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (busy || !configured) return;

        const prompt = promptInput.value.trim();
        if (!prompt) {
            setFieldError(promptInput, promptError, "Please describe the image you want to create.");
            promptInput.focus();
            return;
        }
        setFieldError(promptInput, promptError, "");

        const formData = new FormData();
        formData.append("prompt", prompt);
        selectedFiles.forEach((file) => formData.append("images", file, file.name));

        setLoading(true);
        showState("loading");
        announce("Generating your image. This can take up to a minute.");

        try {
            const response = await fetch("/generate", { method: "POST", body: formData });
            let data;
            try {
                data = await response.json();
            } catch {
                throw new Error(`The server returned an unexpected response (HTTP ${response.status}). Please try again.`);
            }
            if (response.ok && data.success) showResult(data, prompt);
            else showFailure(data.error || "Image generation failed. Please try again.");
        } catch (err) {
            showFailure(err instanceof Error && err.message.startsWith("The server")
                ? err.message
                : "Couldn't reach the server. Check your connection and try again.");
        } finally {
            setLoading(false);
        }
    });

    retryBtn.addEventListener("click", () => form.requestSubmit());

    reuseBtn.addEventListener("click", () => {
        if (!result) return;
        if (selectedFiles.length >= maxImages) {
            setFieldError(fileInput, imagesError, `You already have ${maxImages} images. Remove one to reuse the result.`);
            fileInput.closest(".field").scrollIntoView({ behavior: "smooth", block: "center" });
            return;
        }
        const ext = EXTENSIONS[result.mimeType] || "png";
        const file = new File([result.blob], `generated-${selectedFiles.length + 1}.${ext}`, { type: result.mimeType });
        addFiles([file]);
        promptInput.focus();
        promptInput.setSelectionRange(promptInput.value.length, promptInput.value.length);
        announce("Generated image added as an input. Edit the prompt to refine it.");
    });

    if (/Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)) {
        const modKey = $("modKey");
        if (modKey) modKey.textContent = "⌘";
    }

    updateCount();
    renderPreview();
})();
