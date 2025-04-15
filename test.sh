#!/bin/bash
# shellcheck disable=SC2312
# Run tests and static analysis tools (gitleaks, ruff)
# Usage: ./test.sh

# Check if the script is run from the root directory
if [[ ! -f "requirements.txt" ]]; then
    echo "Please run this script from the root directory of the project."
    exit 1
fi

sudo apt install shellcheck >/dev/null

python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
pip install -r requirements.txt >/dev/null

# Run bandit
printf "\nRunning bandit..."
bandit -c pyproject.toml -r .

# Run ruff
printf "\nRunning ruff..."
ruff check .

# Run yamllint
printf "\nRunning yamllint..."
yamllint -c yamllint.yaml .

# Run shellcheck
printf "\nRunning shellcheck..."
find ./ -type f -name "*.sh" \
    -not -path "./node_modules/*" \
    -not -path "./.venv/*" \
    -not -path "./.git/*" \
    -not -path "./.ruff_cache/*" \
    -not -path "./.pytest_cache/*" \
    -not -path "./tests/*" | while read -r file; do
    shellcheck "${file}"
done
echo ""
echo "All checks completed"
deactivate