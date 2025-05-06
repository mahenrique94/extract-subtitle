from flask import Blueprint
import logging

logger = logging.getLogger(__name__)

# Create the blueprint
main = Blueprint('main', __name__)

logger.debug('Main blueprint created')

# Import routes after blueprint creation to avoid circular imports
from . import routes
logger.debug('Main routes imported') 