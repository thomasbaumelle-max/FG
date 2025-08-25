.PHONY: fast-test

fast-test:
	pytest --testmon -m "not slow"
