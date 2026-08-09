"""
朋友说明书 AI - Flask 后端 (V1.7)
- V0.x: 5 问访谈 + 说明书生成
- V1.4: 分享闭环
- V1.5: 朋友评价
- V2.0: 用户报告页 + AI 融合总结
- V2.1: prebuilt CSS 替代 Tailwind Play CDN
- V1.7: 召唤同类（模拟用户池 + AI 匹配）
- V1.5: 限流（防公网 API 费用失控）+ chat 占位入口
"""
import json
import os
import time
import re
import requests

# V1.5: 加载 .env 文件（python-dotenv 可选；装了就用）
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[V1.5] 已加载 .env 文件")
except ImportError:
    print("[V1.5] 未安装 python-dotenv，将只读系统环境变量")

from flask import Flask, request, jsonify, render_template
from prompts import (
    SYSTEM_PROMPT, build_task_prompt,
    INTERVIEW_SYSTEM_PROMPT, build_interview_task_prompt,
    PERSONALITY_LIBRARY,
    PERSPECTIVES, build_regenerate_prompt,
    build_summon_prompt, build_icebreaker_prompt,  # V1.7
)
from db import (
    init_db, upgrade_db, save_user, get_user_by_share_id, get_user_by_report_id,
    update_user_perspective, get_user_count,
    save_review, get_reviews_by_share_id, get_review_stats,
    save_fusion_summary, get_fusion_summary,
    save_summon_match, clear_summon_matches, get_summon_matches,  # V1.7
    save_icebreaker, get_icebreaker,  # V1.7
    save_relationship, get_relationship, get_all_relationships,  # V1.8.1
    get_rate_limit_count, increment_rate_limit,  # V1.5: 限流
    CHOICE_LABELS
)
from mock_users import get_all_mock_users, get_mock_user_by_id, get_mock_user_summaries  # V1.7
from ai_service import ai_call, get_mode, is_mock  # V1.8.1: AI 调用统一封装
from config import (  # V1.5: 集中配置
    DAILY_SUMMARY_LIMIT, DAILY_MATCH_LIMIT, DAILY_CHAT_LIMIT,
    ENABLE_RATE_LIMIT, RATE_LIMIT_MESSAGE,
)

app = Flask(__name__)
# V2.0.2：开发时改 HTML 模板不用重启（自动重载）
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


# ============================================================
# V1.5：限流工具函数
# ============================================================
def _client_ip() -> str:
    """取客户端 IP（兼容反代场景）"""
    return (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.headers.get("X-Real-IP", "").strip()
        or request.remote_addr
        or "unknown"
    )


def _check_rate_limit(endpoint: str, limit: int):
    """V1.5：检查限流。返回 (ok, current_count, error_msg)"""
    if not ENABLE_RATE_LIMIT:
        return True, 0, None
    ip = _client_ip()
    current = get_rate_limit_count(ip, endpoint)
    if current >= limit:
        return False, current, RATE_LIMIT_MESSAGE
    return True, current, None


def _bump_rate_limit(endpoint: str) -> int:
    """V1.5：自增计数（仅在 deepseek 模式生效）"""
    if not ENABLE_RATE_LIMIT:
        return 0
    return increment_rate_limit(_client_ip(), endpoint)


def get_admin_api_key():
    """V2.0.1：管理员 API Key（从环境变量读，不暴露给前端）

    启动时设置：DEEPSEEK_API_KEY=sk-xxx python3 app.py
    """
    return os.environ.get("DEEPSEEK_API_KEY", "").strip()


# ============================================================
# 全局错误处理：把 500 错误的 traceback 直接打到响应里
# 方便排查问题；生产环境应该关掉
# ============================================================
import traceback

@app.errorhandler(Exception)
def handle_exception(e):
    """任何未捕获异常都返回 JSON 而不是 Flask 默认的 HTML 错误页"""
    tb = traceback.format_exc()
    # 打印到 stderr 方便看日志
    print("=" * 60)
    print("[UNHANDLED EXCEPTION]")
    print(tb)
    print("=" * 60)
    return jsonify({
        "error": f"服务器内部错误: {type(e).__name__}",
        "detail": str(e)[:200],
        "traceback": tb[-1500:]  # 最后 1500 字 traceback
    }), 500


def call_deepseek(api_key, messages, temperature=0.9, max_tokens=2000, max_retry=2):
    """通用 DeepSeek 调用，带重试和 JSON 解析兜底"""
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": temperature,
        "top_p": 0.9,
        "max_tokens": max_tokens,
        "stream": False
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    last_error = None
    for attempt in range(max_retry):
        try:
            t0 = time.time()
            resp = requests.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=120  # V1.8: 加大 timeout（召唤匹配 prompt 约 7000 token，可能跑 60s+）
            )
            elapsed = round(time.time() - t0, 2)

            if resp.status_code != 200:
                return None, f"DeepSeek 返回 {resp.status_code}: {resp.text[:300]}", elapsed

            result = resp.json()
            content = result["choices"][0]["message"]["content"]

            try:
                data = json.loads(content)
                return data, None, elapsed
            except json.JSONDecodeError as e:
                last_error = f"JSON 解析失败: {str(e)} | content前200字: {content[:200]}"
                continue

        except requests.exceptions.Timeout:
            last_error = "DeepSeek 调用超时（60s）"
        except Exception as e:
            last_error = f"调用异常: {str(e)}"

    return None, last_error or "未知错误", 0


