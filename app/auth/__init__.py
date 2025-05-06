from flask import Blueprint
import logging

logger = logging.getLogger(__name__)

# Create the blueprint
auth = Blueprint('auth', __name__)

logger.debug('Auth blueprint created')

# Import routes after blueprint creation to avoid circular imports
from . import routes
logger.debug('Auth routes imported') 