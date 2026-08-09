# 朋友说明书 AI · Friend Manual Demo

> AI 帮你生成"朋友说明书"，并找到可能与你产生连接的人。

一个 Python Flask 全栈 Demo，用户答 5 道题 → AI 生成毒舌风格的人格说明书 → AI 匹配同频/互补的"虚拟同类"。

![Version](https://img.shields.io/badge/version-V1.5-purple) ![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![Flask](https://img.shields.io/badge/flask-3.0%2B-green)

---

## ✨ 核心功能

### 🎭 朋友说明书生成
- **5 道场景化访谈题**（约 1 分钟）
- AI 生成**毒舌风格**的主人格 + 副标签 + 6 大参数（Token/能量/防火墙/权限/价值观/技能）
- 一句"人格名言"（朋友圈签名级传播力）

### ✨ 寻找契合的人
- AI 从 20 种虚拟人格中匹配 **3 位**最契合的人（同频型 + 互补型混合）
- **关系可能性地图**（二维坐标图：表达方式 × 关系节奏）
- 卡片左右滑动浏览
- "认识 TA" 入口（V2 聊天关系沉淀预留）

### 👀 朋友评价闭环
- 把说明书链接发给朋友，朋友能补充"人类观察"
- AI 融合原始分析 + 朋友观察，重新理解你

### 🔐 安全与限流
- DeepSeek API Key **只存在服务器环境变量**，前端零接触
- V1.5 内置限流（IP + 端点 + 日期），防止 API 费用失控
- Mock 模式免 Key，DeepSeek 模式自动启用限流

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────┐
│         用户（浏览器）                 │
└──────────────┬──────────────────────┘
               │ HTTPS
┌──────────────▼──────────────────────┐
│    Flask 应用（V1.5）                │
│    ├── 5 问访谈生成                  │
│    ├── 说明书生成（DeepSeek）        │
│    ├── 召唤契合的人（20 mock + AI）   │
│    ├── 朋友评价                      │
│    ├── AI 融合总结                    │
│    └── 限流拦截（3 个接口）            │
└──────────────┬──────────────────────┘
               │ API Key（服务端持有）
┌──────────────▼──────────────────────┐
│          DeepSeek API                │
└─────────────────────────────────────┘
```

**栈**：Python 3.9+ · Flask 3.0+ · SQLite · vanilla JS · vanilla CSS

---

## 🚀 本地运行

### 前置
- Python 3.9 或更高
- （可选）DeepSeek API Key —— 没也能跑 Mock 模式

### 启动

```bash
# 1. 装依赖
pip3 install -r requirements.txt

# 2. （可选）配置环境变量
cp .env.example .env
# 编辑 .env 填 DEEPSEEK_API_KEY

# 3. 启动
python3 app.py

# 4. 浏览器打开
open http://localhost:5001
```

### 模式说明

| 模式 | 触发方式 | Key | 限流 | 用途 |
|---|---|---|---|---|
| `mock` | `AI_MODE=mock` | 不需要 | 不启用 | 本地演示 |
| `deepseek` | `AI_MODE=deepseek` + `DEEPSEEK_API_KEY` | 需要 | 启用（10次/IP/天）| 生产环境 |

---

## 🌐 公网部署

### 推荐 Render（最简单）

| 字段 | 值 |
|---|---|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120` |

### 环境变量（在 Render Dashboard 配置）

| Key | Value | 说明 |
|---|---|---|
| `AI_MODE` | `deepseek` | 必填（生产环境） |
| `DEEPSEEK_API_KEY` | `sk-你的真实key` | **必填，勿提交 Git** |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | 默认 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 默认 |
| `DAILY_SUMMARY_LIMIT` | `10` | 每天生成说明书上限 |
| `DAILY_MATCH_LIMIT` | `10` | 每天召唤契合的人上限 |
| `DAILY_CHAT_LIMIT` | `10` | 每天 AI 聊天上限（V2） |

> `PORT` 由平台自动注入，**不要手动设置**。

### 部署步骤

1. **推到 GitHub**（见下方）
2. **Render Dashboard** → New Web Service
3. 连 GitHub 仓库，填上面 3 个字段
4. Environment 加 7 个变量（**别把 Key 写进代码**）
5. Create Web Service → 等 2-3 分钟
6. 访问 Render 给的 URL

> ⚠️ Render 免费版 SQLite 重启会丢数据。V1.5 Demo 用量小可接受；如需持久化升级到 PostgreSQL。

---

## 📁 项目结构

```
friend-manual-demo/
├── app.py                  # Flask 主程序（路由 + 业务逻辑）
├── ai_service.py           # AI 调用统一封装（mock/deepseek 自动切换）
├── config.py               # V1.5: 配置入口（限流 + 环境变量）
├── prompts.py              # Prompt 库（5 大场景）
├── db.py                   # SQLite 封装
├── mock_users.py           # 20 个虚拟人格（含 social_x/y 坐标）
├── requirements.txt
│
├── templates/              # 8 个 HTML 页面
│   ├── index.html          # 首页 + 结果页
│   ├── identity.html       # 身份卡
│   ├── manual.html         # 完整说明书
│   ├── report.html         # 报告页（带 AI 融合）
│   ├── profile.html        # 分享页（TA 的人格报告）
│   ├── reviews.html        # 朋友评价
│   ├── relationship.html   # 双人关系书
│   ├── social_map.html     # 同类地图
│   ├── icebreak.html       # AI 破冰话题
│   ├── summon.html         # 寻找契合的人
│   └── chat.html           # V2 聊天入口（占位）
│
├── static/
│   └── app.css             # 全部样式
│
├── .env.example            # 环境变量模板（提交到 Git）
├── .gitignore
├── switch_to_deepseek.sh   # 一键切真实 API 模式
├── DEPLOY_V1.5.md          # 详细部署文档
└── README.md
```

---

## 🔐 安全原则

### ✅ 怎么做
- DeepSeek API Key 存 `.env` 或部署平台环境变量
- `.env` 在 `.gitignore` 里，**绝不**进 Git
- 前端代码**永不**接触 Key（V1.8.1 已彻底移除）
- 用户请求先到我们服务器，**由我们转发**给 DeepSeek

### ❌ 不要做
- 不要把 Key 写进 HTML / JS / Python 注释
- 不要把 `.env` 加进 Git
- 不要在聊天里贴 Key
- 不要把 Key 截图发到群里

---

## 📊 V1.5 产品链路

```
[首页]                          ↓
5 道题访谈                       ↓
[结果页] → 朋友说明书              ↓
  ├ 分享（弹窗 + 随机金句）        ↓
  ├ 我的身份卡（人格 + 名言）      ↓
  └ 完整说明书（隐藏重复入口）      ↓
[寻找契合的人]                    ↓
  ├ 关系可能性地图                 ↓
  ├ 滑动卡片（同频/互补）          ↓
  └ 认识 TA → V2 聊天（占位）      ↓
```

---

## 🛠️ 调参与迭代

### 改限流次数
编辑 `.env`：
```bash
DAILY_SUMMARY_LIMIT=10   # 每人每天最多生成 10 次
DAILY_MATCH_LIMIT=10     # 每人每天最多召唤 10 次
DAILY_CHAT_LIMIT=10      # V2 聊天用
```

### 改 Prompt 毒舌程度
打开 `prompts.py`，编辑 `SYSTEM_PROMPT` 里的毒舌描述。

### 改 AI 温度
打开 `app.py`，搜 `temperature=`，调高更发散（0.9 → 1.0），调低更稳（0.7）。

---

## 📝 版本历史

| 版本 | 重点 |
|---|---|
| V0.x | 5 问访谈 + 说明书生成 |
| V1.4 | 分享闭环 |
| V1.5 | 朋友评价 |
| V1.7 | 召唤同类（20 mock + AI 匹配）|
| V1.8 | 双人关系说明书 |
| V1.9 | 同类地图 + 身份卡 |
| **V1.5opt** | **限流 / 聊天占位 / UI 优化 / 朋友圈金句 1 句化 / 紫色按钮探索更多** |

---

## 📄 许可

MIT License - 仅供学习交流

---

**重要提醒**：本项目是 Demo，所有用户数据（说明书、匹配、评价）仅作演示用途。Render 免费版实例休眠会清空磁盘，**生产使用建议升级数据库**。
