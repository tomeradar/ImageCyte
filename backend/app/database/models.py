from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from app.database.session import Base

class ImageRecord(Base):
    __tablename__ = "image_records"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(String, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    raw_image_base64 = Column(Text, nullable=False)
    processed_image_base64 = Column(Text, nullable=False)
    intensity_average = Column(Float, nullable=False)
    focus_score = Column(Float, nullable=False)
    classification_label = Column(String, nullable=False)
    histogram_json = Column(Text, nullable=False)  # JSON-serialized array of 256 integers
