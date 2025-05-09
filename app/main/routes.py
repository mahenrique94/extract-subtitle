from flask import Blueprint, render_template, request, send_from_directory, current_app, flash, redirect, url_for, jsonify, session, get_flashed_messages
from flask_login import login_required, current_user
import os
import logging
from app.main.forms import UploadForm
from app.models import SubtitleExtraction
from app.services.subtitle_extractor import SubtitleExtractor
from app import db
import threading
from app import create_app
from flask_babel import _, format_datetime
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
    
    # Get pagination parameters with defaults
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get user's extractions with pagination
    extractions = SubtitleExtraction.query.filter_by(user_id=current_user.id)\
        .order_by(SubtitleExtraction.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
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
            
            # Get video duration and check credits
            video_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(form.file.data.filename))
            duration_seconds = extractor.get_video_duration(video_path)  # Already in seconds
            
            # Calculate required credits (1 credit per minute)
            required_credits = (duration_seconds / 60) + 1  # Round up to nearest minute
            
            # Get user's credit balance
            credit_balance = current_user.credit_balance or 0.0
            
            logger.info(f"Video duration: {duration_seconds} seconds, Required credits: {required_credits}, User balance: {credit_balance}")
            
            if credit_balance < required_credits:
                error_message = _('Insufficient credits! You have {} credits, but need {} credits for this video. Please add more credits to continue.').format(
                    credit_balance,
                    required_credits
                )
                flash(error_message, 'error')
                return jsonify({'error': error_message})
            
            # Process the file
            filename = secure_filename(form.file.data.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            form.file.data.save(file_path)
            
            # Deduct credits from user's balance
            current_user.credit_balance = credit_balance - required_credits
            db.session.commit()
            
            # Create extraction record
            extraction = SubtitleExtraction(
                user_id=current_user.id,
                original_filename=filename,
                target_language='unknown',
                status='pending'
            )
            db.session.add(extraction)
            db.session.commit()
            
            # Start background processing
            def process_file(extraction_id):
                with create_app().app_context():
                    try:
                        # Get a fresh reference to the extraction object
                        extraction = SubtitleExtraction.query.get(extraction_id)
                        extractor = SubtitleExtractor(current_app.config['UPLOAD_FOLDER'])
                        extractor.process_extraction(extraction_id)
                    except Exception as e:
                        logger.error(f"Error processing file: {str(e)}")
                        # Get a fresh reference to update the status
                        extraction = SubtitleExtraction.query.get(extraction_id)
                        extraction.status = 'failed'
                        db.session.commit()
            
            thread = Thread(target=process_file, args=(extraction.id,))
            thread.start()
            
            flash(_('File uploaded successfully. Extraction started.'), 'success')
            return jsonify({'success': True})
            
        except Exception as e:
            logger.error(f"Error processing upload: {str(e)}")
            error_message = _('Error processing video file. Please try again.')
            flash(error_message, 'error')
            return jsonify({'error': error_message})
    
    return render_template('main/dashboard.html', 
                         title=_('Dashboard'),
                         form=form,
                         language_options=language_options,
                         credit_balance=current_user.credit_balance or 0.0,
                         extractions=extractions.items,
                         page=page,
                         per_page=per_page,
                         total_pages=extractions.pages,
                         has_next=extractions.has_next,
                         has_prev=extractions.has_prev)

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

@main.route('/add-credits', methods=['GET', 'POST'])
@login_required
def add_credits():
    """Handle credit purchase page and processing."""
    if request.method == 'POST':
        try:
            # Get the amount of credits to add from the form
            amount = float(request.form.get('amount', 0))
            
            if amount <= 0:
                flash(_('Please enter a valid amount of credits.'), 'error')
                return redirect(url_for('main.add_credits'))
            
            # Update user's credit balance
            current_user.credit_balance = (current_user.credit_balance or 0.0) + amount
            db.session.commit()
            
            flash(_('Credits added successfully!'), 'success')
            return redirect(url_for('main.dashboard'))
            
        except ValueError:
            flash(_('Please enter a valid number.'), 'error')
            return redirect(url_for('main.add_credits'))
        except Exception as e:
            logger.error(f"Error adding credits: {str(e)}")
            flash(_('An error occurred while adding credits. Please try again.'), 'error')
            return redirect(url_for('main.add_credits'))
    
    return render_template('main/add_credits.html', 
                         title=_('Add Credits'),
                         credit_balance=current_user.credit_balance or 0.0) 