# flusim-web-interface
A web application designed for running and analysing simulations with the Flusim infectious disease model.

## Usage

This application uses Streamlit to construct a web interface. Run the command `streamlit run dashboardApp.py` to begin the application. Further usage instructions can be found in the User Manual [here](static/UserManual.pdf).

Note that in order to run simulations, this dashboard must be able to connect to the [Flusim Server Program](https://github.com/reilly-23615971/flusim-server-program), which itself must be integrated with the [Flusim Simulator](https://github.com/uwa-computer-science/smrg-flusim) (currently a private repository). Refer to those programs' documentation for further information.
