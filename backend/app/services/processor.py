import abc
import base64
# pyrefly: ignore [missing-import]
import cv2
import numpy as np
import logging
from app.core.exceptions import handle_cv_errors, ImageProcessingError

logger = logging.getLogger(__name__)

def get_placeholder_thumbnail_base64() -> str:
    """
    Generates a 120x90 solid gray placeholder image with red "Error" text,
    encoded as a base64 string. Fallbacks to a 1x1 pixel image if cv2 fails.
    """
    try:
        # 120x90 gray background
        img = np.full((90, 120, 3), 200, dtype=np.uint8)
        # Draw red "Error" text
        cv2.putText(img, "Error", (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        _, buffer = cv2.imencode('.png', img)
        return base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to generate custom fallback thumbnail: {e}", exc_info=True)
        # 1x1 gray pixel PNG base64 fallback
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mMs+Q8AAQcBRzR5X6gAAAAASUVORK5CYII="

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

    @handle_cv_errors()
    def process_image(self, raw_image_base64: str, process_type: str) -> str:
        """
        Decodes a raw base64 BGR buffer, executes the registered overlay strategy,
        and returns the resulting transparent overlay as a base64 PNG.
        """
        strategy = self._strategies.get(process_type)
        if not strategy:
            raise ValueError(f"Unknown overlay processing strategy '{process_type}'.")

        img_bytes = base64.b64decode(raw_image_base64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image BGR buffer.")

        overlay_img = strategy.process(img)
        
        _, buffer = cv2.imencode('.png', overlay_img)
        return base64.b64encode(buffer).decode('utf-8')

    @handle_cv_errors(fallback_factory=get_placeholder_thumbnail_base64)
    def generate_thumbnail(self, raw_image_base64: str, width: int = 120, height: int = 90) -> str:
        """
        Resizes a base64 BGR image to thumbnail sizes. Falls back to a custom gray placeholder on error.
        """
        img_bytes = base64.b64decode(raw_image_base64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image buffer.")

        thumbnail = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
        _, buffer = cv2.imencode('.png', thumbnail)
        return base64.b64encode(buffer).decode('utf-8')

    def is_valid_image(self, raw_image_base64: str) -> bool:
        """
        Validates if a raw base64 string can be successfully decoded by OpenCV.
        """
        try:
            img_bytes = base64.b64decode(raw_image_base64)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return img is not None
        except Exception:
            return False

# Singleton processor context service
cv_processor_service = CVProcessorService()
