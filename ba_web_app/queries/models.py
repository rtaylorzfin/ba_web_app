# -*- coding: utf-8 -*-
"""User models."""
import datetime as dt

from ba_web_app.database import Column, PkModel, db


class Query(PkModel):
    """A user of the app."""

    __tablename__ = "queries"
    id = Column(db.Integer, primary_key=True)

    # long text field:
    assistant = Column(db.Text, nullable=False)
    prompt = Column(db.Text, nullable=False)
    functions = Column(db.Text, nullable=False)
    created_at = Column(
        db.DateTime, nullable=False, default=dt.datetime.now(dt.timezone.utc)
    )

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<Query({self.id!r})>"
