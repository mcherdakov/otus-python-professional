# Log Analyzer


To launch script, use following command(python >=3.9):
```bash
    chmod +x log_analyzer.py 
    ./log_analyzer.py --config path/to/config
```

To run tests and style check, you need to setup pipenv and install dev dependencies:
```bash
    pipenv shell
    pipenv install --dev
    python -m unittest -v test_log_analyzer test_log_parser
    flake8 .
    mypy .
```
