#!/bin/bash
# V1.5: 一键切换到 DeepSeek 模式
# 用法：bash switch_to_deepseek.sh sk-你的真实key

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

KEY="$1"

if [ -z "$KEY" ]; then
    echo "❌ 用法: bash switch_to_deepseek.sh sk-你的真实key"
    echo "   或者先编辑 .env 文件再启动"
    exit 1
fi

echo "=== 1. 写入 .env ==="
cat > .env <<EOF
AI_MODE=deepseek
DEEPSEEK_API_KEY=$KEY
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
DAILY_SUMMARY_LIMIT=5
DAILY_MATCH_LIMIT=5
DAILY_CHAT_LIMIT=5
PORT=5001
EOF
chmod 600 .env
echo "✓ .env 已创建（权限 600，仅你可见）"

echo ""
echo "=== 2. 停止当前服务 ==="
lsof -ti:5001 | xargs -r kill -9 2>/dev/null || true
sleep 1

echo ""
echo "=== 3. 启动 deepseek 模式 ==="
nohup python3 app.py > /tmp/friend_manual_v15.log 2>&1 &
sleep 3

echo ""
echo "=== 4. 验证启动 ==="
if lsof -ti:5001 > /dev/null; then
    echo "✓ 服务在 5001 端口运行"
    echo ""
    echo "=== 5. 真实 API 连通性测试 ==="
    RESULT=$(curl -s -X POST http://localhost:5001/api/start-interview \
        -H "Content-Type: application/json" -d '{}' 2>&1)
    echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    if d.get('ok'):
        print(f'  ✓ DeepSeek API 调用成功')
        print(f'    生成题目数: {len(d.get(\"questions\", []))}')
        print(f'    耗时: {d.get(\"elapsed\")}s')
        print(f'    模式: {d.get(\"mode\")}')
        print(f'    限流: {d.get(\"rate_limit\")}')
    else:
        print(f'  ✗ 调用失败: {d.get(\"error\")}')
        print(f'    详情: {d.get(\"detail\")}')
        print(f'    模式: {d.get(\"mode\")}')
        if 'Key' in str(d) or 'key' in str(d):
            print('    → 请检查 .env 里的 DEEPSEEK_API_KEY 是否正确')
except Exception as e:
    print(f'  解析失败: {e}')
    print(f'  原始返回: $RESULT')
"
else
    echo "❌ 启动失败，看日志: tail -20 /tmp/friend_manual_v15.log"
fi

echo ""
echo "=== 日志前 20 行 ==="
head -20 /tmp/friend_manual_v15.log
