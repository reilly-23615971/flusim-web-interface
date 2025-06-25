# Flusim Web Interface Application
# Developed by Reilly Evans
# Constants and other saved variables used by the web application

# Imports
from queue import Queue
import logging

# Previous imports
#import threading
#from concurrent.futures import ThreadPoolExecutor
#import asyncio
#from aiohttp import ClientSession
#import streamlit as st
#from streamlit.runtime import get_instance
#from streamlit.runtime.scriptrunner import get_script_run_ctx

# Logging
sharedLog = logging.getLogger(__name__)

# Constants
# change URL to Azure SWA URL
serverUrl = 'http://127.0.0.1:8000/'
resultQueue = Queue()
population = {'albany': 0, 'cairns': 140402, 'newcastle': 272407}



# Outdated code
'''
#threadExecutor = ThreadPoolExecutor(max_workers = 1)
#httpSession: ClientSession | None = None

# Teardown function to close resources when app shuts down
def closeSessions():
    global httpSession#, threadExecutor
    # Close ClientSession if open
    if httpSession is not None and not httpSession.closed:
        try: asyncio.run(httpSession.close())
        except Exception as e:
            sharedLog.error('[closeSessions] Error closing client session:', e)

    ''#'
    # Shut down ThreadPoolExecutor
    try:
        threadExecutor.shutdown(wait = False, cancel_futures = True)
    except Exception as e:
        sharedLog.error('[closeSessions] Error shutting down HTTP thread executor:', e)
    ''#'

# Function to monitor the session and close resources when it ends
@st.cache_resource
def monitorSession():
    # Get session context
    sharedLog.info(f'[monitorSession] Initialising session monitor...')
    userSession = get_instance()
    userContext = get_script_run_ctx()
    if userContext is None or userSession is None:
        sharedLog.info('[monitorSession] No session/script context found; session invalid.')
        return
    sessionId = userContext.session_id

    # Inner function to identify when the session ends
    def watch(userSession, sessionId):
        sharedLog.info(f'[watch] Session {sessionId} is now being monitored.')
        while userSession.is_active_session(sessionId): 
            asyncio.run(asyncio.sleep(3))
        sharedLog.info(f'[watch] Session {sessionId} has ended. Closing resources now.')
        closeSessions()
        sharedLog.info(f'[watch] Session {sessionId} closed.')

    # Create thread for monitoring
    thread = threading.Thread(
        target = watch, args = (userSession, sessionId), daemon = True
        )
    thread.start()
    sharedLog.info('[monitorSession] Started monitoring thread.')
'''