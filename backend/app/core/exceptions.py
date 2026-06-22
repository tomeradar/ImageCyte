import functools
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorCode(str, Enum):
    UPSTREAM_CONNECTION = "ERR_UPSTREAM_CONNECTION"
    UPSTREAM_AUTH = "ERR_UPSTREAM_AUTH"
    UPSTREAM_MALFORMED_DATA = "ERR_UPSTREAM_MALFORMED_DATA"
    DATABASE_OPERATION = "ERR_DATABASE_OPERATION"
    QUEUE_OPERATION = "ERR_QUEUE_OPERATION"
    IMAGE_DECODING = "ERR_IMAGE_DECODING"
    IMAGE_PROCESSING = "ERR_IMAGE_PROCESSING"
    THUMBNAIL_GENERATION = "ERR_THUMBNAIL_GENERATION"
    UNKNOWN = "ERR_UNKNOWN"

class AppException(Exception):
    """Base exception for all managed application errors."""
    def __init__(self, message: str, error_code: ErrorCode, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

# Concrete subclasses
class UpstreamConnectionError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ErrorCode.UPSTREAM_CONNECTION, details)

class UpstreamAuthError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ErrorCode.UPSTREAM_AUTH, details)

class UpstreamMalformedDataError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ErrorCode.UPSTREAM_MALFORMED_DATA, details)

class DatabaseError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ErrorCode.DATABASE_OPERATION, details)

class QueueError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ErrorCode.QUEUE_OPERATION, details)

class ImageDecodingError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ErrorCode.IMAGE_DECODING, details)

class ImageProcessingError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ErrorCode.IMAGE_PROCESSING, details)

class ThumbnailGenerationError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ErrorCode.THUMBNAIL_GENERATION, details)


def log_managed_error(exc: Exception):
    """
    Logs exceptions. If it is an AppException, logs a single structured line
    and suppresses the traceback output (unless logger level is set to DEBUG).
    For unmanaged exceptions, prints the traceback at ERROR level.
    """
    if isinstance(exc, AppException):
        details_str = f" | Details: {exc.details}" if exc.details else ""
        logger.error(
            f"[MANAGED_ERROR] Code: {exc.error_code.value} | Message: {exc.message}{details_str}"
        )
        # Traceback is only logged at DEBUG level for managed errors
        logger.debug("Traceback for managed error:", exc_info=True)
    else:
        logger.error(
            f"[UNMANAGED_ERROR] Code: {ErrorCode.UNKNOWN.value} | Message: {exc}",
            exc_info=True
        )


def handle_cv_errors(fallback_factory=None):
    """
    Decorator to wrap OpenCV/NumPy/Base64 image processing logic.
    Catches all exceptions, maps standard ValueError/OpenCV exceptions
    to ImageDecodingError or ImageProcessingError, logs them using log_managed_error,
    and returns a fallback (if provided) or raises the wrapped AppException.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # If already a managed AppException, just log and raise
                if isinstance(e, AppException):
                    log_managed_error(e)
                    raise e
                
                # Check positional arguments for base64 inputs to include in details
                context_info = {}
                for i, arg in enumerate(args):
                    if isinstance(arg, str):
                        context_info[f"arg_{i}"] = {
                            "length": len(arg),
                            "prefix": arg[:30] + "..." if len(arg) > 30 else arg
                        }
                for k, v in kwargs.items():
                    if isinstance(v, str):
                        context_info[f"kwarg_{k}"] = {
                            "length": len(v),
                            "prefix": v[:30] + "..." if len(v) > 30 else v
                        }
                
                # Determine concrete exception class
                error_msg = str(e)
                if "decode" in error_msg.lower() or "bgr buffer" in error_msg.lower():
                    wrapped_exc = ImageDecodingError(
                        message=f"Failed to decode image in '{func.__name__}': {error_msg}",
                        details=context_info
                    )
                elif func.__name__ == "generate_thumbnail":
                    wrapped_exc = ThumbnailGenerationError(
                        message=f"Failed to generate thumbnail in '{func.__name__}': {error_msg}",
                        details=context_info
                    )
                else:
                    wrapped_exc = ImageProcessingError(
                        message=f"Failed to process image in '{func.__name__}': {error_msg}",
                        details=context_info
                    )
                
                # Log using our custom managed error handler (suppresses standard stdout traceback)
                log_managed_error(wrapped_exc)
                
                if fallback_factory:
                    try:
                        logger.info(f"Invoking fallback factory for '{func.__name__}' failure.")
                        return fallback_factory()
                    except Exception as fallback_err:
                        # Log fallback factory errors as unmanaged
                        log_managed_error(fallback_err)
                
                raise wrapped_exc from e
        return wrapper
    return decorator
