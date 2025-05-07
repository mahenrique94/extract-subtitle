from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField
from wtforms.validators import DataRequired
from flask_babel import lazy_gettext as _l
from app.config.languages import SUPPORTED_LANGUAGES

class UploadForm(FlaskForm):
    file = FileField('File', validators=[
        FileRequired(),
        FileAllowed(['mp4', 'avi', 'mkv', 'mov'], 'Only video files are allowed!')
    ])
    submit = SubmitField('Upload') 