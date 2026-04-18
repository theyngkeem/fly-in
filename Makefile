install:
	pip install -r requirements.txt
run:
	python main.py <map_file>
debug:
	python -m pdb main.py <map_file>
clean:
	remove __pycache__, .mypy_cache
lint:
    flake8 . && mypy . --warn-return-any --warn-unused-ignores \
    --ignore-missing-imports --disallow-untyped-defs \
    --check-untyped-def