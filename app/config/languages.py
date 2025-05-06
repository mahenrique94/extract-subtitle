SUPPORTED_LANGUAGES = {
    'en': {
        'name': 'English',
        'code': 'en',
        'flag': '🇺🇸',
        'whisper_model': 'base',
        'display_name': 'English'
    },
    'pt_BR': {
        'name': 'Portuguese (Brazil)',
        'code': 'pt_BR',
        'flag': '🇧🇷',
        'whisper_model': 'base',
        'display_name': 'Português (Brasil)'
    },
    'es': {
        'name': 'Spanish',
        'code': 'es',
        'flag': '🇪🇸',
        'whisper_model': 'base',
        'display_name': 'Español'
    }
}

def get_language_name(code):
    """Get the display name for a language code."""
    return SUPPORTED_LANGUAGES.get(code, {}).get('display_name', code)

def get_language_flag(code):
    """Get the flag emoji for a language code."""
    return SUPPORTED_LANGUAGES.get(code, {}).get('flag', '🌐')

def get_whisper_model(code):
    """Get the Whisper model to use for a language code."""
    return SUPPORTED_LANGUAGES.get(code, {}).get('whisper_model', 'base') 