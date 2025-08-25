.PHONY: fast-test precommit-test

fast-test:
	pytest --testmon -m "not slow"

precommit-test:
	pytest --maxfail=1 -m "not slow"
