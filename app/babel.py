from flask import request, session, g
from flask_babel import Babel
from app.config.languages import SUPPORTED_LANGUAGES
import logging

logger = logging.getLogger(__name__)

babel = Babel()

def get_locale():
    # First check if user has manually selected a language
    if 'language' in session:
        # Convert from pt-BR to pt_BR for Babel
        lang = session['language'].replace('-', '_')
        if lang in SUPPORTED_LANGUAGES:
            logger.debug(f"Using language from session: {lang}")
            return lang
    
    # If no manual selection, use browser's preferred language
    supported_codes = list(SUPPORTED_LANGUAGES.keys())
    browser_lang = request.accept_languages.best_match(supported_codes, 'en')
    if browser_lang:
        logger.debug(f"Using browser language: {browser_lang}")
        return browser_lang
    
    logger.debug("Using default language: en")
    return 'en'

def configure_babel(app):
    babel.init_app(app, locale_selector=get_locale)
    
    @app.before_request
    def before_request():
        g.lang_code = get_locale()
        logger.debug(f"Setting lang_code to: {g.lang_code}")
    
    return babel 