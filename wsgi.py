from app import create_app
import logging
from flask import request

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = create_app()

@app.before_request
def log_request_info():
    logger.debug('Headers: %s', request.headers)
    logger.debug('Body: %s', request.get_data())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True) 