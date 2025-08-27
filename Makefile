.PHONY: fast lf all-fast serial long fast-test precommit-test

fast:
	pytest --testmon -q -n auto

fast-test: fast

lf:
	pytest --lf -q -n auto

all-fast:
	pytest -q -n auto --dist=loadgroup -m "not slow and not worldgen and not combat and not serial"

precommit-test: all-fast

serial:
	pytest -q -n 1 -m serial

long:
	pytest -q -n auto -m "slow or worldgen or combat"
