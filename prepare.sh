poetry run isort .
poetry run black .
poetry run pylint **/*.py
poetry run mypy . --explicit-package-bases