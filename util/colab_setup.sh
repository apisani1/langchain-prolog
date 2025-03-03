# Install SWI-Prolog
sudo apt-add-repository ppa:swi-prolog/stable
sudo apt-get update
sudo apt-get install -y swi-prolog

# Set up SWI-Prolog environment
SWIPL_HOME=$(swipl -g "current_prolog_flag(home, Home), writeln(Home)" -t halt)
echo "SWI_HOME_DIR=$SWIPL_HOME" >> $GITHUB_ENV
ARCH=$(uname -m)
echo "LD_LIBRARY_PATH=$SWIPL_HOME/lib/$ARCH-linux:$LD_LIBRARY_PATH" >> $GITHUB_ENV

# Install packages
pip install "langchain>=0.3.0"
pip install "pydantic>=2.0.0"
pip install "janus-swi>=1.5.0"
pip install langchain-prolog

# Set up Python environment
SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")
export PYTHONPATH="${SITE_PACKAGES}:${PYTHONPATH:-}"

# Test import and version
python -c "import langchain_prolog; print(f'Installed version: {langchain_prolog.__version__}')"