# ============================================================
# 路由
# ============================================================
@app.route("/")
def index():
    """首页（单页应用）"""
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    """避免 favicon.ico 触发 404，被全局 errorhandler 包装成 500 污染 console"""
    return ("", 204)


@app.route("/api/personality-library", methods=["GET"])
def get_personality_library():
    return jsonify({"library": PERSONALITY_LIBRARY})


@app.route("/api/start-interview", methods=["POST"])
def start_interview():
    """生成 5 道场景化问题 + 各自的 3-4 个选项

    V1.8.1：不再接收 api_key，统一用 ai_service（mock/deepseek 自动切换）
    V1.5：限流拦截（仅 deepseek 模式）
    """
    # V1.5：限流检查
    ok, current, err = _check_rate_limit("summary", DAILY_SUMMARY_LIMIT)
    if not ok:
        return jsonify({
            "ok": False,
            "error": err,
            "rate_limited": True,
            "limit": DAILY_SUMMARY_LIMIT,
            "used": current,
        }), 429

    messages = [
        {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
        {"role": "user", "content": build_interview_task_prompt()}
    ]

    result = ai_call(
        scenario="start_interview",
        user_profile={},
        messages=messages,
        temperature=0.95,
        max_tokens=2500,
        max_retry=2
    )

    if not result.get("ok"):
        return jsonify({
            "error": "题目生成失败",
            "detail": result.get("error", "未知错误"),
            "mode": result.get("mode")
        }), 500

    data = result["data"]
    questions = data.get("questions")
    if not questions or len(questions) != 5:
        return jsonify({
            "error": "AI 返回的题目数量不对",
            "detail": f"期望 5 道，实际 {len(questions) if questions else 0} 道"
        }), 500

    # 校验每道题的格式
    for i, q in enumerate(questions):
        if "question" not in q or "options" not in q:
            return jsonify({
                "error": f"第 {i+1} 道题格式不对",
                "detail": str(q)[:200]
            }), 500
        if not (3 <= len(q["options"]) <= 4):
            return jsonify({
                "error": f"第 {i+1} 道题选项数应该是 3-4 个",
                "detail": f"实际 {len(q['options'])} 个"
            }), 500

    return jsonify({
        "ok": True,
        "questions": questions,
        "elapsed": result.get("elapsed", 0),
        "mode": result.get("mode", "mock"),
        # V1.5：限流回显（mock 模式是 0）
        "rate_limit": {
            "summary_used": _bump_rate_limit("summary"),
            "summary_limit": DAILY_SUMMARY_LIMIT,
        },
    })


@app.route("/api/generate", methods=["POST"])
def generate_instruction():
    """生成朋友说明书（紧凑卡片版）

    V1.8.1：不再接收 api_key，统一用 ai_service（mock/deepseek 自动切换）

    请求体：
    {
        "answers": [
            {"emoji": "🪫", "text": "5%，躺平等天亮"},
            ...
        ]
    }
    """
    data = request.get_json() or {}
    answers = data.get("answers") or []

    if len(answers) != 5:
        return jsonify({
            "error": "需要正好 5 个回答",
            "detail": f"实际收到 {len(answers)} 个（可能是浏览器缓存了旧前端，请 Ctrl+Shift+R 强制刷新）"
        }), 400

    # V1.5：限流拦截（说明书生成也走 summary 配额）
    ok, current, err = _check_rate_limit("summary", DAILY_SUMMARY_LIMIT)
    if not ok:
        return jsonify({
            "ok": False,
            "error": err,
            "rate_limited": True,
            "limit": DAILY_SUMMARY_LIMIT,
            "used": current,
        }), 429

    # 校验每个 answer 必须是对象（防止旧前端传字符串数组导致 .get 报错）
    for i, a in enumerate(answers):
        if not isinstance(a, dict):
            return jsonify({
                "error": f"第 {i+1} 个答案格式不对（应该是对象，不是字符串）",
                "detail": f"收到: {str(a)[:100]}（很可能是浏览器缓存了旧前端，请 Ctrl+Shift+R 强制刷新）"
            }), 400
        if not a.get("text", "").strip():
            return jsonify({"error": "每个问题都需要回答"}), 400

    # 直接用原 answers 对象数组（前端已带 emoji/text/dim 三个字段）
    # 不再做格式转换，避免破坏结构
    task_prompt = build_task_prompt(answers)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task_prompt}
    ]

    result = ai_call(
        scenario="generate",
        user_profile={},
        messages=messages,
        extra={"answers": answers},
        temperature=0.9,
        max_tokens=2000,
        max_retry=2
    )

    if not result.get("ok"):
        return jsonify({
            "error": "说明书生成失败",
            "detail": result.get("error", "未知错误"),
            "mode": result.get("mode")
        }), 500

    instruction = result["data"]

    # 校验必要字段（V1.3 朋友观察版）
    required = ["main_type", "tags", "one_liner", "stats", "bug", "skill", "instruction"]
    missing = [k for k in required if k not in instruction]
    # share_quotes 数组（3 条候选金句）
    sq = instruction.get("share_quotes") or instruction.get("share_quote") or instruction.get("share_sentence")
    if not sq:
        missing.append("share_quotes")
    if missing:
        return jsonify({
            "error": "AI 返回的说明书缺字段",
            "detail": f"缺少: {missing}"
        }), 500

    # 兼容处理：如果 AI 还是返回 share_quote（字符串），包成数组
    if isinstance(sq, str):
        instruction["share_quotes"] = [sq]
    elif not isinstance(instruction.get("share_quotes"), list):
        instruction["share_quotes"] = list(sq) if sq else []

    return jsonify({
        "ok": True,
        "instruction": instruction,
        "elapsed": result.get("elapsed", 0),
        "mode": result.get("mode", "mock")
    })


