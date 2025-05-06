from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import User
from flask_babel import lazy_gettext as _l

class LoginForm(FlaskForm):
    class Meta:
        csrf = True
    
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    remember_me = BooleanField(_l('Remember Me'))
    submit = SubmitField(_l('Sign in'))

class RegistrationForm(FlaskForm):
    class Meta:
        csrf = True
    
    first_name = StringField(_l('First Name'), validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField(_l('Last Name'), validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_l('Password'), validators=[
        DataRequired(),
        Length(min=8, message=_l('Password must be at least 8 characters long'))
    ])
    password2 = PasswordField(_l('Repeat Password'), validators=[
        DataRequired(),
        EqualTo('password', message=_l('Passwords must match'))
    ])
    submit = SubmitField(_l('Register'))

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(_l('Please use a different email address.')) 