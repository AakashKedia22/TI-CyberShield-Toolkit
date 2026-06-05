#!/bin/env sh

pytest -v --cov=. --cov-report=xml:output/coverage.xml
