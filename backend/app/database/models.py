from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from app.database.session import Base
import datetime

class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(String, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    raw_image_base64 = Column(Text, nullable=False)
    thumbnail_base64 = Column(Text, nullable=False)  # 120x90 thumbnail for preview tooltips
    intensity_average = Column(Float, nullable=False)
    focus_score = Column(Float, nullable=False)
    classification_label = Column(String, nullable=False)
    histogram_json = Column(Text, nullable=False)  # JSON-serialized array of 256 integers

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(String, index=True, nullable=False)
    status = Column(String, default="pending")  # 'pending', 'processing', 'completed', 'failed'
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class ProcessingResult(Base):
    __tablename__ = "processing_results"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(String, index=True, nullable=False)
    process_type = Column(String, nullable=False)  # 'canny', 'otsu'
    processed_image_base64 = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
