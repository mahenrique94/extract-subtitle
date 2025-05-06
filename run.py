from app import create_app, socketio, db
from app.models import SubtitleExtraction
import logging

app = create_app()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'SubtitleExtraction': SubtitleExtraction}

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=8080) 