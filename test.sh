#!/bin/bash
# shellcheck disable=SC2312,2031,2181

# Run tests and static analysis tools (gitleaks, ruff)
# Usage: ./test.sh

# Check if the script is run from the root directory
if [[ ! -f "requirements.txt" ]]; then
    echo -e "${RED}Please run this script from the root directory of the project.${NC}"
    exit 1
fi

# Setup colors for titles and errors
RED='\033[0;31m'
GREEN='\033[0;32m'
PINK='\033[38;5;225m'
NC='\033[0m' # No color

sudo apt-get install shellcheck >/dev/null

python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
pip install -r requirements.txt >/dev/null

# Initialize a failure flag
failure_flag=0

# Run bandit
echo -e "----------------------------------------${PINK}"
echo -e "Running bandit...${NC}"
bandit -c pyproject.toml -r .
if [[ $? -ne 0 ]]; then
    echo -e "${RED}Bandit check failed.${NC}"
    failure_flag=1
fi

# Run ruff
echo -e "----------------------------------------${PINK}"
echo -e "Running ruff...${NC}"
ruff check .
if [[ $? -ne 0 ]]; then
    echo -e "${RED}Ruff check failed.${NC}"
    failure_flag=1
fi

# Run yamllint
echo -e "----------------------------------------${PINK}"
echo -e "Running yamllint...${NC}"
yamllint -c yamllint.yaml .
if [[ $? -ne 0 ]]; then
    echo -e "${RED}Yamllint check failed.${NC}"
    failure_flag=1
fi

# Run shellcheck
echo -e "----------------------------------------${PINK}"
echo -e "Running shellcheck...${NC}"
while read -r file; do
    shellcheck "${file}"
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}Shellcheck failed for file: ${file}${NC}"
        failure_flag=1
    fi
done < <(find ./ -type f -name "*.sh" \
    -not -path "./node_modules/*" \
    -not -path "./.venv/*" \
    -not -path "./.git/*" \
    -not -path "./.ruff_cache/*" \
    -not -path "./.pytest_cache/*" \
    -not -path "./tests/*")

echo -e "${NC}----------------------------------------"

# Deactivate virtual environment
deactivate

# Check if any failures occurred
if [[ ${failure_flag} -ne 0 ]]; then
    echo -e "${RED}One or more checks failed.${NC}"
    exit 1
else
    echo -e "${GREEN}All checks passed successfully.${NC}"
    exit 0
fi
