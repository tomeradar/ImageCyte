import logging
import sys

def setup_logging():
    """
    Sets up a structured and rich logging configuration for the FastAPI application.
    """
    log_format = "%(asctime)s [%(levelname)s] (%(name)s) %(filename)s:%(lineno)d: %(message)s"
    
    root_logger = logging.getLogger()
    
    # Set logging level for the root logger
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        
    # Create console handler printing to sys.stdout
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)
    
    # Tune specific library logging levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    root_logger.info("Rich logging system configured successfully.")
