install:
	pip install -r requirements.txt

run:
	python3 pedri.py mapfile.txt

debug:
	python3 -m pdb pedri.py

clean:
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type d -name .mypy_cache -exec rm -rf {} +
	@find . -name "*.pyc" -delete

lint:
	@flake8 .
	@mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
