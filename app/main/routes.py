from flask import Blueprint, render_template, request, send_from_directory, current_app, flash, redirect, url_for, jsonify, session
from flask_login import login_required, current_user
import os
import logging
from app.main.forms import UploadForm
from app.models import SubtitleExtraction
from app.services.subtitle_extractor import SubtitleExtractor
from app import db
import threading
from app import create_app
from flask_babel import _
from app.config.languages import SUPPORTED_LANGUAGES
from datetime import datetime
from werkzeug.utils import secure_filename
from threading import Thread
from app.services.translator import SubtitleTranslator

logger = logging.getLogger(__name__)

# Get the blueprint instance
from app.main import main

# Initialize translator
translator = SubtitleTranslator()

@main.route('/')
def index():
    logger.debug('Accessing index route')
    return render_template('main/index.html', title='Home', hide_nav=False)

@main.route('/test')
def test():
    logger.debug('Accessing test route')
    return 'Test route working!'

@main.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    logger.debug('Accessing dashboard route')
    form = UploadForm()
    
    # Get available languages for the dropdown
    language_options = [
        {'value': 'en', 'label': _('English')},
        {'value': 'pt', 'label': _('Portuguese')},
        {'value': 'es', 'label': _('Spanish')},
        {'value': 'fr', 'label': _('French')},
        {'value': 'de', 'label': _('German')},
        {'value': 'it', 'label': _('Italian')},
        {'value': 'ja', 'label': _('Japanese')},
        {'value': 'ko', 'label': _('Korean')},
        {'value': 'zh', 'label': _('Chinese')},
        {'value': 'ru', 'label': _('Russian')}
    ]
    
    if form.validate_on_submit():
        try:
            logger.info(f"Processing file upload: {form.file.data.filename}")
            
            # Initialize subtitle extractor
            extractor = SubtitleExtractor(current_app.config['UPLOAD_FOLDER'])
            
            # Create extraction record first
            extraction = SubtitleExtraction(
                user_id=current_user.id,
                original_filename='',  # Will be set after saving
                srt_filename='',  # Will be set after processing
                target_language='unknown',  # Will be updated with detected language
                status='pending'
            )
            db.session.add(extraction)
            db.session.commit()
            extraction_id = extraction.id
            
            # Save the uploaded file
            filename = secure_filename(form.file.data.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            form.file.data.save(file_path)
            
            # Update extraction record with filename
            extraction.original_filename = filename
            db.session.commit()
            
            # Start processing in background
            def process_extraction():
                app = create_app()
                with app.app_context():
                    try:
                        # Get the extraction record
                        extraction = SubtitleExtraction.query.get(extraction_id)
                        if not extraction:
                            logger.error(f"Extraction record not found: {extraction_id}")
                            return
                        
                        # Update status to processing
                        extraction.status = 'processing'
                        extraction.progress = 0
                        db.session.commit()
                        
                        # Extract subtitles using original audio language
                        srt_filename, detected_language = extractor.extract_subtitles(file_path, extraction_id)
                        
                        # Update extraction record
                        extraction.srt_filename = srt_filename
                        extraction.target_language = detected_language  # Store the detected language
                        extraction.status = 'completed'
                        extraction.progress = 100
                        extraction.completed_at = datetime.utcnow()
                        db.session.commit()
                        
                        logger.info(f"Extraction completed successfully: {extraction_id}")
                    except Exception as e:
                        logger.error(f"Error processing extraction {extraction_id}: {str(e)}")
                        try:
                            extraction = SubtitleExtraction.query.get(extraction_id)
                            if extraction:
                                extraction.status = 'failed'
                                extraction.error_message = str(e)
                                db.session.commit()
                        except Exception as inner_e:
                            logger.error(f"Error updating failed status: {str(inner_e)}")
            
            # Start background processing
            thread = Thread(target=process_extraction)
            thread.daemon = True
            thread.start()
            
            flash(_('File uploaded successfully. Extraction started.'), 'success')
            return redirect(url_for('main.dashboard'))
            
        except Exception as e:
            logger.error(f"Error in upload route: {str(e)}")
            flash(_('An error occurred while processing your file.'), 'error')
            return redirect(url_for('main.dashboard'))
    
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", 'error')
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get user's extractions with pagination
    pagination = SubtitleExtraction.query.filter_by(user_id=current_user.id)\
        .order_by(SubtitleExtraction.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    extractions = pagination.items
    
    return render_template('main/dashboard.html', 
                         title=_('Dashboard'),
                         form=form,
                         extractions=extractions,
                         language_options=language_options,
                         current_language=session.get('language', 'en'),
                         page=page,
                         per_page=per_page,
                         total_pages=pagination.pages)

@main.route('/download/<filename>')
@login_required
def download_file(filename):
    """Download SRT file."""
    try:
        # Verify file ownership
        extraction = SubtitleExtraction.query.filter_by(
            user_id=current_user.id,
            srt_filename=filename
        ).first_or_404()
        
        # Get language from query parameter, default to original language
        language = request.args.get('language', extraction.target_language)
        
        # Get the base filename without language suffix
        base_filename = filename.replace('_' + extraction.target_language + '.srt', '.srt')
        
        # Construct the language-specific filename
        lang_filename = base_filename.replace('.srt', f'_{language}.srt')
        lang_path = os.path.join(current_app.config['UPLOAD_FOLDER'], lang_filename)
        
        # If the language-specific file doesn't exist, return 404
        if not os.path.exists(lang_path):
            return "File not found", 404
            
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], lang_filename, as_attachment=True)
    except Exception as e:
        current_app.logger.error(f"Error downloading SRT file: {str(e)}")
        return str(e), 500

