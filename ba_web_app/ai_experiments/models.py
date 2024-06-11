# -*- coding: utf-8 -*-
"""User models."""
import datetime as dt

from ba_web_app.database import Column, PkModel, db


class AiExperiment(PkModel):
    """An experiment from a user."""

    __tablename__ = "ai_experiments"
    id = Column(db.Integer, primary_key=True)
    assistant = Column(db.Text, nullable=False)
    prompt = Column(db.Text, nullable=False)
    functions = Column(db.Text, nullable=False)
    created_at = Column(
        db.DateTime, nullable=False, default=dt.datetime.now(dt.timezone.utc)
    )

    file_uploads = db.relationship(
        "AiFileUpload", back_populates="ai_experiment", cascade="all, delete-orphan"
    )

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<AiExperiment({self.id!r})>"


class AiFileUpload(PkModel):
    """A file uploaded by a user."""

    __tablename__ = "ai_file_uploads"
    id = Column(db.Integer, primary_key=True)

    filename = Column(db.String(256), nullable=False)
    filepath = Column(db.Text, nullable=False)
    file_type = Column(db.String(50), nullable=False)  # Example: 'pdf', 'docx', etc.
    ai_experiment_id = Column(db.Integer, db.ForeignKey("ai_experiments.id"), nullable=False)

    # Relationship to the AiExperiment model
    ai_experiment = db.relationship("AiExperiment", back_populates="file_uploads")

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<AiFileUpload({self.filename!r}, {self.ai_experiment_id!r})>"
