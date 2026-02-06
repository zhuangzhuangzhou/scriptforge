#!/bin/bash
# 会话记录脚本 - 记录开发工作会话

TRELLIS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SESSIONS_DIR="$TRELLIS_DIR/sessions"
PROJECT_DIR="$(cd "$TRELLIS_DIR/.." && pwd)"

usage() {
    echo "用法: add-session.sh --title <title> --commit <hash1,hash2,...> [--summary <summary>]"
    echo ""
    echo "选项:"
    echo "  --title <title>          会话标题（必需）"
    echo "  --commit <hash1,hash2>   提交哈希，逗号分隔（必需）"
    echo "  --summary <summary>      简短总结（可选）"
    echo ""
    echo "也可以通过 stdin 传递详细内容（Markdown 格式）"
}

# 初始化变量
TITLE=""
COMMITS=""
SUMMARY=""
CONTENT=""

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --title)
            TITLE="$2"
            shift 2
            ;;
        --commit)
            COMMITS="$2"
            shift 2
            ;;
        --summary)
            SUMMARY="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            usage
            exit 1
            ;;
    esac
done

# 检查必需参数
if [ -z "$TITLE" ] || [ -z "$COMMITS" ]; then
    echo "错误: --title 和 --commit 是必需的"
    usage
    exit 1
fi

# 读取 stdin 内容
if [ ! -t 0 ]; then
    CONTENT=$(cat)
fi

# 确保 sessions 目录存在
mkdir -p "$SESSIONS_DIR"

# 查找当前 journal 文件
JOURNAL_FILE="$SESSIONS_DIR/journal-1.md"
JOURNAL_NUM=1

# 查找最新的 journal 文件
for file in "$SESSIONS_DIR"/journal-*.md; do
    if [ -f "$file" ]; then
        num=$(basename "$file" | sed 's/journal-\([0-9]*\)\.md/\1/')
        if [ "$num" -gt "$JOURNAL_NUM" ]; then
            JOURNAL_NUM=$num
            JOURNAL_FILE="$file"
        fi
    fi
done

# 如果文件不存在，创建初始文件
if [ ! -f "$JOURNAL_FILE" ]; then
    cat > "$JOURNAL_FILE" <<EOF
# 开发会话日志 - Journal $JOURNAL_NUM

记录项目的开发会话历史。

---

EOF
fi

# 检查文件行数，如果超过 2000 行则创建新文件
if [ -f "$JOURNAL_FILE" ]; then
    LINE_COUNT=$(wc -l < "$JOURNAL_FILE")
    if [ "$LINE_COUNT" -gt 2000 ]; then
        JOURNAL_NUM=$((JOURNAL_NUM + 1))
        JOURNAL_FILE="$SESSIONS_DIR/journal-$JOURNAL_NUM.md"
        cat > "$JOURNAL_FILE" <<EOF
# 开发会话日志 - Journal $JOURNAL_NUM

记录项目的开发会话历史。

---

EOF
    fi
fi

# 生成会话记录
SESSION_DATE=$(date "+%Y-%m-%d %H:%M:%S")
SESSION_ID=$(date "+%Y%m%d-%H%M%S")

# 转换提交哈希为数组
IFS=',' read -ra COMMIT_ARRAY <<< "$COMMITS"

# 获取提交详情
cd "$PROJECT_DIR"
COMMIT_DETAILS=""
for commit_hash in "${COMMIT_ARRAY[@]}"; do
    commit_hash=$(echo "$commit_hash" | xargs) # 去除空格
    commit_msg=$(git log -1 --format="%s" "$commit_hash" 2>/dev/null)
    if [ -n "$commit_msg" ]; then
        COMMIT_DETAILS="${COMMIT_DETAILS}- \`${commit_hash}\` - ${commit_msg}\n"
    fi
done

# 构建会话条目
{
    echo ""
    echo "## [$SESSION_ID] $TITLE"
    echo ""
    echo "**时间**: $SESSION_DATE"
    echo ""
    echo "**提交**:"
    echo -e "$COMMIT_DETAILS"

    if [ -n "$SUMMARY" ]; then
        echo ""
        echo "**摘要**: $SUMMARY"
    fi

    if [ -n "$CONTENT" ]; then
        echo ""
        echo "$CONTENT"
    fi

    echo ""
    echo "---"
    echo ""
} >> "$JOURNAL_FILE"

# 更新索引文件
INDEX_FILE="$SESSIONS_DIR/index.md"
TOTAL_SESSIONS=0

# 统计总会话数
for file in "$SESSIONS_DIR"/journal-*.md; do
    if [ -f "$file" ]; then
        count=$(grep -c "^## \[" "$file" 2>/dev/null || echo 0)
        TOTAL_SESSIONS=$((TOTAL_SESSIONS + count))
    fi
done

# 创建或更新索引
cat > "$INDEX_FILE" <<EOF
# 会话记录索引

## 统计信息

- **总会话数**: $TOTAL_SESSIONS
- **最后更新**: $SESSION_DATE
- **当前 Journal**: journal-$JOURNAL_NUM.md

## Journal 文件列表

EOF

# 列出所有 journal 文件及其行数
for file in "$SESSIONS_DIR"/journal-*.md; do
    if [ -f "$file" ]; then
        basename=$(basename "$file")
        lines=$(wc -l < "$file")
        sessions=$(grep -c "^## \[" "$file" 2>/dev/null || echo 0)
        echo "- [\`$basename\`](./$basename) - $sessions 个会话, $lines 行" >> "$INDEX_FILE"
    fi
done

echo "" >> "$INDEX_FILE"
echo "---" >> "$INDEX_FILE"
echo "" >> "$INDEX_FILE"
echo "最近更新: $SESSION_DATE" >> "$INDEX_FILE"

echo "✅ 会话已记录到: $JOURNAL_FILE"
echo "📊 总会话数: $TOTAL_SESSIONS"
echo "📁 索引文件: $INDEX_FILE"
