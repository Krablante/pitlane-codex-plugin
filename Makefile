PYTHON ?= python3

.PHONY: test

test:
	$(PYTHON) tests/test_pitlane_codex_hook.py