@main.route('/preview/<filename>')
@login_required
def preview_srt(filename):
    """Preview SRT file content."""
    try:
        # Verify file ownership
        extraction = SubtitleExtraction.query.filter_by(
            user_id=current_user.id,
            srt_filename=filename
        ).first_or_404()
        
        # Read the original SRT content
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({
                'error': _('File not found'),
                'status': 'error'
            }), 404
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return jsonify({
            'content': content,
            'detected_language': extraction.target_language,
            'status': 'success'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error previewing SRT file: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@main.route('/extraction-progress')
@login_required
def extraction_progress():
    logger.debug('Accessing extraction progress route')
    try:
        # Get all processing extractions for the current user
        extractions = SubtitleExtraction.query.filter_by(
            user_id=current_user.id,
            status='processing'
        ).all()
        
        # Return progress data
        progress_data = [{
            'id': e.id,
            'progress': e.progress,
            'status': e.status,
            'error_message': e.error_message
        } for e in extractions]
        
        return jsonify(progress_data)
    except Exception as e:
        logger.error(f"Error getting extraction progress: {str(e)}")
        return jsonify([])

@main.route('/set-language', methods=['POST'])
def set_language():
    try:
        data = request.get_json()
        if data and 'language' in data:
            language = data['language']
            # Convert pt-BR to pt_BR format but preserve case
            if language.lower() == 'pt-br':
                language = 'pt_BR'
            session['language'] = language
            logger.debug(f"Language set to: {language}")
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': _('No language specified')}), 400
    except Exception as e:
        logger.error(f"Error setting language: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@main.route('/save-srt', methods=['POST'])
@login_required
def save_srt():
    logger.debug('Accessing save SRT route')
    try:
        data = request.get_json()
        if not data or 'filename' not in data or 'content' not in data:
            return jsonify({'success': False, 'message': _('Missing required data')}), 400

        filename = data['filename']
        content = data['content']

        # Verify the file belongs to the current user
        extraction = SubtitleExtraction.query.filter_by(
            user_id=current_user.id,
            srt_filename=filename
        ).first_or_404()

        # Save the content to the file
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"SRT file updated successfully: {filename}")
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error saving SRT file: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500 