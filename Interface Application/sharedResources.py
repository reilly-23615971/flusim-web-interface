# Flusim Web Interface Application
# Developed by Reilly Evans
# Constants and other saved variables used by the web application interface
from queue import Queue
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio
from aiohttp import ClientSession
from streamlit.runtime import get_instance
from streamlit.runtime.scriptrunner import get_script_run_ctx


# Constants
# change URL to Azure SWA URL
serverUrl = 'http://127.0.0.1:8000'
threadExecutor = ThreadPoolExecutor(max_workers = 1)
resultQueue = Queue()
httpSession: ClientSession | None = None



# Teardown function to close resources when app shuts down
def closeSessions():
    global threadExecutor, httpSession
    # Close ClientSession if open
    if httpSession is not None and not httpSession.closed:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(httpSession.close())
            loop.close()
        except Exception as e:
            logging.error('Error closing client session:', e)

    # Shut down ThreadPoolExecutor
    try:
        threadExecutor.shutdown(wait = False, cancel_futures = True)
    except Exception as e:
        logging.error('Error shutting down HTTP thread executor:', e)

# Function to monitor the session and close resources when it ends
def monitorSession():
    # Inner function to identify when the session ends
    def watch():
        userSession = get_instance()
        userContext = get_script_run_ctx()
        if userContext is None:
            logging.info('No script context found; session invalid.')
            return
        sessionId = userContext.session_id

        logging.info(f'Session {sessionId} is now being monitored.')
        while userSession.is_active_session(sessionId): 
            asyncio.run(asyncio.sleep(3))
        logging.info(f'Session {sessionId} has ended. Closing resources now.')
        closeSessions()

    thread = threading.Thread(target=watch, daemon=True)
    thread.start()