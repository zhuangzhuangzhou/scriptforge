#!/bin/bash
# 任务管理脚本

TRELLIS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TASKS_DIR="$TRELLIS_DIR/tasks"

usage() {
    echo "用法: task.sh <command> [options]"
    echo ""
    echo "命令:"
    echo "  create <title> [--slug <name>]  创建新任务"
    echo "  start <task_dir>                激活任务"
    echo "  finish                          完成当前任务"
    echo "  list                            列出所有任务"
    echo "  init-context <dir> <type>       初始化上下文"
    echo "  add-context <dir> <phase> <path> <reason>  添加上下文"
}

create_task() {
    local title="$1"
    local slug=""
    shift
    while [[ $# -gt 0 ]]; do
        case $1 in
            --slug) slug="$2"; shift 2 ;;
            *) shift ;;
        esac
    done

    if [ -z "$slug" ]; then
        slug=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-')
    fi

    local date=$(date +%Y%m%d)
    local task_dir="$TASKS_DIR/${date}-${slug}"

    mkdir -p "$task_dir"

    cat > "$task_dir/task.json" << EOF
{
  "title": "$title",
  "slug": "$slug",
  "status": "created",
  "created_at": "$(date -Iseconds)"
}
EOF

    echo "$task_dir"
}

start_task() {
    local task_dir="$1"
    echo "$task_dir" > "$TRELLIS_DIR/.current-task"

    # 更新状态
    if [ -f "$task_dir/task.json" ]; then
        local tmp=$(mktemp)
        jq '.status = "in_progress"' "$task_dir/task.json" > "$tmp" && mv "$tmp" "$task_dir/task.json"
    fi

    echo "已激活任务: $task_dir"
}

finish_task() {
    if [ -f "$TRELLIS_DIR/.current-task" ]; then
        local task_dir=$(cat "$TRELLIS_DIR/.current-task")

        if [ -f "$task_dir/task.json" ]; then
            local tmp=$(mktemp)
            jq '.status = "completed"' "$task_dir/task.json" > "$tmp" && mv "$tmp" "$task_dir/task.json"
        fi

        rm "$TRELLIS_DIR/.current-task"
        echo "已完成任务: $task_dir"
    else
        echo "没有活动的任务"
    fi
}

list_tasks() {
    echo "任务列表:"
    for dir in "$TASKS_DIR"/*/; do
        if [ -f "$dir/task.json" ]; then
            local title=$(jq -r '.title' "$dir/task.json")
            local status=$(jq -r '.status' "$dir/task.json")
            echo "  - $(basename "$dir"): $title [$status]"
        fi
    done
}

init_context() {
    local task_dir="$1"
    local type="$2"

    touch "$task_dir/implement.jsonl"
    touch "$task_dir/check.jsonl"

    echo "已初始化上下文: $type"
}

add_context() {
    local task_dir="$1"
    local phase="$2"
    local path="$3"
    local reason="$4"

    local jsonl_file="$task_dir/${phase}.jsonl"
    echo "{\"path\": \"$path\", \"reason\": \"$reason\"}" >> "$jsonl_file"

    echo "已添加上下文: $path -> $phase.jsonl"
}

case "$1" in
    create) shift; create_task "$@" ;;
    start) start_task "$2" ;;
    finish) finish_task ;;
    list) list_tasks ;;
    init-context) init_context "$2" "$3" ;;
    add-context) add_context "$2" "$3" "$4" "$5" ;;
    *) usage ;;
esac
