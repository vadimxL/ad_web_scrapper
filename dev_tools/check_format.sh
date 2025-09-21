#!/bin/env bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"


pushd ${SCRIPT_DIR}/../

echo "Running ruff check --fix ./"
ruff check --fix ./
ruff_status=$?
echo "vulture ./"
vulture ./
vulture_status=$?
popd

if [[ $ruff_status -ne 0 ]] || [[ $vulture_status -ne 0 ]]; then
    echo "ruff_status=$ruff_status vulture_status=$vulture_status"
    exit 1
else
    echo "all checks passed, exit status 0"
    exit 0
fi
