import abc
import base64
# pyrefly: ignore [missing-import]
import cv2
import numpy as np

class CVOverlayStrategy(abc.ABC):
    """
    Interface for classical computer vision image processing strategies.
    Defines the contract to process a BGR numpy image and return an RGBA transparent overlay.
    """
    @abc.abstractmethod
    def process(self, img: np.ndarray) -> np.ndarray:
        pass

class CannyOverlayStrategy(CVOverlayStrategy):
    """
    Strategy for Canny Edge Detection overlay mask creation.
    """
    def __init__(self, sigma: float = 0.33):
        self.sigma = sigma

    def _auto_canny(self, image: np.ndarray) -> np.ndarray:
        v = np.median(image)
        lower = int(max(0, (1.0 - self.sigma) * v))
        upper = int(min(255, (1.0 + self.sigma) * v))
        return cv2.Canny(image, lower, upper)

    def process(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = self._auto_canny(gray)

        h, w = edges.shape
        overlay = np.zeros((h, w, 4), dtype=np.uint8)

        # Dilate edges slightly to make notches/lines glow
        kernel = np.ones((2, 2), np.uint8)
        dilated_edges = cv2.dilate(edges, kernel, iterations=1)

        # Bright neon green (GFP style): B=0, G=255, R=0, A=255
        overlay[dilated_edges > 0] = [0, 255, 0, 255]
        return overlay

class OtsuOverlayStrategy(CVOverlayStrategy):
    """
    Strategy for Otsu cell body segmentation overlay mask creation.
    """
    def process(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresholded = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        h, w = thresholded.shape
        overlay = np.zeros((h, w, 4), dtype=np.uint8)

        # Semi-transparent neon orange (cell bodies): B=0, G=100, R=255, A=120
        overlay[thresholded > 0] = [0, 100, 255, 120]
        return overlay

class CVProcessorService:
    """
    Context executor service implementing strategy selection logic.
    """
    def __init__(self):
        self._strategies = {
            "canny": CannyOverlayStrategy(),
            "otsu": OtsuOverlayStrategy()
        }

    def process_image(self, raw_image_base64: str, process_type: str) -> str:
        """
        Decodes a raw base64 BGR buffer, executes the registered overlay strategy,
        and returns the resulting transparent overlay as a base64 PNG.
        """
        strategy = self._strategies.get(process_type)
        if not strategy:
            raise ValueError(f"Unknown overlay processing strategy '{process_type}'.")

        try:
            img_bytes = base64.b64decode(raw_image_base64)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Failed to decode image BGR buffer.")

            overlay_img = strategy.process(img)
            
            _, buffer = cv2.imencode('.png', overlay_img)
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"Strategy '{process_type}' failed: {e}")

    def generate_thumbnail(self, raw_image_base64: str, width: int = 120, height: int = 90) -> str:
        """
        Resizes a base64 BGR image to thumbnail sizes.
        """
        try:
            img_bytes = base64.b64decode(raw_image_base64)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Failed to decode image buffer.")

            thumbnail = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
            _, buffer = cv2.imencode('.png', thumbnail)
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"Thumbnail generation failed: {e}")

# Singleton processor context service
cv_processor_service = CVProcessorService()

# Legacy compatibility wrapper
def process_microscopy_image(raw_image_base64: str) -> str:
    return cv_processor_service.process_image(raw_image_base64, "canny")
