// RxScan Core Application Logic (Theme, Mobile Drawer, Drag & Drop Upload, UX Micro-interactions)

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initMobileDrawer();
  initDropzone();
  initScanSubmit();
  initLiveSearch();
  initServiceWorker();
});

function initServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/scanner/sw.js").catch(() => {});
  }
}

// Theme Management (Light / Dark Mode)
function initTheme() {
  const savedTheme = localStorage.getItem("rxscan_theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeButtons(savedTheme);

  document.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      const nextTheme = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", nextTheme);
      localStorage.setItem("rxscan_theme", nextTheme);
      updateThemeButtons(nextTheme);
    });
  });
}

function updateThemeButtons(theme) {
  document.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
    btn.innerHTML = theme === "dark" ? "☀️ Light mode" : "🌙 Dark mode";
  });
}

// Mobile Drawer
function initMobileDrawer() {
  const toggleBtn = document.getElementById("mobile-menu-toggle");
  const side = document.querySelector(".side");
  if (toggleBtn && side) {
    toggleBtn.addEventListener("click", () => {
      side.classList.toggle("open");
    });

    // Close when clicking outside on mobile
    document.addEventListener("click", (e) => {
      if (side.classList.contains("open") && !side.contains(e.target) && !toggleBtn.contains(e.target)) {
        side.classList.remove("open");
      }
    });
  }
}

// Interactive Drag & Drop File Upload with Instant Preview
function initDropzone() {
  const dropzone = document.getElementById("rx-dropzone");
  const fileInput = document.getElementById("id_image");
  const previewBox = document.getElementById("preview-box");
  const previewImg = document.getElementById("preview-img");
  const dropzoneTitle = document.getElementById("dropzone-title");

  if (!dropzone || !fileInput) return;

  ["dragenter", "dragover"].forEach((event) => {
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((event) => {
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      handleFilePreview(fileInput.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files.length > 0) {
      handleFilePreview(fileInput.files[0]);
    }
  });

  function handleFilePreview(file) {
    if (!file) return;
    if (dropzoneTitle) {
      dropzoneTitle.textContent = `Selected: ${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
    }
    if (file.type.startsWith("image/") && previewBox && previewImg) {
      const reader = new FileReader();
      reader.onload = (e) => {
        previewImg.src = e.target.result;
        previewBox.style.display = "block";
      };
      reader.readAsDataURL(file);
    } else if (previewBox) {
      previewBox.style.display = "none";
    }
  }
}

// Scanning HUD & Processing Spinner
function initScanSubmit() {
  const form = document.querySelector("form.upload-form");
  const submitBtn = document.getElementById("scan-submit-btn");
  if (form && submitBtn) {
    form.addEventListener("submit", () => {
      submitBtn.disabled = true;
      submitBtn.innerHTML = `
        <span style="display:inline-block;animation:spin 1s linear infinite;margin-right:8px">⌛</span>
        Running OpenCV & OCR Analysis...
      `;
    });
  }
}

// Instant Filter for Medicine Table
function initLiveSearch() {
  const searchInput = document.getElementById("live-med-search");
  const rows = document.querySelectorAll(".med-table-row");
  if (searchInput && rows.length > 0) {
    searchInput.addEventListener("input", () => {
      const query = searchInput.value.toLowerCase().trim();
      rows.forEach((row) => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? "" : "none";
      });
    });
  }
}
