# -*- coding: utf-8 -*-
"""User models."""
import datetime as dt

from ba_web_app.database import Column, PkModel, db


class AiExperiment(PkModel):
    """An experiment from a user."""

    __tablename__ = "ai_experiments"
    id = Column(db.Integer, primary_key=True)
    group_id = Column(db.String(256), nullable=True)
    name = Column(db.String(256), nullable=True)
    assistant = Column(db.Text, nullable=False)
    prompt = Column(db.Text, nullable=False)
    functions = Column(db.Text, nullable=False)
    created_at = Column(
        db.DateTime, nullable=False, default=dt.datetime.now(dt.timezone.utc)
    )

    file_uploads = db.relationship(
        "AiFileUpload", back_populates="ai_experiment", cascade="all, delete-orphan"
    )

    gene_experiment_result = db.relationship(
        "AiGeneExperimentResult", back_populates="ai_experiment", uselist=False, cascade="all, delete-orphan"
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


class AiGeneExperimentResult(PkModel):
    """Results of a gene experiment."""

    __tablename__ = "ai_gene_experiment_results"
    id = Column(db.Integer, primary_key=True)
    ai_experiment_id = Column(db.Integer, db.ForeignKey("ai_experiments.id"), nullable=False)
    publication_name = Column(db.String(256), nullable=True)
    responses = Column(db.Text, nullable=True)
    responses_csv = Column(db.Text, nullable=True)
    true_positives = Column(db.Text, nullable=True)
    created_at = Column(
        db.DateTime, nullable=False, default=dt.datetime.now(dt.timezone.utc)
    )

    ai_experiment = db.relationship("AiExperiment", back_populates="gene_experiment_result")

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<AiGeneExperimentResult({self.id!r}, {self.ai_experiment_id!r})>"

class AiGeneAlias(PkModel):
    """An alias for a gene."""

    __tablename__ = "ai_gene_aliases"
    id = Column(db.Integer, primary_key=True)
    gene = Column(db.String(256), nullable=False)
    alias = Column(db.String(256), nullable=False)
    created_at = Column(
        db.DateTime, nullable=False, default=dt.datetime.now(dt.timezone.utc)
    )

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<AiGeneAlias({self.id!r}, {self.gene_id!r})>"