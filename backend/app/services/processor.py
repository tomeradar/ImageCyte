import base64
import cv2
import numpy as np

def auto_canny(image: np.ndarray, sigma: float = 0.33) -> np.ndarray:
    """
    Computes Canny edge thresholds adaptively based on the median pixel intensity of the image.
    """
    v = np.median(image)
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    return cv2.Canny(image, lower, upper)

def generate_canny_overlay(raw_image_base64: str) -> str:
    """
    Applies classical CV Canny Edge Detection and returns a transparent PNG overlay
    containing only the glowing neon green boundaries.
    """
    try:
        img_bytes = base64.b64decode(raw_image_base64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image data.")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = auto_canny(gray)

        # Create transparent RGBA image
        h, w = edges.shape
        overlay = np.zeros((h, w, 4), dtype=np.uint8)

        # Dilate edges to make them glow/pop
        kernel = np.ones((2, 2), np.uint8)
        dilated_edges = cv2.dilate(edges, kernel, iterations=1)

        # Set green color with 255 alpha for detected edges (B=0, G=255, R=0, A=255)
        overlay[dilated_edges > 0] = [0, 255, 0, 255]

        _, buffer = cv2.imencode('.png', overlay)
        return base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"Canny processing failed: {e}")

def generate_otsu_overlay(raw_image_base64: str) -> str:
    """
    Applies Otsu's thresholding to isolate cell bodies and returns a transparent PNG
    overlay containing semi-transparent neon orange mask overlays on cells.
    """
    try:
        img_bytes = base64.b64decode(raw_image_base64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image data.")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Otsu's Thresholding
        _, thresholded = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Create transparent RGBA image
        h, w = thresholded.shape
        overlay = np.zeros((h, w, 4), dtype=np.uint8)

        # Set neon orange/red with 120 alpha for cells (B=0, G=100, R=255, A=120)
        overlay[thresholded > 0] = [0, 100, 255, 120]

        _, buffer = cv2.imencode('.png', overlay)
        return base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"Otsu processing failed: {e}")

def generate_thumbnail(raw_image_base64: str, width: int = 120, height: int = 90) -> str:
    """
    Generates a low-resolution base64 PNG thumbnail of the original image for fast history scrubbing tooltips.
    """
    try:
        img_bytes = base64.b64decode(raw_image_base64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image data.")

        thumbnail = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
        _, buffer = cv2.imencode('.png', thumbnail)
        return base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"Thumbnail generation failed: {e}")

def process_microscopy_image(raw_image_base64: str) -> str:
    """
    Legacy wrapper for compatibility: returns canny overlay.
    """
    return generate_canny_overlay(raw_image_base64)
