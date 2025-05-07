from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired
from flask_babel import lazy_gettext as _l
from app.config.languages import SUPPORTED_LANGUAGES

class UploadForm(FlaskForm):
    file = FileField(_l('Media File'), validators=[
        FileAllowed(['mp4', 'avi', 'mkv', 'mov'], _l('Only video files are allowed!'))
    ])
    target_language = HiddenField(_l('Target Language'), validators=[DataRequired()])
    submit = SubmitField(_l('Extract Subtitles')) 