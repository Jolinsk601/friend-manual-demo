"""
V1.5: 配置管理（环境变量 + 默认值）

设计原则：
- 所有可调配置都走环境变量，提供合理默认值
- 敏感信息（API Key）必须用环境变量，不入代码库
- Mock 模式下所有限流失效，避免本地调试时被限制
"""

import os

# V1.5: 加载 .env 文件（如果装了 python-dotenv）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 没装也能跑，只是不读 .env


# ============================================================
# AI 模式：mock / deepseek
# ============================================================
# V1.5: 通过环境变量切换，默认 mock（公网部署时改为 deepseek）
AI_MODE = os.environ.get("AI_MODE", "mock").lower()

# DeepSeek API 配置（V1.5 接入时用）
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


# ============================================================
# V1.5: 限流配置（防公网部署后 API 费用失控）
# ============================================================
# 三个能力的每日调用上限（按 IP + 端点统计）
# 改这里就行，无需改代码
DAILY_SUMMARY_LIMIT = int(os.environ.get("DAILY_SUMMARY_LIMIT", "10"))  # 生成说明书
DAILY_MATCH_LIMIT = int(os.environ.get("DAILY_MATCH_LIMIT", "10"))       # 召唤契合的人
DAILY_CHAT_LIMIT = int(os.environ.get("DAILY_CHAT_LIMIT", "10"))         # AI 聊天能力（V2 预留）

# 是否启用限流：仅 deepseek 模式启用，mock 模式放行
ENABLE_RATE_LIMIT = AI_MODE == "deepseek"

# 限流超限的友好提示文案
RATE_LIMIT_MESSAGE = "今天的探索次数已经用完啦，明天再来看看新的连接吧✨"


# ============================================================
# 端口等运行配置
# ============================================================
PORT = int(os.environ.get("PORT", "5001"))


def get_mode() -> str:
    """返回当前 AI 模式，供前端展示"""
    return AI_MODE