@app.route("/api/regenerate", methods=["POST"])
def regenerate_instruction():
    """换视角重生成（V1.3 新功能）

    V1.8.1：不再接收 api_key，统一用 ai_service（mock/deepseek 自动切换）

    请求体：
    {
        "instruction": {原始说明书 JSON},
        "perspective": "close_friend" | "bestie" | "first_meet" | "ai_analyst"
    }
    """
    data = request.get_json() or {}
    instruction = data.get("instruction") or {}
    perspective = (data.get("perspective") or "").strip()

    if not instruction or not isinstance(instruction, dict):
        return jsonify({"error": "缺少原始说明书 instruction"}), 400
    if perspective not in PERSPECTIVES:
        return jsonify({
            "error": "视角不对",
            "detail": f"可选: {list(PERSPECTIVES.keys())}"
        }), 400

    # 构造换视角的 prompt
    task_prompt, perspective_info = build_regenerate_prompt(instruction, perspective)
    if not task_prompt:
        return jsonify({"error": "Prompt 构造失败"}), 500

    # 调用 AI（V1.8.1：统一用 ai_service）
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task_prompt}
    ]

    result = ai_call(
        scenario="regenerate",
        user_profile=instruction,
        messages=messages,
        extra={"instruction": instruction, "perspective": perspective},
        temperature=0.9,
        max_tokens=2000,
        max_retry=2
    )

    if not result.get("ok"):
        return jsonify({
            "error": f"重生成失败（{perspective_info['name']}）",
            "detail": result.get("error", "未知错误"),
            "mode": result.get("mode")
        }), 500

    new_data = result["data"]

    # 强制保留主数据（即使 AI 想改也覆盖回去）
    new_data["main_type"] = instruction.get("main_type", new_data.get("main_type"))
    new_data["tags"] = instruction.get("tags", new_data.get("tags"))
    new_data["stats"] = instruction.get("stats", new_data.get("stats"))
    new_data["main_type_reason"] = instruction.get("main_type_reason", new_data.get("main_type_reason"))

    # 校验关键字段
    for field in ["bug", "skill", "one_liner", "instruction", "others_view", "share_quotes"]:
        if field not in new_data:
            return jsonify({
                "error": f"换视角生成缺字段 {field}",
                "detail": str(list(new_data.keys()))[:200]
            }), 500

    # 兼容性：share_quotes 若是字符串包成数组
    if isinstance(new_data.get("share_quotes"), str):
        new_data["share_quotes"] = [new_data["share_quotes"]]
    if not isinstance(new_data.get("share_quotes"), list):
        new_data["share_quotes"] = [str(new_data.get("share_quotes", ""))]

    return jsonify({
        "ok": True,
        "instruction": new_data,
        "perspective": perspective,
        "perspective_name": perspective_info["name"],
        "elapsed": result.get("elapsed", 0),
        "mode": result.get("mode", "mock")
    })


@app.route("/api/perspectives", methods=["GET"])
def get_perspectives():
    """返回可选的 4 种观察视角"""
    return jsonify({
        "perspectives": [
            {"key": k, "name": v["name"], "description": v["description"]}
            for k, v in PERSPECTIVES.items()
        ]
    })


# ============================================================
# V1.4：分享 & 社交闭环
# ============================================================

@app.route("/api/save", methods=["POST"])
def save_profile():
    """保存用户说明书，返回 share_id

    请求体：
    {
        "profile": {完整 instruction JSON},
        "answers": [...],   // 可选
        "perspective": "close_friend"  // 可选
    }
    """
    data = request.get_json() or {}
    profile = data.get("profile")
    answers = data.get("answers")
    perspective = data.get("perspective")

    if not profile or not isinstance(profile, dict):
        return jsonify({"error": "缺少 profile（说明书）"}), 400
    if not profile.get("main_type"):
        return jsonify({"error": "profile 缺少 main_type"}), 400

    try:
        user_id, share_id, report_id = save_user(profile, answers, perspective)
        print("DEBUG:", user_id, share_id, report_id)
    except Exception as e:
        return jsonify({"error": f"保存失败: {str(e)}"}), 500

    return jsonify({
        "ok": True,
        "user_id": user_id,
        "share_id": share_id,
        "report_id": report_id,
        "share_url": f"/profile/{share_id}",
        "report_url": f"/report/{report_id}",
        "total_users": get_user_count()
    })


@app.route("/api/profile/<share_id>", methods=["GET"])
def api_get_profile(share_id):
    """通过 share_id 获取说明书（API）"""
    user = get_user_by_share_id(share_id)
    if not user:
        return jsonify({"error": "说明书不存在", "share_id": share_id}), 404
    return jsonify({
        "ok": True,
        "user_id": user["user_id"],
        "profile": user["profile"],
        "created_time": user["created_time"]
    })


