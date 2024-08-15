#!/bin/sh

COVERAGE_REPORT_DIR="${COVERAGE_REPORT_DIR:-htmlcov}"
FAIL_FAST="${FAIL_FAST:-true}"

if [ "${FAIL_FAST}" = "true" ]; then
    python -m coverage run --branch -m unittest discover --failfast
else 
    python -m coverage run --branch -m unittest discover
fi
test_result=$?

python -m coverage html --skip-empty -d "${COVERAGE_REPORT_DIR}"

exit "${test_result}"
