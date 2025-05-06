from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User
from app.auth.forms import LoginForm, RegistrationForm
from flask_babel import _
import logging

logger = logging.getLogger(__name__)

# Get the blueprint instance
from app.auth import auth

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    logger.debug('Accessing login route')
    logger.debug(f'Request method: {request.method}')
    logger.debug(f'Form data: {request.form}')
    
    form = LoginForm()
    if request.method == 'POST':
        logger.debug('Processing POST request')
        if form.validate_on_submit():
            logger.debug('Form validated successfully')
            user = User.query.filter_by(email=form.email.data).first()
            if user is None or not user.check_password(form.password.data):
                flash(_('Invalid email or password'), 'error')
                return redirect(url_for('auth.login'))
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.dashboard')
            return redirect(next_page)
        else:
            logger.debug(f'Form validation errors: {form.errors}')
    
    return render_template('auth/login.html', title=_('Sign In'), form=form, hide_nav=True)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    logger.debug('Accessing register route')
    logger.debug(f'Request method: {request.method}')
    logger.debug(f'Form data: {request.form}')
    
    form = RegistrationForm()
    if request.method == 'POST':
        logger.debug('Processing POST request')
        if form.validate_on_submit():
            logger.debug('Form validated successfully')
            user = User(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash(_('Congratulations, you are now registered!'), 'success')
            return redirect(url_for('auth.login'))
        else:
            logger.debug(f'Form validation errors: {form.errors}')
    
    return render_template('auth/register.html', title=_('Register'), form=form, hide_nav=True)

@auth.route('/logout')
@login_required
def logout():
    logger.debug('Accessing logout route')
    logout_user()
    return redirect(url_for('main.index')) 