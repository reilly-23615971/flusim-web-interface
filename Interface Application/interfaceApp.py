# Flusim Web Interface Application
# Developed by Reilly Evans

# Imports
import streamlit as st
from streamlit.logger import get_logger

# Start logger
flusimLogger = get_logger(__name__)

st.set_page_config(page_title = 'SMRG Flusim Web Dashboard', page_icon = '🦠')


pages = {
    'SMRG Flusim Web Dashboard': [
        st.Page("modelDescription.py", title="Model Description"),
        st.Page("initialChartPage.py", title="Model Results")
    ]
}

# Define model parameters to adjust
st.sidebar.slider('Beta', 0.01, 10.0, 0.11, key = 'beta')
st.sidebar.selectbox('NPI Presets', ['None', 'Low', 'Medium', 'High'], key='npi')


flusimPages = st.navigation(pages)
flusimPages.run()