// Pharmacist & Result Prescription Image Workbench: Zoom, Pan, Rotate, Contrast Enhance

document.addEventListener("DOMContentLoaded", () => {
  const img = document.getElementById("inspect-img");
  if (!img) return;

  let zoom = 1.0;
  let rotation = 0;
  let invert = false;
  let isDragging = false;
  let startX = 0, startY = 0, translateX = 0, translateY = 0;

  function updateTransform() {
    img.style.transform = `translate(${translateX}px, ${translateY}px) scale(${zoom}) rotate(${rotation}deg)`;
    img.style.filter = invert ? "invert(1) contrast(1.4) brightness(0.9)" : "none";
  }

  // Zoom In
  document.getElementById("btn-zoom-in")?.addEventListener("click", () => {
    zoom = Math.min(zoom + 0.25, 3.5);
    updateTransform();
  });

  // Zoom Out
  document.getElementById("btn-zoom-out")?.addEventListener("click", () => {
    zoom = Math.max(zoom - 0.25, 0.5);
    updateTransform();
  });

  // Rotate Right
  document.getElementById("btn-rotate-right")?.addEventListener("click", () => {
    rotation = (rotation + 90) % 360;
    updateTransform();
  });

  // Rotate Left
  document.getElementById("btn-rotate-left")?.addEventListener("click", () => {
    rotation = (rotation - 90 + 360) % 360;
    updateTransform();
  });

  // Contrast / Invert Toggle (crucial for faint blue or red ballpoint ink)
  document.getElementById("btn-invert")?.addEventListener("click", () => {
    invert = !invert;
    updateTransform();
  });

  // Reset
  document.getElementById("btn-reset")?.addEventListener("click", () => {
    zoom = 1.0;
    rotation = 0;
    invert = false;
    translateX = 0;
    translateY = 0;
    updateTransform();
  });

  // Mouse drag pan support
  img.addEventListener("mousedown", (e) => {
    if (zoom > 1.0) {
      isDragging = true;
      startX = e.clientX - translateX;
      startY = e.clientY - translateY;
      img.style.cursor = "grabbing";
    }
  });

  window.addEventListener("mousemove", (e) => {
    if (isDragging) {
      translateX = e.clientX - startX;
      translateY = e.clientY - startY;
      updateTransform();
    }
  });

  window.addEventListener("mouseup", () => {
    isDragging = false;
    img.style.cursor = zoom > 1.0 ? "grab" : "default";
  });
});
