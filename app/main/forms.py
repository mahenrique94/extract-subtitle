from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired
from flask_babel import lazy_gettext as _l
from app.config.languages import SUPPORTED_LANGUAGES

class UploadForm(FlaskForm):
    file = FileField(_l('Media File'), validators=[
        FileRequired(),
        FileAllowed(['mp4', 'avi', 'mkv', 'mov'], _l('Only video files are allowed!'))
    ])
    language = SelectField(_l('Target Language'), validators=[DataRequired()], 
                         choices=[(code, f"{info['flag']} {info['name']}") 
                                 for code, info in SUPPORTED_LANGUAGES.items()])
    submit = SubmitField(_l('Extract Subtitles')) 