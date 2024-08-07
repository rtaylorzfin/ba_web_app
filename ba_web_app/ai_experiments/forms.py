# -*- coding: utf-8 -*-
"""AiExperiment forms."""
from flask_wtf import FlaskForm
from wtforms import TextAreaField, StringField, BooleanField
from wtforms.validators import DataRequired, Length


class SubmitAiExperimentForm(FlaskForm):
    """Submit a biocurator assistant query form."""

    name = StringField("Name", validators=[DataRequired()])
    assistant = TextAreaField("Assistant Definition", validators=[DataRequired(), Length(min=3)])
    prompt = TextAreaField("Prompt", validators=[DataRequired(), Length(min=6)])
    functions = TextAreaField("Functions", validators=[DataRequired(), Length(min=6)])

    # Checkbox for save each file as a separate experiment
    save_files_separately = BooleanField("Save each file as a separate experiment", default=False)

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(SubmitAiExperimentForm, self).__init__(*args, **kwargs)
        self.user = None

    def validate(self, **kwargs):
        """Validate the form."""
        initial_validation = super(SubmitAiExperimentForm, self).validate()
        if not initial_validation:
            return False
        return True
