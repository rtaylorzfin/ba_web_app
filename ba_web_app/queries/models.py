# -*- coding: utf-8 -*-
"""User models."""
import datetime as dt

from ba_web_app.database import Column, PkModel, db


class Query(PkModel):
    """A query from a user."""

    __tablename__ = "queries"
    id = Column(db.Integer, primary_key=True)
    assistant = Column(db.Text, nullable=False)
    prompt = Column(db.Text, nullable=False)
    functions = Column(db.Text, nullable=False)
    created_at = Column(
        db.DateTime, nullable=False, default=dt.datetime.now(dt.timezone.utc)
    )

    file_uploads = db.relationship(
        "FileUpload", back_populates="query", cascade="all, delete-orphan"
    )

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<Query({self.id!r})>"


class FileUpload(PkModel):
    """A file uploaded by a user."""

    __tablename__ = "file_uploads"
    id = Column(db.Integer, primary_key=True)

    filename = Column(db.String(256), nullable=False)
    filepath = Column(db.Text, nullable=False)
    file_type = Column(db.String(50), nullable=False)  # Example: 'pdf', 'docx', etc.
    query_id = Column(db.Integer, db.ForeignKey("queries.id"), nullable=False)

    # Relationship to the Query model
    query = db.relationship("Query", back_populates="file_uploads")

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<FileUpload({self.filename!r}, {self.query_id!r})>"
