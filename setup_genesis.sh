# setup_genesis.sh
#!/bin/bash
# Script to set up the GENESIS environment

echo "Setting up GENESIS environment..."

# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate
echo "Virtual environment created and activated."

# 2. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
echo "Core Python dependencies installed."

# 3. Install developer dependencies for linting and testing
pip install -e .[dev]
echo "Developer dependencies installed."

# 4. Download spaCy model
echo "Downloading spaCy model en_core_web_sm..."
python -m spacy download en_core_web_sm

# 5. --- Critical: NAOqi/Pepper SDK Setup (Manual Step) ---
echo " "
echo "====================================================================="
echo "CRITICAL STEP: PEPPER NAOqi SDK"
echo " "
echo "GENESIS requires the NAOqi Python SDK bindings to run."
echo "These libraries (pynaoqi/qi) must be installed separately, usually matching"
echo "your local OS and Python version, and connecting to the Pepper Robot."
echo " "
echo "Please ensure the appropriate SDK libraries are installed in your environment."
echo "====================================================================="
echo " "

echo "Setup complete. Run 'source venv/bin/activate' and then './run_genesis.sh'."