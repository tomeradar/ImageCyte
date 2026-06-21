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

def process_microscopy_image(raw_image_base64: str) -> str:
    """
    Applies classical computer vision (Canny Edge Detection) to highlight cell boundaries,
    overlays the edges in bright neon green (GFP style) over the original image, and returns
    the result as a base64-encoded PNG string.
    """
    try:
        # Decode base64 string to numpy buffer
        img_bytes = base64.b64decode(raw_image_base64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Failed to decode image data; invalid image format.")

        # Convert to grayscale for edge detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Generate edge mask
        edges = auto_canny(gray)

        # Create overlay image
        processed_img = img.copy()
        
        # Color edges in neon green (BGR: 0, 255, 0)
        # We can also dilate the edges slightly to make them more visible/glowing
        kernel = np.ones((2, 2), np.uint8)
        dilated_edges = cv2.dilate(edges, kernel, iterations=1)
        
        processed_img[dilated_edges > 0] = [0, 255, 0]

        # Encode back to PNG
        _, buffer = cv2.imencode('.png', processed_img)
        processed_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return processed_base64
    except Exception as e:
        # In case of any processing failure, return the original image as fallback
        # and log/raise the error appropriately
        raise RuntimeError(f"Failed to process microscopy image: {e}")