@app.route("/profile/<share_id>")
def profile_page(share_id):
    """分享页（公共访问）"""
    user = get_user_by_share_id(share_id)
    if not user:
        return render_template("not_found.html", share_id=share_id), 404
    # V1.5：加载评价数据
    reviews = get_reviews_by_share_id(share_id)
    stats = get_review_stats(share_id)
    return render_template("profile.html",
                           share_id=share_id,
                           profile=user["profile"],
                           reviews=reviews,
                           stats=stats,
                           choice_labels=CHOICE_LABELS)


# ============================================================
# V1.5：朋友评价
# ============================================================

@app.route("/api/reviews", methods=["POST"])
def submit_review():
    """提交朋友评价

    请求体：
    {
        "share_id": "xxx",
        "review_user_name": "小明",
        "choice": "accurate" | "partial" | "misunderstand",
        "comment": "可选，评论"
    }
    """
    data = request.get_json() or {}
    share_id = (data.get("share_id") or "").strip()
    review_user_name = (data.get("review_user_name") or "").strip()
    choice = (data.get("choice") or "").strip() or None
    comment = (data.get("comment") or "").strip() or None

    if not share_id:
        return jsonify({"error": "缺少 share_id"}), 400
    if not review_user_name:
        return jsonify({"error": "请填写你的称呼（让 TA 知道是谁评价的）"}), 400
    # V2.0 校验：choice 和 comment 至少有一个
    if not choice and not comment:
        return jsonify({
            "error": "写一句你对 TA 的真实观察吧（选标签 或 写评论 至少一个）"
        }), 400
    # 如果有 choice，必须是合法值
    if choice and choice not in CHOICE_LABELS:
        return jsonify({
            "error": "choice 必须是 accurate / partial / misunderstand 之一",
            "valid_choices": list(CHOICE_LABELS.keys())
        }), 400

    # 校验 share_id 真实存在
    user = get_user_by_share_id(share_id)
    if not user:
        return jsonify({"error": "说明书不存在", "share_id": share_id}), 404

    try:
        review_id = save_review(
            review_user_name=review_user_name,
            target_user_id=user["user_id"],
            share_id=share_id,
            choice=choice,
            comment=comment
        )
    except Exception as e:
        return jsonify({"error": f"提交失败: {str(e)}"}), 500

    return jsonify({
        "ok": True,
        "review_id": review_id,
        "total_reviews": len(get_reviews_by_share_id(share_id))
    })


@app.route("/api/reviews/<share_id>", methods=["GET"])
def api_get_reviews(share_id):
    """获取某份说明书的所有评价"""
    reviews = get_reviews_by_share_id(share_id)
    stats = get_review_stats(share_id)
    return jsonify({
        "ok": True,
        "share_id": share_id,
        "total": len(reviews),
        "stats": stats,
        "reviews": [{
            "id": r["id"],
            "review_user_name": r["review_user_name"],
            "choice": r["choice"],
            "comment": r["comment"],
            "created_time": r["created_time"]
        } for r in reviews]
    })


# ============================================================
# V2.0：用户自己的报告页 + AI 融合总结
# ============================================================

@app.route("/report/<int:report_id>")
def report_page(report_id):
    """用户自己的报告页（含 AI 初识 + 朋友评价 + 融合总结）"""
    user = get_user_by_report_id(report_id)
    if not user:
        return render_template("not_found.html", share_id=report_id), 404

    # 加载朋友评价
    reviews = get_reviews_by_share_id(user["share_id"])
    stats = get_review_stats(user["share_id"])
    # 加载 AI 融合总结（可能没有）
    fusion = get_fusion_summary(report_id)

    return render_template("report.html",
                           report_id=report_id,
                           share_id=user["share_id"],
                           profile=user["profile"],
                           reviews=reviews,
                           stats=stats,
                           fusion=fusion,
                           choice_labels=CHOICE_LABELS)


# ============================================================
# V1.9 说明书独立页（深度探索）
# ============================================================
@app.route("/manual/<int:report_id>")
def manual_page(report_id):
    """完整说明书（V1.9 独立于身份卡的深度探索页）"""
    user = get_user_by_report_id(report_id)
    if not user:
        return render_template("not_found.html", share_id=report_id), 404

    reviews = get_reviews_by_share_id(user["share_id"])
    fusion = get_fusion_summary(report_id)

    return render_template("manual.html",
                           report_id=report_id,
                           share_id=user["share_id"],
                           profile=user["profile"],
                           reviews=reviews,
                           fusion=fusion)


# ============================================================
# V1.9 身份卡主页（个人空间入口）
# ============================================================
@app.route("/me")
def me_home():
    """用户自己的身份卡主页（V1.9 信息架构核心）

    - 如果有 report_id（URL 参数或 referer），跳到 /me/<id>
    - 否则渲染"开始生成"引导页
    """
    return render_template("identity.html", mode="empty")


