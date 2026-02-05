#!/bin/bash
# 获取当前开发上下文

TRELLIS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_DIR="$(cd "$TRELLIS_DIR/.." && pwd)"

echo "=== 开发上下文 ==="
echo ""

# Git 状态
echo "## Git 状态"
cd "$PROJECT_DIR"
echo "分支: $(git branch --show-current 2>/dev/null || echo 'N/A')"
echo "修改文件:"
git status --short 2>/dev/null | head -10
echo ""

# 当前任务
echo "## 当前任务"
if [ -f "$TRELLIS_DIR/.current-task" ]; then
    TASK_DIR=$(cat "$TRELLIS_DIR/.current-task")
    if [ -f "$TASK_DIR/task.json" ]; then
        echo "任务目录: $TASK_DIR"
        jq '.' "$TASK_DIR/task.json"
    fi
else
    echo "无活动任务"
fi
echo ""

# 活动任务列表
echo "## 任务列表"
for dir in "$TRELLIS_DIR/tasks"/*/; do
    if [ -f "$dir/task.json" ]; then
        status=$(jq -r '.status' "$dir/task.json")
        if [ "$status" != "completed" ] && [ "$status" != "archived" ]; then
            title=$(jq -r '.title' "$dir/task.json")
            echo "  - $(basename "$dir"): $title [$status]"
        fi
    fi
done 2>/dev/null || echo "  无任务"
