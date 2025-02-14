
#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Start the Streamlit app
streamlit run app.py --server.port=8000 --server.address=0.0.0.0
