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

logger = logging.getLogger(__name__)

# Get the blueprint instance
from app.main import main

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
    
    # Prepare language options for the template
    language_options = [
        {'value': code, 'label': _(info['display_name']), 'flag': info['flag']}
        for code, info in SUPPORTED_LANGUAGES.items()
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
                target_language=form.target_language.data,
                status='pending'
            )
            db.session.add(extraction)
            db.session.commit()
            extraction_id = extraction.id
            
            # Save the uploaded file
            filename, file_path = extractor.save_file(form.file.data, extraction_id)
            logger.info(f"File saved successfully: {filename}")
            
            # Update extraction record with filename
            extraction.original_filename = filename
            db.session.commit()
            
            # Start processing in background
            def process_extraction():
                try:
                    with create_app().app_context():
                        # Get the extraction record
                        extraction = SubtitleExtraction.query.get(extraction_id)
                        if not extraction:
                            logger.error(f"Extraction record not found: {extraction_id}")
                            return
                        
                        # Update status to processing
                        extraction.status = 'processing'
                        db.session.commit()
                        
                        # Convert language code for Whisper (e.g., pt_BR -> pt)
                        whisper_language = extraction.target_language.split('_')[0].lower()
                        
                        # Extract subtitles
                        srt_filename = extractor.extract_subtitles(file_path, whisper_language, extraction_id)
                        
                        # Update extraction record
                        extraction.srt_filename = srt_filename
                        extraction.status = 'completed'
                        db.session.commit()
                        
                        logger.info(f"Extraction completed successfully: {extraction_id}")
                except Exception as e:
                    logger.error(f"Error processing extraction {extraction_id}: {str(e)}")
                    try:
                        with create_app().app_context():
                            extraction = SubtitleExtraction.query.get(extraction_id)
                            if extraction:
                                extraction.status = 'failed'
                                extraction.error_message = str(e)
                                db.session.commit()
                    except Exception as inner_e:
                        logger.error(f"Error updating failed status: {str(inner_e)}")
            
            # Start background processing
            thread = threading.Thread(target=process_extraction)
            thread.start()
            
            flash(_('Your file is being processed. You will be notified when it\'s ready.'), 'info')
            return redirect(url_for('main.dashboard'))
            
        except Exception as e:
            logger.error(f"Error processing upload: {str(e)}")
            flash(_('An error occurred while processing your file.'), 'error')
            return redirect(url_for('main.dashboard'))
    
    # Get user's extractions
    extractions = SubtitleExtraction.query.filter_by(user_id=current_user.id).order_by(SubtitleExtraction.created_at.desc()).all()
    
    return render_template('main/dashboard.html', 
                         title=_('Dashboard'),
                         form=form,
                         extractions=extractions,
                         language_options=language_options)

@main.route('/download/<filename>')
@login_required
def download_file(filename):
    logger.debug(f'Accessing download route for file: {filename}')
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@main.route('/preview/<filename>')
@login_required
def preview_file(filename):
    logger.debug(f'Accessing preview route for file: {filename}')
    try:
        # Verify the file belongs to the current user
        extraction = SubtitleExtraction.query.filter_by(
            user_id=current_user.id,
            srt_filename=filename
        ).first_or_404()
        
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        logger.error(f"Error previewing file: {str(e)}")
        return "Error loading file preview", 500

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