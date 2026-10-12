"""Image quality checks and OpenCV preprocessing."""
import cv2
import numpy as np


def _load(path):
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError("The file could not be opened as an image.")
    return img


def _resize_width(img, width):
    h, w = img.shape[:2]
    scale = width / float(w)
    interp = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    return cv2.resize(img, (width, int(h * scale)), interpolation=interp)


def assess_quality(path):
    """Return {'ok': bool, 'issues': [...], 'blur': float, 'brightness': float}."""
    try:
        img = _load(path)
    except ValueError as exc:
        return {"ok": False, "issues": [str(exc)], "blur": 0, "brightness": 0}
    h, w = img.shape[:2]
    gray = cv2.cvtColor(_resize_width(img, 1000), cv2.COLOR_BGR2GRAY)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    contrast = float(gray.std())
    issues = []
    if min(h, w) < 300:
        issues.append("resolution is too low")
    if blur < 25:
        issues.append("image is blurry")
    if brightness < 60:
        issues.append("image is too dark")
    if contrast < 20:
        issues.append("contrast is too low")
    return {"ok": not issues, "issues": issues, "blur": round(blur, 1), "brightness": round(brightness, 1)}


def _deskew(gray):
    inv = cv2.bitwise_not(gray)
    _, bw = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(bw > 0))
    if len(coords) < 200:
        return gray
    angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
    # Normalise to (-45, 45] regardless of OpenCV version conventions.
    if angle > 45:
        angle -= 90
    elif angle < -45:
        angle += 90
    if abs(angle) < 0.5 or abs(angle) > 15:
        return gray
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def preprocess(path):
    """Resize -> grayscale -> denoise -> contrast -> deskew. Returns a grayscale array."""
    img = _load(path)
    img = _resize_width(img, 1800 if img.shape[1] < 1800 else min(img.shape[1], 2400))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    gray = _deskew(gray)
    return gray
