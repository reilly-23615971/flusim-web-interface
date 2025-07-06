# Flusim Web Interface Application
# Developed by Reilly Evans
# Page describing the Flusim model itself (and potentially other info)

# Imports
import streamlit as st

# Create page
st.title('Flusim Disease Model Web Dashboard')

st.markdown(
    '''
    The SMRG Flusim model, developed by the Software Modelling Research Group at the University of Western Australia, implements a high-performance agent-based simulation model to simulate the spread of infectious disease in a population. This model has been used to aid in deciding effective policy for diseases such as influenza [[1](https://doi.org/10.1586/eri.10.136)] and COVID-19 [[2](https://doi.org/10.1101/2022.03.09.22272170)].

    This website allows users to easily run the model with specific parameters and visualise the results. Currently, an example graph can be viewed on the 'Model Results' page.
    '''
)