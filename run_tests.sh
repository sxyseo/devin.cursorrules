#!/bin/bash

# 设置错误处理
set -e
trap 'echo "Error occurred at line $LINENO"; exit 1' ERR

# 设置环境变量
export PYTHONPATH=.
export TEST_ENV=development
export PYTHONUNBUFFERED=1

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Python版本
echo -e "${YELLOW}Checking Python version...${NC}"
python_version=$(python3 -V 2>&1 | awk '{print $2}')
required_version="3.8.0"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo -e "${GREEN}Python version $python_version is compatible${NC}"
else
    echo -e "${RED}Error: Python version $python_version is not compatible. Required version >= $required_version${NC}"
    exit 1
fi

# 检查系统资源 (Linux specific)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "${YELLOW}Checking system resources...${NC}"
    free_memory=$(free -m | awk '/^Mem:/{print $4}')
    required_memory=1024 # 1GB

    if [ "$free_memory" -lt "$required_memory" ]; then
        echo -e "${RED}Warning: Available memory ($free_memory MB) is less than recommended ($required_memory MB)${NC}"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    echo -e "${YELLOW}Skipping memory check on non-Linux system ($OSTYPE)${NC}"
fi

# 创建虚拟环境（如果不存在）
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# 激活虚拟环境
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# 检查和安装依赖
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r test_requirements.txt

# 清理之前的测试结果
echo -e "${YELLOW}Cleaning previous test results...${NC}"
rm -f test_report.html cursorrules_test_report.json tool_integration_test.log .coverage
rm -rf htmlcov/

# 运行测试
echo -e "${YELLOW}Running tests...${NC}"
python -m pytest tests/test_cursorrules.py tests/test_tool_integration.py \
    -v \
    --cov=. \
    --cov-report=html \
    --cov-report=term-missing \
    --html=test_report.html \
    --self-contained-html \
    --json-report \
    --json-report-file=cursorrules_test_report.json

# 检查测试结果
test_exit_code=$?
if [ $test_exit_code -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"

    # 显示覆盖率报告
    echo -e "${YELLOW}Coverage Report:${NC}"
    coverage report

    # 打开测试报告（如果在图形环境中）
    if [ -n "$DISPLAY" ] || [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "${YELLOW}Opening test report...${NC}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open test_report.html
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            xdg-open test_report.html
        fi
    fi
else
    echo -e "${RED}Some tests failed. Please check the test report for details.${NC}"
    echo -e "${YELLOW}Test report is available at: test_report.html${NC}"
fi

# 清理
deactivate

# 退出
exit $test_exit_code 