#!/bin/env bash


SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

pushd ${SCRIPT_DIR}/../
echo "Running autopep8 ./"
autopep8 ./
autopep8_status=$?
popd

if [[ $autopep8_status -ne 0 ]]; then
    echo "autopep8_status=$autopep8_status"
    exit 1
else
    echo "all automatic formating succeed, exit status 0"
    exit 0
fi