@app.route("/me/<int:report_id>")
def me_with_report(report_id):
    """用户自己的身份卡主页（带身份卡）"""
    user = get_user_by_report_id(report_id)
    if not user:
        return render_template("not_found.html", share_id=report_id), 404

    # 加载朋友评价数量
    reviews = get_reviews_by_share_id(user["share_id"])

    # 加载召唤匹配数量
    matches_db = get_summon_matches(report_id)
    matches_count = len(matches_db) if matches_db else 0

    return render_template("identity.html",
                           mode="card",
                           report_id=report_id,
                           share_id=user["share_id"],
                           profile=user["profile"],
                           reviews=reviews,
                           reviews_count=len(reviews),
                           matches_count=matches_count)


# ============================================================
# V1.9 朋友评价列表页（独立于报告页）
# ============================================================
@app.route("/reviews/<int:report_id>")
def reviews_page(report_id):
    """朋友眼中的我（朋友评价列表）"""
    user = get_user_by_report_id(report_id)
    if not user:
        return render_template("not_found.html", share_id=report_id), 404

    reviews = get_reviews_by_share_id(user["share_id"])
    stats = get_review_stats(user["share_id"])

    return render_template("reviews.html",
                           report_id=report_id,
                           share_id=user["share_id"],
                           profile=user["profile"],
                           reviews=reviews,
                           stats=stats,
                           choice_labels=CHOICE_LABELS)


def build_fusion_prompt(profile, reviews):
    """构造 AI 融合总结的 Prompt"""
    profile_text = json.dumps(profile, ensure_ascii=False, indent=2)
    reviews_text = "\n".join([
        f"- {r['review_user_name']}（{r.get('choice') or '未选标签'}）：{r.get('comment') or '（仅选标签）'}"
        for r in reviews
    ]) or "（暂无朋友评价）"

    return f"""【AI 原始报告】
{profile_text}

【朋友评价（{len(reviews)} 条）】
{reviews_text}

【任务】
基于 AI 原始报告 + 朋友评价，生成"融合版本"。
不要覆盖 AI 原始报告，而是**融合 AI 初识 + 朋友观察**。

【输出 JSON Schema】
{{
  "v1_ai_initial": "AI 第一次怎么看你（≤50字）",
  "v1_friend_observations": [
    {{
      "name": "朋友昵称",
      "tag": "AI 说中了 / 差点东西 / AI 误会了",
      "summary": "朋友的关键观察（≤30字）"
    }}
  ],
  "v2_fusion_summary": "AI 融合后的重新理解（≤80字，朋友视角下更立体的你）",
  "new_insight": "AI 原始报告没看到、但朋友帮你看到的一个新点（≤40字）"
}}

要求：
- 不要简单堆砌
- v2_fusion_summary 要"原来 + 朋友补充 + 现在"三段融合
- new_insight 是 AI 主动承认"我没看到的那个点"
- 朋友视角要保留人的温度，不是冷冰冰分析

请直接输出 JSON，不要任何 markdown 代码块标记。"""


@app.route("/api/fusion/<int:report_id>", methods=["POST"])
def generate_fusion(report_id):
    """生成 AI 融合总结

    V1.8.1：不再接收 api_key，统一用 ai_service（mock/deepseek 自动切换）
    """
    user = get_user_by_report_id(report_id)
    if not user:
        return jsonify({"error": "报告不存在", "report_id": report_id}), 404

    reviews = get_reviews_by_share_id(user["share_id"])
    if len(reviews) == 0:
        return jsonify({"error": "还没有朋友评价，无法生成融合总结"}), 400

    # 调 LLM
    prompt = build_fusion_prompt(user["profile"], reviews)
    messages = [
        {"role": "system", "content": "你是「朋友说明书」AI 融合师。你要把 AI 原始分析 + 朋友观察融合成一份更立体的说明书。语气要像朋友 + 互联网嘴替。"},
        {"role": "user", "content": prompt}
    ]

    result = ai_call(
        scenario="fusion",
        user_profile=user["profile"],
        mock_user_summaries=reviews,  # 复用字段传 reviews
        messages=messages,
        temperature=0.9,
        max_tokens=1500,
        max_retry=2
    )

    if not result.get("ok"):
        # 失败不暴露技术细节，统一友好提示
        return jsonify({
            "error": "AI 正在休息，请稍后再试",
            "code": "ai_error",
            "detail": result.get("error", ""),
            "mode": result.get("mode")
        }), 500

    fusion_data = result["data"]

    # 校验
    for field in ["v1_ai_initial", "v1_friend_observations", "v2_fusion_summary", "new_insight"]:
        if field not in fusion_data:
            return jsonify({
                "error": "AI 正在休息，请稍后再试",
                "code": "ai_response_invalid"
            }), 500

    # 保存到 DB
    save_fusion_summary(report_id, fusion_data, len(reviews))

    return jsonify({
        "ok": True,
        "report_id": report_id,
        "fusion": fusion_data,
        "review_count": len(reviews),
        "elapsed": result.get("elapsed", 0),
        "mode": result.get("mode", "mock")
    })


@app.route("/api/fusion/<int:report_id>", methods=["GET"])
def api_get_fusion(report_id):
    """获取 AI 融合总结（V2.0）"""
    fusion = get_fusion_summary(report_id)
    if not fusion:
        return jsonify({"ok": True, "fusion": None, "report_id": report_id})
    return jsonify({
        "ok": True,
        "report_id": report_id,
        "fusion": fusion["summary"],
        "review_count": fusion["review_count"],
        "updated_time": fusion["updated_time"]
    })


