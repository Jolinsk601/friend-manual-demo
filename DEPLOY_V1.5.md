# 朋友说明书 AI · V1.5 上线部署文档

> AI 产品 Demo 上线部署指南。
> 目标：从 0 到 1 把本地项目部署到公网，让朋友通过链接体验。
> 所有操作都在你自己的环境完成，**不要把 API Key 发给任何人（包括 AI 助手）**。

---

## 📑 目录

- [一、整体部署路线](#一整体部署路线)
- [二、GitHub 上传准备](#二github-上传准备)
- [三、推荐部署：Render / Railway](#三推荐部署render--railway)
- [四、环境变量说明](#四环境变量说明)
- [五、限流机制](#五限流机制)
- [六、API 成本控制说明](#六api-成本控制说明)
- [七、上线前检查清单](#七上线前检查清单)
- [八、文件结构说明](#八文件结构说明)
- [九、安全自查](#九安全自查)
- [十、附录：高级部署方式（自建服务器）](#十附录高级部署方式自建服务器)

---

## 一、整体部署路线

```
┌──────────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────────┐
│  本地 Mac     │    │  GitHub  │    │ Render /     │    │  朋友访问     │
│  （开发）      │───►│ （代码）  │───►│ Railway       │───►│  HTTPS 链接  │
│              │    │          │    │ （自动部署）  │    │              │
└──────────────┘    └──────────┘    └──────────────┘    └──────────────┘
                                                  ↓
                                          自动 HTTPS
                                          环境变量配 Key
```

**总耗时**：本地准备 5 分钟 + 推送 5 分钟 + 平台部署 5 分钟 = **15 分钟内公网可访问**。

---

## 二、GitHub 上传准备

### 2.1 上传前清单

#### ✅ 必须上传
| 类型 | 文件 |
|---|---|
| Python 代码 | `app.py` · `config.py` · `prompts.py` · `db.py` · `ai_service.py` · `mock_users.py` |
| 模板 | `templates/`（12 个 HTML 文件）|
| 静态资源 | `static/app.css` |
| 依赖 | `requirements.txt` |
| 部署文档 | `README.md` · `.env.example` · `.gitignore` |

#### ❌ 禁止上传（敏感/临时文件）
| 类型 | 文件 / 目录 | 原因 |
|---|---|---|
| **环境变量** | `.env` | ⚠️ 包含真实 DeepSeek API Key |
| **数据库** | `*.db` / `*.sqlite3` | 用户数据（部署到云端会重新建）|
| **Python 缓存** | `__pycache__/` | 编译缓存，无意义 |
| **临时文件** | `*.log` / `*.tmp` / `*.bak` | 调试残留 |
| **系统文件** | `.DS_Store` | Mac 系统文件 |
| **旧文档** | `handoff-package/` | V1.x 老交付物 |

### 2.2 上传到 GitHub

```bash
# 1. 初始化
cd /Users/xueer/Desktop/friend-manual-demo
git init
git config user.name "你的GitHub用户名"
git config user.email "你的GitHub邮箱"

# 2. 暂存所有文件
git add .

# 3. ⭐ 关键检查：确认 .env 没被加入
git status
# 看输出列表里有没有 .env
# ✅ 出现 .env = 错！立即停止
# ✅ 没出现 = 对，继续

# 4. 提交
git commit -m "V1.5: 朋友说明书 AI Demo 完整版"
```

### 2.3 推送到 GitHub

```bash
# 1. 在 github.com 新建空仓库（不勾选 README/license/.gitignore）
# 2. 拿到仓库地址，例如：
#    https://github.com/你的用户名/friend-manual-demo.git

# 3. 关联并推送
git remote add origin https://github.com/你的用户名/friend-manual-demo.git
git branch -M main
git push -u origin main
```

**如果弹出登录框**：用 GitHub **Personal Access Token**（不是密码）。  
Token 在 https://github.com/settings/tokens 生成，勾选 `repo` 权限。

### 2.4 推送后必做：仓库确认

1. 打开 GitHub 仓库网页
2. **确认仓库里没有 `.env` 文件**
3. 在仓库内搜索 `DEEPSEEK_API_KEY` → **应该搜不到**

---

## 三、推荐部署：Render / Railway

### 3.1 为什么推荐 Render

| 维度 | Render | Vercel | Railway |
|---|---|---|---|
| Flask + SQLite 友好度 | ✅ 原生支持 | ⚠️ 需改造 | ✅ 原生 |
| 免费额度 | 750 小时/月 | 较多 | $5/月额度 |
| 自动 HTTPS | ✅ | ✅ | ✅ |
| GitHub 集成 | ✅ 一键 | ✅ 一键 | ✅ 一键 |
| 本项目适配 | ✅ **完美** | ❌ 不推荐 | ✅ 良好 |

**结论：用 Render**（最简单 + 适合本项目）。

### 3.2 Render 部署步骤

#### 步骤 1：连接 GitHub
1. 打开 https://dashboard.render.com
2. **New** → **Web Service**
3. 选 **Connect a repository** → 选你的 GitHub 仓库

#### 步骤 2：填写配置

| 字段 | 值 |
|---|---|
| Name | `friend-manual-demo-v15`（避免和 V1.4 重名）|
| Region | Singapore（亚洲快）或 Oregon（美西）|
| Branch | `main` |
| Runtime | Python 3 |
| Plan | Free |

#### 步骤 3：构建和启动命令

| 字段 | 值 |
|---|---|
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120` |

**参数说明**：
- `$PORT` 由 Render 自动注入，**不要手动设**
- `--workers 1` 免费版只能 1 个 worker
- `--timeout 120` 给 DeepSeek API 调用留够时间（默认 30s 会超时）

#### 步骤 4：环境变量（在 Environment 标签加）

⚠️ **这一节是你最需要小心的部分，Key 只在 Render 填，勿贴给别人**

| Key | Value | 说明 |
|---|---|---|
| `AI_MODE` | `deepseek` | **必填**，切到真实 API 模式 |
| `DEEPSEEK_API_KEY` | `sk-你的真实key` | **必填，勿提交 Git** |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | 默认 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 默认 |
| `DAILY_SUMMARY_LIMIT` | `10` | 每天生成说明书上限 |
| `DAILY_MATCH_LIMIT` | `10` | 每天召唤契合的人上限 |
| `DAILY_CHAT_LIMIT` | `10` | 每天 AI 聊天上限（V2 启用）|

⚠️ **`PORT` 不要手动设置**，Render 自动注入。

#### 步骤 5：创建服务
点 **Create Web Service**，等 2-5 分钟。

#### 步骤 6：访问
Render 会给一个 URL：`https://friend-manual-demo-v15-xxxx.onrender.com`

---

## 四、环境变量说明

### 4.1 全部变量清单

| 变量 | 默认值 | 必填 | 说明 |
|---|---|---|---|
| `AI_MODE` | `mock` | ✅ | `mock` 本地演示 / `deepseek` 生产 |
| `DEEPSEEK_API_KEY` | （空）| 真实模式必填 | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | 否 | DeepSeek API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 否 | 使用的模型 |
| `DAILY_SUMMARY_LIMIT` | `10` | 否 | 每天生成说明书上限 |
| `DAILY_MATCH_LIMIT` | `10` | 否 | 每天召唤契合的人上限 |
| `DAILY_CHAT_LIMIT` | `10` | 否 | 每天 AI 聊天上限（V2）|
| `PORT` | 平台注入 | 否 | 不要手动设置 |

### 4.2 修改限流

**线上环境**：在 Render Dashboard → Environment 改完保存 → 自动重启。

**本地环境**：编辑 `.env`：
```bash
DAILY_SUMMARY_LIMIT=20
DAILY_MATCH_LIMIT=20
DAILY_CHAT_LIMIT=20
```

**Mock 模式不限流**（仅 deepseek 模式生效）。

---

## 五、限流机制

### 5.1 限流规则

| 端点 | 默认限制 | 触发场景 |
|---|---|---|
| `summary` | 10 次/天 | 生成说明书 |
| `match` | 10 次/天 | 召唤契合的人 |
| `chat` | 10 次/天 | AI 聊天（V2 启用）|

- 按 **IP + 端点 + 日期** 统计
- 超限返回：`{"rate_limited": true, "error": "今天的探索次数已经用完啦，明天再来看看新的连接吧✨"}`
- 前端友好 toast 提示，不弹 alert

### 5.2 限流数据库表

```sql
CREATE TABLE rate_limits (
    id INTEGER PRIMARY KEY,
    ip TEXT,
    endpoint TEXT,    -- summary / match / chat
    date TEXT,        -- YYYY-MM-DD
    count INTEGER
);
```

### 5.3 紧急清空限流（线上环境）

Render 部署的是 SQLite，**默认实例休眠会清空数据**。如需手动清：
```bash
sqlite3 friend_manual.db "DELETE FROM rate_limits WHERE date = date('now')"
```

---

## 六、API 成本控制说明

本项目使用 DeepSeek API 提供 AI 能力。

由于大模型 API 按 token 使用量计费，实际成本会受到：

- **模型版本**（不同模型单价不同）
- **输入文本长度**（用户问题越长越贵）
- **输出长度**（AI 回答越长越贵）
- **用户调用次数**（调用越多次越贵）

等因素影响。

**因此 V1.5 增加以下成本保护机制**：

### 1. 用户每日调用次数限制

| 能力 | 限制 | 端点 |
|---|---|---|
| AI 融合总结 | 每日限制 X 次 | `DAILY_SUMMARY_LIMIT` |
| 契合推荐生成 | 每日限制 X 次 | `DAILY_MATCH_LIMIT` |
| AI 聊天能力 | 每日限制 X 次 | `DAILY_CHAT_LIMIT` |

### 2. 后台环境变量控制

所有限制参数支持通过环境变量调整，无需改代码：

```bash
DAILY_SUMMARY_LIMIT=
DAILY_MATCH_LIMIT=
DAILY_CHAT_LIMIT=
```

### 3. API Key 安全保护

- **API Key 仅存储于服务器环境变量**（不在代码、不在 Git）
- **不进入前端代码**（V1.8.1 已彻底移除 Key 引用）
- **不上传 GitHub**（`.env` 在 `.gitignore` 里）

**目标**：保证 Demo 开放体验的同时，避免异常请求导致 API 费用不可控。

---

## 七、上线前检查清单

### 7.1 服务端
- [ ] 服务部署成功（`https://xxx.onrender.com` 返回 200）
- [ ] Render Environment 配了 7 个变量
- [ ] `AI_MODE=deepseek`（不是 mock）
- [ ] `DEEPSEEK_API_KEY` 是真实 key
- [ ] 自己在浏览器打开 URL，答 5 道题成功
- [ ] 试一次召唤，看到真 AI 写的"为什么匹配"
- [ ] Render Logs 没有报错

### 7.2 GitHub 仓库
- [ ] 仓库里没有 `.env` 文件
- [ ] 仓库里搜不到 `DEEPSEEK_API_KEY`
- [ ] 仓库文件结构 = 本地项目结构

### 7.3 朋友体验前
- [ ] 把链接发到群里：`https://xxx.onrender.com`
- [ ] 提醒：每人每天 10 次生成 / 10 次召唤
- [ ] 不在群里发任何 key / 服务器信息

### 7.4 出问题怎么排查

| 症状 | 排查 |
|---|---|
| 朋友打不开链接 | Render 服务挂了？Dashboard → Logs 看 |
| 出题失败 | DeepSeek 余额用完？https://platform.deepseek.com |
| "Key 未配置" | Render Environment 里 Key 没配对 |
| 看不到页面 | Dashboard → Manual Deploy 重启 |
| 想看用户访问 | Dashboard → Logs → 实时日志 |

---

## 八、文件结构说明

### 8.1 完整项目结构

```
friend-manual-demo/
├── 📄 Python 核心代码
│   ├── app.py              # Flask 主程序（路由 + 业务逻辑）
│   ├── config.py           # V1.5: 配置入口（限流 + 环境变量）
│   ├── prompts.py          # Prompt 库（5 大场景）
│   ├── db.py               # SQLite 封装
│   ├── ai_service.py       # AI 调用统一封装（mock/deepseek）
│   └── mock_users.py       # 20 个虚拟人格 + 坐标
│
├── 📄 配置 / 文档
│   ├── requirements.txt
│   ├── README.md
│   ├── .env.example
│   ├── .gitignore
│   ├── DEPLOY_V1.5.md      # 本文档
│   └── switch_to_deepseek.sh
│
├── 📁 templates/           # 12 个 HTML 页面
└── 📁 static/              # app.css
```

### 8.2 各文件作用

| 路径 | 作用 |
|---|---|
| `app.py` | Flask 主程序 |
| `config.py` | V1.5 配置入口（限流 / 端口 / Key）|
| `prompts.py` | Prompt 库（5 大场景）|
| `db.py` | SQLite（含 `rate_limits` 表）|
| `ai_service.py` | DeepSeek 调用封装 |
| `mock_users.py` | 20 个虚拟人格 + social 坐标 |
| `templates/` | 全部前端页面 |
| `static/app.css` | 样式 |
| `requirements.txt` | Python 依赖 |
| `.env.example` | 配置模板（提交到 Git）|
| `.gitignore` | Git 忽略规则 |
| `switch_to_deepseek.sh` | 一键切真实 API 模式 |
| `friend_manual.db` | 用户数据（云端自动建，**不入库**）|

---

## 九、安全自查

部署完跑这 4 条命令：

```bash
# 1. .env 不被外人读（本地）
ls -la .env
# 期望：-rw-------  ... .env

# 2. .env 未入库
git status | grep .env
# 期望：nothing

# 3. 前端无 Key 痕迹
grep -r "sk-" templates/ static/
# 期望：No matches found

# 4. 服务在跑
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5001/
# 期望：200
```

---

## 十、附录：高级部署方式（自建服务器）

> ⚠️ 此方案适合**有运维经验**的开发者，新手请用方案三（Render）。
> 自建服务器需要自己处理：服务器购买、HTTPS、域名、Cloudflare 隧道、安全加固。

### 10.1 适用场景
- 数据需要持久化（Render 免费版会清）
- 需要自定义域名
- 需要更多控制权
- 已经有公网服务器

### 10.2 准备清单

| 需要的 | 怎么拿 |
|---|---|
| 一台公网服务器（最低 1 核 1G）| 阿里云 / 腾讯云 / DigitalOcean |
| 一个域名（建议）| Cloudflare / 阿里云 |
| DeepSeek API Key | https://platform.deepseek.com/api_keys |
| Python 3.9+ | 服务器自带 / `brew install python3` |

### 10.3 部署步骤

#### 上传代码到服务器

```bash
# 在你本地
cd /Users/xueer/Desktop/friend-manual-demo
tar czf friend-manual-v1.5.tar.gz \
    --exclude='.env' --exclude='__pycache__' --exclude='*.db' \
    --exclude='handoff-package' .
scp friend-manual-v1.5.tar.gz user@你的服务器:/home/user/
```

#### 在服务器上跑起来

```bash
ssh user@你的服务器
cd /home/user
tar xzf friend-manual-v1.5.tar.gz
cd friend-manual-demo/

pip3 install -r requirements.txt

cp .env.example .env
nano .env
# 改这两行：
#   AI_MODE=deepseek
#   DEEPSEEK_API_KEY=sk-填你的真实key
chmod 600 .env

# 测试
python3 app.py
# Ctrl+C 退出，后台跑：
nohup python3 app.py > /tmp/friend.log 2>&1 &
```

#### 配置 HTTPS（Cloudflare Tunnel）

```bash
# 装 cloudflared
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared focal main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install cloudflared

# 登录
cloudflared tunnel login

# 建隧道
cloudflared tunnel create friend-manual

# 配置 DNS（Cloudflare 控制台把 demo.你的域名 指向 tunnel）
cloudflared tunnel route dns friend-manual demo.你的域名.com

# 跑
nohup cloudflared tunnel --url http://localhost:5001 run friend-manual > /tmp/tunnel.log 2>&1 &
```

#### 日常运维

```bash
# 启动 / 停止 / 重启
lsof -ti:5001 | xargs kill -9
cd /home/user/friend-manual-demo
nohup python3 app.py > /tmp/friend.log 2>&1 &

# 看日志
tail -f /tmp/friend.log

# 看限流
sqlite3 friend_manual.db "SELECT * FROM rate_limits ORDER BY id DESC LIMIT 20"

# 清空限流
sqlite3 friend_manual.db "DELETE FROM rate_limits WHERE date = date('now')"
```

### 10.4 模式切换

```bash
# 切 mock
sed -i 's/AI_MODE=.*/AI_MODE=mock/' .env
lsof -ti:5001 | xargs kill -9
nohup python3 app.py > /tmp/friend.log 2>&1 &

# 切 deepseek
bash switch_to_deepseek.sh sk-你的key
```

---

## 总结

| 场景 | 推荐方案 | 耗时 |
|---|---|---|
| **新手 / 快速上线** | Render 一键部署 | 15 分钟 |
| 有数据持久化需求 | Render 付费 + PostgreSQL | 30 分钟 |
| 已有服务器 / 要自建 | 自建 + Cloudflare Tunnel | 1-2 小时 |

**新人建议直接走方案三（Render）**。等你熟悉了再考虑迁移到自建。

---

**准备好就开始，发链接前把第七节清单走一遍** 👊
