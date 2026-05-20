check-python:
	@python3 -c "import sys; assert sys.version_info >= (3, 10), 'Python 3.10+ required'"

install: check-python
	pip install -r requirements.txt

run: check-python
	python3 pedri.py mapfile.txt

debug: check-python
	python3 -m pdb pedri.py

clean:
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type d -name .mypy_cache -exec rm -rf {} +
	@find . -name "*.pyc" -delete

lint: check-python
	@flake8 .
	@mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