# ============================================================
# V1.7：召唤同类
# ============================================================

@app.route("/summon/<int:report_id>")
def summon_page(report_id):
    """召唤同类页面（V1.7）
    V1.5opt：传 profile 给模板，让参数显示真实内容
    """
    user = get_user_by_report_id(report_id)
    if not user:
        return render_template("not_found.html"), 404
    return render_template("summon.html", report_id=report_id, profile=user.get("profile", {}))


@app.route("/icebreak/<int:report_id>/<mock_user_id>")
def icebreak_page(report_id, mock_user_id):
    """AI 破冰助手页面（V1.8 新增）

    从 summon.html 点"💬 开始认识TA"跳到这里
    """
    user = get_user_by_report_id(report_id)
    if not user:
        return render_template("not_found.html"), 404
    mock = get_mock_user_by_id(mock_user_id)
    if not mock:
        return render_template("not_found.html"), 404
    return render_template("icebreak.html", report_id=report_id, mock_user=mock)


@app.route("/chat/<int:report_id>/<mock_user_id>")
def chat_page(report_id, mock_user_id):
    """V1.5：聊天页面占位（V2 关系记忆入口）

    只展示：TA 头像 + 名字 + 一句话介绍 + 输入框 UI（不可输入）
    V2 将在此基础加：破冰话术 / 聊天小智囊 / 我们的故事 / AI 关系记忆
    """
    user = get_user_by_report_id(report_id)
    if not user:
        return render_template("not_found.html"), 404
    mock = get_mock_user_by_id(mock_user_id)
    if not mock:
        return render_template("not_found.html"), 404
    return render_template("chat.html", report_id=report_id, mock_user=mock)


@app.route("/api/summon/<int:report_id>", methods=["POST"])
def api_summon(report_id):
    """触发召唤同类匹配（V1.8.1 - 改用 ai_service 统一封装）

    1 次 AI 调用，从 20 个模拟用户中找 Top 3 + 评分 + 解释 + 关系类型
    V1.5：限流拦截（match 配额）+ 返回 3-5 人（前端按 3 核心展示，剩的入池）
    V1.5: 支持 append=true 追加模式（紫色按钮使用，不清空旧匹配）
    """
    # V1.5: 追加模式（紫色按钮专用）
    is_append = request.get_json(silent=True) or {}
    is_append = bool(is_append.get("append", False))

    # V1.5：限流检查
    ok, current, err = _check_rate_limit("match", DAILY_MATCH_LIMIT)
    if not ok:
        return jsonify({
            "ok": False,
            "error": err,
            "rate_limited": True,
            "limit": DAILY_MATCH_LIMIT,
            "used": current,
        }), 429

    # V1.8.1：不再接受 api_key，统一用 ai_service（mock/deepseek 自动切换）
    user = get_user_by_report_id(report_id)
    if not user:
        return jsonify({"error": "报告不存在", "report_id": report_id}), 404

    profile = user["profile"]
    mock_summaries = get_mock_user_summaries()

    # 构建 prompt（用于 deepseek 模式）
    from prompts import build_summon_prompt
    prompt = build_summon_prompt(profile, mock_summaries)
    messages = [
        {"role": "system", "content": "你是「朋友说明书 AI」的匹配师。你要按\"人类运行参数\"匹配 Top 3，必须输出严格 JSON。"},
        {"role": "user", "content": prompt}
    ]

    # V1.8.1：统一调用 ai_service
    result = ai_call(
        scenario="summon",
        user_profile=profile,
        mock_user_summaries=mock_summaries,
        prompt=prompt,
        messages=messages,
        temperature=0.85,
        max_tokens=2000,
    )

    if not result.get("ok"):
        return jsonify({
            "error": result.get("error", "AI 匹配失败"),
            "mode": result.get("mode"),
            "elapsed": result.get("elapsed", 0)
        }), 500

    parsed = result["data"]
    matches = parsed.get("matches", [])
    if not matches:
        return jsonify({"error": "AI 没有返回有效匹配", "raw": str(parsed)[:500]}), 500

    # V1.5: 追加模式不清空，常规模式才清空
    if not is_append:
        clear_summon_matches(report_id)

    # 验证 mock_user_id 真实存在 + 写 DB
    valid_mock_ids = {u["id"] for u in get_all_mock_users()}
    saved = 0
    for m in matches:
        if m.get("mock_user_id") not in valid_mock_ids:
            continue
        if saved >= 3:
            break
        saved += 1
        scores = m.get("scores", {})
        save_summon_match(
            report_id=report_id,
            mock_user_id=m["mock_user_id"],
            rank=saved,
            scores={
                "total": scores.get("total", 0),
                "token": scores.get("token", 0),
                "energy": scores.get("energy", 0),
                "firewall": scores.get("firewall", 0),
                "interest": scores.get("interest", 0),
                "value": scores.get("value", 0),
            },
            explanation=m.get("explanation", ""),
            relationship_types=m.get("relationship_types", []),
            detailed_analysis=m.get("detailed_analysis"),
        )

    return jsonify({
        "ok": True,
        "report_id": report_id,
        "match_count": saved,
        "elapsed": result.get("elapsed", 0),
        "mode": result.get("mode"),
        # V1.5：限流回显 + 召唤池大小（前端做左右滑）
        "rate_limit": {
            "match_used": _bump_rate_limit("match"),
            "match_limit": DAILY_MATCH_LIMIT,
        },
        "pool_size": saved,  # 暂存多少个推荐（V1.5：3 个核心；后续扩到 5-8）
    })


