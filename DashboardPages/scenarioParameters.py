# Flusim Web Interface Application
# Developed by Reilly Evans
# Page where variables for vaccination and NPIs can be configured

# Imports
import streamlit as st



st.title('Flusim Disease Model Web Dashboard')

st.write((
    'This page allows for configuring the parameters that will be used by the simulation. To allow for direct comparison of different parameter sets, you may define multiple sets of parameters.'
))

#TODO

st.header('Testing Scale Changes')

upperBound = st.slider(
    'Upper Bound Test Slider', 1, 1000, 750, key = 'upper', help = f'''
        Slider used for testing.
    '''
)

testValue = st.slider(
    'Test Slider', 1, upperBound, key = 'test2', help = f'''
        Slider used for testing with modifiable upper bound.
    '''
)

st.markdown(f'''
    Current Slider Values:
    
    - Upper Bound Slider: {upperBound}
    - The Other One: {testValue}
''')