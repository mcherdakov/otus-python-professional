# Scoring API

To run server, use following commands(python >=3.9):
```bash
    chmod +x log_analyzer.py 
    ./log_analyzer.py
```

To run tests and style check, you need to setup pipenv and install dev dependencies:
```bash
    pipenv shell
    pipenv install --dev
    python -m unittest
    flake8 .
    mypy .
```