@app.route("/api/summon/<int:report_id>/matches", methods=["GET"])
def api_get_summon_matches(report_id):
    """获取召唤结果（V1.7）"""
    matches = get_summon_matches(report_id)
    if not matches:
        return jsonify({"ok": True, "matches": [], "report_id": report_id})

    # 关联 mock 用户详情
    enriched = []
    for m in matches:
        mock = get_mock_user_by_id(m["mock_user_id"])
        if not mock:
            continue
        enriched.append({
            "rank": m["rank"],
            "scores": m["scores"],
            "explanation": m["explanation"],
            "relationship_types": m["relationship_types"],
            "detailed_analysis": m.get("detailed_analysis", {}),  # V1.8
            "mock_user": {
                "id": mock["id"],
                "name": mock["name"],
                "main_type": mock["main_type"],
                "one_liner": mock["one_liner"],
                "intro": mock["intro"],
                "share_quote": mock["share_quote"],
                "params": mock["params"],
                # V1.5: 关系坐标（二维图用）
                "social_x": mock.get("social_x", 0),
                "social_y": mock.get("social_y", 0),
            },
        })
    return jsonify({
        "ok": True,
        "report_id": report_id,
        "matches": enriched,
    })


@app.route("/api/icebreaker/<int:report_id>/<mock_user_id>", methods=["POST"])
def api_icebreaker(report_id, mock_user_id):
    """生成 AI 破冰话题（V1.8.1 - 改用 ai_service 统一封装）
    V1.5：限流拦截（chat 配额，为 V2 聊天预留）
    """
    # V1.5：限流检查
    ok, current, err = _check_rate_limit("chat", DAILY_CHAT_LIMIT)
    if not ok:
        return jsonify({
            "ok": False,
            "error": err,
            "rate_limited": True,
            "limit": DAILY_CHAT_LIMIT,
            "used": current,
        }), 429

    user = get_user_by_report_id(report_id)
    if not user:
        return jsonify({"error": "报告不存在"}), 404
    mock = get_mock_user_by_id(mock_user_id)
    if not mock:
        return jsonify({"error": "匹配用户不存在"}), 404

    profile = user["profile"]
    prompt = build_icebreaker_prompt(profile, mock)

    # V1.8.1: 统一调用 ai_service
    result = ai_call(
        scenario="icebreaker",
        user_profile=profile,
        mock_user=mock,
        prompt=prompt,
        messages=[
            {"role": "system", "content": "你是一个严格按照要求输出 json 格式数据的助手。"},
            {"role": "user", "content": prompt},
        ],
        extra={"regenerate": False},
        temperature=0.95,
        max_tokens=1500,
    )

    if not result.get("ok"):
        return jsonify({
            "error": result.get("error"),
            "mode": result.get("mode"),
        }), 500

    icebreakers = result["data"].get("icebreakers", [])
    if not icebreakers:
        return jsonify({"error": "AI 没返回有效内容"}), 500

    # 存
    save_icebreaker(report_id, mock_user_id, json.dumps(icebreakers, ensure_ascii=False))

    return jsonify({
        "ok": True,
        "report_id": report_id,
        "mock_user_id": mock_user_id,
        "icebreakers": icebreakers,
        "elapsed": result.get("elapsed", 0),
        "mode": result.get("mode"),
        # V1.5：限流回显
        "rate_limit": {
            "chat_used": _bump_rate_limit("chat"),
            "chat_limit": DAILY_CHAT_LIMIT,
        },
    })


@app.route("/api/icebreaker/regenerate/<int:report_id>/<mock_user_id>", methods=["POST"])
def api_icebreaker_regenerate(report_id, mock_user_id):
    """重新生成 AI 破冰话题（V1.8.1 - "换一个"按钮，ai_service 统一）"""
    user = get_user_by_report_id(report_id)
    if not user:
        return jsonify({"error": "报告不存在"}), 404
    mock = get_mock_user_by_id(mock_user_id)
    if not mock:
        return jsonify({"error": "匹配用户不存在"}), 404

    profile = user["profile"]
    prompt = build_icebreaker_prompt(profile, mock)

    # V1.8.1：统一调用 ai_service
    result = ai_call(
        scenario="icebreaker",
        user_profile=profile,
        mock_user=mock,
        prompt=prompt,
        messages=[
            {"role": "system", "content": "你是一个严格按照要求输出 json 格式数据的助手。"},
            {"role": "user", "content": prompt},
        ],
        extra={"regenerate": True},
        temperature=1.0,
        max_tokens=1500,
    )

    if not result.get("ok"):
        return jsonify({
            "error": result.get("error"),
            "mode": result.get("mode"),
        }), 500

    icebreakers = result["data"].get("icebreakers", [])
    if not icebreakers:
        return jsonify({"error": "AI 没返回有效内容"}), 500

    save_icebreaker(report_id, mock_user_id, json.dumps(icebreakers, ensure_ascii=False))

    return jsonify({
        "ok": True,
        "report_id": report_id,
        "mock_user_id": mock_user_id,
        "icebreakers": icebreakers,
        "elapsed": result.get("elapsed", 0),
        "mode": result.get("mode"),
    })


