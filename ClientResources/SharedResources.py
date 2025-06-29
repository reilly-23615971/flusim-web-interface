# Flusim Web Interface Application
# Developed by Reilly Evans
# Constants and other saved variables used by the web application

# Imports
from queue import Queue
import logging

# Logging
sharedLog = logging.getLogger(__name__)

# Constants
# change URL to Azure SWA URL
serverUrl = 'http://127.0.0.1:8000/'
resultQueue = Queue()
population = {'albany': 0, 'cairns': 140402, 'newcastle': 272407}