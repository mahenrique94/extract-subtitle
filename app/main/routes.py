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
    if form.validate_on_submit():
        try:
            logger.info(f"Processing file upload: {form.file.data.filename}")
            # Initialize subtitle extractor
            extractor = SubtitleExtractor(current_app.config['UPLOAD_FOLDER'])
            
            # Save the uploaded file
            filename, file_path = extractor.save_file(form.file.data)
            logger.info(f"File saved successfully: {filename}")
            
            # Create extraction record
            extraction = SubtitleExtraction(
                user_id=current_user.id,
                original_filename=filename,
                srt_filename='',  # Will be set after processing
                target_language=form.language.data,
                status='pending'
            )
            db.session.add(extraction)
            db.session.commit()
            logger.info(f"Created extraction record with ID: {extraction.id}")
            
            # Start processing in background
            def process_in_background():
                # Create a new application context for the background thread
                app = create_app()
                with app.app_context():
                    try:
                        logger.info(f"Starting background processing for extraction {extraction.id}")
                        extractor.process_extraction(extraction.id)
                        logger.info(f"Background processing completed for extraction {extraction.id}")
                    except Exception as e:
                        logger.error(f"Error in background processing: {str(e)}")
                        extraction.status = 'failed'
                        extraction.error_message = str(e)
                        db.session.commit()
            
            thread = threading.Thread(target=process_in_background)
            thread.daemon = True  # Make thread daemon so it exits when main thread exits
            thread.start()
            logger.info(f"Background thread started for extraction {extraction.id}")
            
            flash(_('Your file is being processed. You will be notified when it\'s ready.'))
            return redirect(url_for('main.dashboard'))
            
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            flash(_('An error occurred while processing your file.'))
            return redirect(url_for('main.dashboard'))
    
    # Get user's extractions
    extractions = SubtitleExtraction.query.filter_by(user_id=current_user.id).order_by(SubtitleExtraction.created_at.desc()).all()
    logger.debug(f"Found {len(extractions)} extractions for user {current_user.id}")
    
    return render_template('main/dashboard.html', 
                         title='Dashboard',
                         form=form,
                         extractions=extractions)

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
            'progress': e.progress
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
            # Convert pt-BR to pt_BR format
            if language == 'pt-BR':
                language = 'pt_BR'
            session['language'] = language
            logger.debug(f"Language set to: {language}")
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': _('No language specified')}), 400
    except Exception as e:
        logger.error(f"Error setting language: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500 