# ============================================================
# V1.8.1：双人关系说明书
# ============================================================

@app.route("/relationship/<int:report_id>/<mock_user_id>")
def relationship_page(report_id, mock_user_id):
    """双人关系说明书页面（V1.8.1 新增）"""
    user = get_user_by_report_id(report_id)
    if not user:
        return render_template("not_found.html"), 404
    mock = get_mock_user_by_id(mock_user_id)
    if not mock:
        return render_template("not_found.html"), 404
    return render_template("relationship.html", report_id=report_id, mock_user=mock)


@app.route("/api/relationship/<int:report_id>/<mock_user_id>", methods=["POST"])
def api_relationship(report_id, mock_user_id):
    """生成双人关系说明书（V1.8.1）

    V1.8.1：改用 ai_service 统一封装，页面无需感知
    """
    user = get_user_by_report_id(report_id)
    if not user:
        return jsonify({"error": "报告不存在"}), 404
    mock = get_mock_user_by_id(mock_user_id)
    if not mock:
        return jsonify({"error": "匹配用户不存在"}), 404

    profile = user["profile"]

    # V1.8.1：统一调用 ai_service
    result = ai_call(
        scenario="relationship",
        user_profile=profile,
        mock_user=mock,
        temperature=0.85,
        max_tokens=1500,
    )

    if not result.get("ok"):
        return jsonify({
            "error": result.get("error"),
            "mode": result.get("mode"),
        }), 500

    data = result["data"]

    # 存到 relationships 表（关系资产沉淀）
    save_relationship(
        report_id=report_id,
        mock_user_id=mock_user_id,
        match_score=user.get("report_id") and 89,  # 简化：用 user 数据
        relationship_analysis=data,
        has_report=True,
    )

    return jsonify({
        "ok": True,
        "report_id": report_id,
        "mock_user_id": mock_user_id,
        "data": data,
        "mode": result.get("mode"),
        "elapsed": result.get("elapsed", 0),
    })


@app.route("/api/relationship/<int:report_id>/<mock_user_id>", methods=["GET"])
def api_get_relationship(report_id, mock_user_id):
    """获取已存的关系说明书"""
    rel = get_relationship(report_id, mock_user_id)
    if not rel:
        return jsonify({"ok": True, "relationship": None, "report_id": report_id})
    return jsonify({
        "ok": True,
        "report_id": report_id,
        "mock_user_id": mock_user_id,
        "relationship": rel,
    })


# ============================================================
# V1.8.1：我的同类地图
# ============================================================

@app.route("/social-map/<int:report_id>")
def social_map_page(report_id):
    """我的同类地图页面（V1.8.1 新增）"""
    user = get_user_by_report_id(report_id)
    if not user:
        return render_template("not_found.html"), 404
    return render_template("social_map.html", report_id=report_id)


@app.route("/api/social-map/<int:report_id>")
def api_social_map(report_id):
    """获取我的同类地图（V1.8.1）

    V1.8.1：改用 ai_service 统一封装
    """
    user = get_user_by_report_id(report_id)
    if not user:
        return jsonify({"error": "报告不存在"}), 404

    # 先取所有 summon_matches
    matches_db = get_summon_matches(report_id)
    if not matches_db:
        return jsonify({
            "ok": True,
            "report_id": report_id,
            "matches": [],
            "social_dna": None,
            "next_step": "你还没有召唤过同类。先去召唤同类，回来就能看到地图了。",
            "mode": get_mode(),
        })

    # 拼装完整 match 列表
    matches = []
    for m in matches_db:
        mock = get_mock_user_by_id(m["mock_user_id"])
        if not mock:
            continue
        matches.append({
            "rank": m["rank"],
            "scores": m["scores"],
            "explanation": m["explanation"],
            "relationship_types": m["relationship_types"],
            "has_relationship": bool(get_relationship(report_id, m["mock_user_id"])),
            "mock_user": {
                "id": mock["id"],
                "name": mock["name"],
                "main_type": mock["main_type"],
                "one_liner": mock["one_liner"],
                "params": mock["params"],
            },
        })

    # V1.8.1：统一调用 ai_service 生成社交 DNA
    result = ai_call(
        scenario="social_map",
        user_profile=user["profile"],
        matches=matches,
        temperature=0.7,
        max_tokens=1000,
    )

    if not result.get("ok"):
        return jsonify({
            "ok": False,
            "error": result.get("error"),
            "mode": result.get("mode"),
        }), 500

    data = result["data"]

    return jsonify({
        "ok": True,
        "report_id": report_id,
        "matches": matches,
        "social_dna": data.get("social_dna"),
        "matches_summary": data.get("matches_summary"),
        "ai_observation": data.get("ai_observation"),  # V1.5opt
        "next_step": data.get("next_step"),
        "mode": result.get("mode"),
    })


if __name__ == "__main__":
    # V1.4/V2.0：初始化 DB + 老数据升级
    init_db()
    upgrade_db()
    print("=" * 60)
    print("📖 朋友说明书 AI Demo v1.4")
    print("访问地址: http://localhost:5001")
    print("按 Ctrl+C 停止")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5001, debug=False)
