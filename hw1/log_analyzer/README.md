# Log Analyzer


To launch script, use following command(python >=3.9):
    chmod +x log_analyzer.py 
    ./log_analyzer.py


To run tests and style check, you need to setup pipenv and install dev dependencies:
    pipenv shell
    pipenv install --dev
    python -m unittest -v test_log_analyzer test_log_parser
    flake8 .
    mypy .
