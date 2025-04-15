#!/bin/bash
# shellcheck disable=SC2312,2031,2181

# Run tests and static analysis tools (gitleaks, ruff)
# Usage: ./test.sh

# Check if the script is run from the root directory
if [[ ! -f "requirements.txt" ]]; then
    echo "Please run this script from the root directory of the project."
    exit 1
fi

sudo apt-get install shellcheck >/dev/null

python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
pip install -r requirements.txt >/dev/null

# Initialize a failure flag
failure_flag=0

# Run bandit
echo "----------------------------------------"
echo "Running bandit..."
bandit -c pyproject.toml -r .
if [[ $? -ne 0 ]]; then
    echo "Bandit check failed."
    failure_flag=1
fi

# Run ruff
echo "----------------------------------------"
echo "Running ruff..."
ruff check .
if [[ $? -ne 0 ]]; then
    echo "Ruff check failed."
    failure_flag=1
fi

# Run yamllint
echo "----------------------------------------"
echo "Running yamllint..."
yamllint -c yamllint.yaml .
if [[ $? -ne 0 ]]; then
    echo "Yamllint check failed."
    failure_flag=1
fi

# Run shellcheck
echo "----------------------------------------"
echo "Running shellcheck..."
while read -r file; do
    shellcheck "${file}"
    if [[ $? -ne 0 ]]; then
        echo "Shellcheck failed for file: ${file}"
        failure_flag=1
    fi
done < <(find ./ -type f -name "*.sh" \
    -not -path "./node_modules/*" \
    -not -path "./.venv/*" \
    -not -path "./.git/*" \
    -not -path "./.ruff_cache/*" \
    -not -path "./.pytest_cache/*" \
    -not -path "./tests/*")

echo "----------------------------------------"
# Check if any failures occurred
if [[ ${failure_flag} -ne 0 ]]; then
    echo "One or more checks failed."
    exit 1
else
    echo "All checks passed successfully."
    exit 0
fi

# Deactivate virtual environment
deactivate
