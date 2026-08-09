"""
AI 服务统一封装（V1.8.1 - P0 基础）

解决老大需求：
- 不恢复用户输入 API Key
- 通过环境变量 AI_MODE 切换 mock / deepseek
- 页面无需感知

环境变量：
- AI_MODE=mock     → 用 mock 数据（开发/演示）
- AI_MODE=deepseek → 用 DEEPSEEK_API_KEY 调真实 API（生产）
- 默认 mock（无 Key 也能完整体验）
"""
import os
import json
import time
import requests
from typing import Any, Dict, Optional, List


# ============================================================
# 配置
# ============================================================
AI_MODE = os.environ.get("AI_MODE", "mock").strip().lower()  # mock | deepseek
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


def get_admin_api_key() -> str:
    """从环境变量读取管理员 Key（仅 deepseek 模式用）"""
    return os.environ.get("DEEPSEEK_API_KEY", "").strip()


# ============================================================
# Mock 数据（按调用场景区分）
# ============================================================

def _mock_summon(user_profile: dict, mock_user_summaries: list) -> dict:
    """Mock：召唤同类匹配"""
    main_type = user_profile.get("main_type", "未知")
    one_liner = user_profile.get("one_liner", user_profile.get("intro", ""))
        # 根据用户回答动态选择推荐池
    if any(k in one_liner for k in ["运动", "户外", "旅行", "摄影"]):
        order = ["mock_003", "mock_008", "mock_011"]

    elif any(k in one_liner for k in ["阅读", "学习", "思考", "写作"]):
        order = ["mock_016", "mock_018", "mock_017"]

    else:
        order = ["mock_017", "mock_016", "mock_018"]

    # V1.5: 给 mock 推荐注入 social 坐标（从 mock_users 读取，让坐标图能渲染）
    from mock_users import get_mock_user_by_id
    def _coord(uid):
        u = get_mock_user_by_id(uid)
        if not u:
            return {"social_x": 0, "social_y": 0}
        return {"social_x": u.get("social_x", 0), "social_y": u.get("social_y", 0)}
    return {
        "matches": [
            {
                "mock_user_id": order[0],
                "rank": 1,
                **_coord(order[0]),  # V1.5: 注入 social 坐标
                "scores": {"total": 89, "token": 92, "energy": 90, "firewall": 88, "interest": 80, "value": 85},
                "explanation": f"你们都是低耗能高续航人类。你 {main_type} 谨慎决策，TA 节能模式按自己节奏。你们能各自充电又能在场。",
                "detailed_analysis": {
                    "energy": {
                        "common_ground": "你们都是独处回血型，社交消耗能量",
                        "why_fit": "长期相处不会互相消耗，能各自充电又能在场"
                    },
                    "social": {
                        "common_ground": "都喜欢深聊而非泛泛之交",
                        "why_fit": "不容易冷场，话题深度足够支撑长期关系"
                    },
                    "value": {
                        "common_ground": "都重视长期关系，不喜欢速食社交",
                        "why_fit": "价值观一致能让关系走得更远"
                    }
                },
                "relationship_types": [
                    {"type": "🌿 安静陪伴", "score": 95, "scenario": "不需要一直聊也不会尴尬"},
                    {"type": "☕ 深聊朋友", "score": 82, "scenario": "想说话时能聊到深夜"}
                ]
            },
            {
                "mock_user_id": order[1],
                "rank": 2,
                **_coord(order[1]),  # V1.5: 注入 social 坐标
                "scores": {"total": 82, "token": 78, "energy": 88, "firewall": 85, "interest": 72, "value": 80},
                "explanation": "慢热对慢热。第一次见面安静，第三次就开始讲人生。",
                "detailed_analysis": {
                    "energy": {"common_ground": "你们都倾向于独处充电", "why_fit": "能互相给空间不会索取"},
                    "social": {"common_ground": "都喜欢观察后表达", "why_fit": "节奏一致不容易抢话"},
                    "value": {"common_ground": "都重视深度连接", "why_fit": "愿意为关系投入时间"}
                },
                "relationship_types": [
                    {"type": "🌿 安静陪伴", "score": 90, "scenario": "慢热同盟"},
                    {"type": "☕ 深聊朋友", "score": 78, "scenario": "偶尔约出来深聊"}
                ]
            },
            {
                "mock_user_id": order[2],
                "rank": 3,
                **_coord(order[2]),  # V1.5: 注入 social 坐标
                "scores": {"total": 75, "token": 80, "energy": 70, "firewall": 82, "interest": 75, "value": 70},
                "explanation": "温柔处理器会帮你把世界的恶意软化。",
                "detailed_analysis": {
                    "energy": {"common_ground": "都需要空间但方式不同", "why_fit": "互补让你体验不同的充电方式"},
                    "social": {"common_ground": "都不喜欢冲突", "why_fit": "沟通成本低"},
                    "value": {"common_ground": "都希望世界更温柔", "why_fit": "价值观底层一致"}
                },
                "relationship_types": [
                    {"type": "☕ 深聊朋友", "score": 80, "scenario": "互相倾诉"},
                    {"type": "🌱 成长伙伴", "score": 70, "scenario": "互相支持"}
                ]
            }
        ]
    }


def _mock_icebreaker(user_profile: dict, mock_user: dict, regenerate: bool = False) -> dict:
    """Mock：AI 破冰话题（基于双方说明书）"""
    main_type = user_profile.get("main_type", "TA")
    mock_name = mock_user.get("name", "TA")
    mock_main = mock_user.get("main_type", "")
    mock_one_liner = mock_user.get("one_liner", "")

    if regenerate:
        # 换一个：换切入角度
        return {
            "icebreakers": [
                {
                    "why": f"换个角度：从你们的{_get_param(user_profile, 'energy')}能量模式切入",
                    "topic_type": "共同点",
                    "content": f"看你的说明书说你也是{main_type}，想问问你最近一次觉得'电量回满'是什么时候？"
                },
                {
                    "why": "从 TA 的兴趣切入（你可能不知道的细节）",
                    "topic_type": "兴趣",
                    "content": f"你 '{mock_one_liner[:20]}...' 这句话很有意思，背后有什么故事吗？"
                },
                {
                    "why": "从价值观切入（深度对话）",
                    "topic_type": "价值观",
                    "content": f"我一直觉得 {mock_main} 的人有一种独特的节奏，你觉得这种节奏是后天学的还是天生的？"
                }
            ]
        }

    return {
        "icebreakers": [
            {
                "why": f"你们都有{_get_param(user_profile, 'firewall')}防火墙，都不擅长主动。所以从一个不需要 TA 主动回应的话题开始",
                "topic_type": "共同点",
                "content": f"看你的说明书说你是{mock_main}，我{main_type}，感觉我们可能都不太擅长主动寒暄。换个方式——你最近有没有发现什么让你'蓄上电'的小事？"
            },
            {
                "why": f"TA 的 {mock_one_liner[:30]}... 这句话很独特，挖一下能打开真实对话",
                "topic_type": "兴趣",
                "content": f"你的说明书上写'{mock_one_liner}'，这句话挺戳我的。你一般在什么状态下会说出这种感觉？"
            },
            {
                "why": "你们都慢热，从对方的主类型切入能避开'在吗'式开场",
                "topic_type": "互补点",
                "content": f"我俩都是慢热型，所以这次厚着脸皮先开口——你最容易被哪种话题点燃？"
            }
        ]
    }


def _mock_relationship(user_profile: dict, mock_user: dict) -> dict:
    """Mock：双人关系说明书"""
    user_main = user_profile.get("main_type", "你")
    mock_main = mock_user.get("main_type", "TA")
    return {
        "match_summary": f"你和 {mock_user.get('name', 'TA')} 的兼容度评分 89 分。两个慢热型的人，但一旦建立信任，会进入深度交流模式。",
        "why_fit": {
            "energy": {
                "you": _get_param(user_profile, "energy"),
                "ta": _get_param(mock_user.get("params", {}), "energy"),
                "common_ground": "你们都是低能量模式，社交消耗能量",
                "why_fit": "你需要独处恢复，而 TA 擅长提供稳定陪伴，不会造成社交压力。你们能各自充电又能在场。"
            },
            "social": {
                "common_ground": "不喜欢强社交，更喜欢深聊；都不太主动；建立关系需要时间",
                "why_fit": "你们可能第一次见面很安静，但第三次见面开始讲人生。不会冷场因为你们都不喜欢尬聊。"
            },
            "value": {
                "common_ground": "重视长期关系；喜欢真实交流；不追求速食社交",
                "why_fit": "价值观一致，能一起走很长的路。短期不会有戏剧性火花，但长期稳定。"
            }
        },
        "possible_relationships": [
            {"type": "☕ 深聊朋友", "score": 92, "scenario": "晚上聊人生和意义"},
            {"type": "🌱 成长伙伴", "score": 78, "scenario": "互相支持各自的成长"},
            {"type": "🌿 安静陪伴", "score": 88, "scenario": "不需要一直聊但心里有对方"}
        ],
        "advice": [
            "不要急着每天聊天。你们都需要空间，强迫社交会让关系早死。",
            "从兴趣和经历开始比尬聊更有效。你们都不擅长客套，那就都别客套。",
            "偶尔分享一个小发现（一首歌、一个想法、一张照片），会增强连接。你们都欣赏真实。"
        ]
    }


def _mock_social_map(user_profile: dict, matches: list) -> dict:
    """Mock：我的同类地图总结（V1.5opt 升级为 AI 观察风格）"""
    main_type = user_profile.get("main_type", "未知")
    high_match = [m for m in matches if m.get("scores", {}).get("total", 0) >= 80]
    energy = _get_param(user_profile, "energy")
    firewall = _get_param(user_profile, "firewall")

    # V1.5opt：根据用户类型动态生成 AI 观察（mock 阶段用模板，深层用 deepseek）
    if "低耗能" in main_type or "慢热" in main_type or "节能" in main_type:
        ai_observation = f"你的社交模式更偏向深度连接，而不是高频互动。目前发现的 {len(matches)} 个同类，都与你在节奏感和关系期待上高度接近。"
    elif "目标" in main_type or "推进" in main_type:
        ai_observation = f"你更看重成长和效率，{len(matches)} 个已发现的同类里，{len(high_match)} 个在目标和行动力上和你同步。"
    elif "幽默" in main_type or "段子" in main_type:
        ai_observation = f"你用幽默处理世界，已发现的 {len(matches)} 个同类里，多数和你一样把吐槽当亲近。"
    else:
        ai_observation = f"你已发现 {len(matches)} 个潜在同类。{len(high_match)} 个与你的契合度超过 80%，节奏和价值观都接近。"

    return {
        "social_dna": {
            "your_type": main_type,
            "energy_profile": energy,
            "firewall_profile": firewall,
            "connect_with": [
                "慢热型（不强迫社交，给彼此空间）",
                "深度交流型（话题深度优先）",
                "长期主义型（重视稳定关系）"
            ],
            "avoid": [
                "强社交型（会消耗你的能量）",
                "速食社交型（和你价值观冲突）"
            ]
        },
        "matches_summary": f"已发现 {len(matches)} 个潜在同类，整体契合度 82%，其中 {len(high_match)} 个高度匹配（≥80%）。",
        "next_step": "挑一个最匹配的同类，用 AI 破冰建议开启第一次对话。",
        # V1.5opt：AI 观察（一句话总结，比 matches_summary 更有温度）
        "ai_observation": ai_observation,
    }


def _mock_start_interview() -> dict:
    """Mock：5 道场景化访谈题（首页 start-interview 用）"""
    return {
        "questions": [
            {
                "question": "周五晚上 11 点，你刚加完班。脑子里第一个冒出来的念头是？",
                "options": [
                    {"text": "终于结束了，关机睡觉", "dim": "能量", "feedback": "独处回血型。电量用完只能靠睡觉补。"},
                    {"text": "想找个人聊聊，但又不知道找谁", "dim": "社交", "feedback": "想被看见但不想主动，你被看见就发光。"},
                    {"text": "打开手机刷半小时再说", "dim": "状态", "feedback": "低能量但不想承认，用刷手机当借口。"},
                    {"text": "打开小红书看别人在干嘛", "dim": "观察", "feedback": "标准观察者模式，先看再决定。"}
                ]
            },
            {
                "question": "朋友临时约你 1 小时后吃饭，你的反应是？",
                "options": [
                    {"text": "看心情。心情好就回，心情差就装死", "dim": "能量", "feedback": "选择性社交，关键看当下状态。"},
                    {"text": "算了不去，累", "dim": "能量", "feedback": "独处回血型。临时约等于社交消耗。"},
                    {"text": "问一句还有谁再决定", "dim": "判断", "feedback": "要预判社交压力再决定。"},
                    {"text": "行，反正闲着也是闲着", "dim": "社交", "feedback": "低防火墙型，容易被叫出去。"}
                ]
            },
            {
                "question": "有人第一次加你微信，你第一反应是？",
                "options": [
                    {"text": "等对方先开口", "dim": "社交", "feedback": "你的防火墙不是拒绝，是观察期。"},
                    {"text": "已读不回，过几天再说", "dim": "防火墙", "feedback": "慢热型典型反应，不是不在意，是在意才慢。"},
                    {"text": "寒暄两句再撤", "dim": "状态", "feedback": "礼貌但保持距离，先用最低成本应付。"},
                    {"text": "看朋友圈判断要不要回", "dim": "判断", "feedback": "数据先于情感，你是数据型人类。"}
                ]
            },
            {
                "question": "你和一个新朋友吃完饭，临走时你的内心活动是？",
                "options": [
                    {"text": "嗯还不错，下次可以再来", "dim": "判断", "feedback": "允许进入第二回合，但还有评估期。"},
                    {"text": "呼，终于可以回家了", "dim": "能量", "feedback": "社交消耗已结算，需要充电。"},
                    {"text": "希望对方下次主动约我", "dim": "关系", "feedback": "你不是不愿意，是希望对方更主动。"},
                    {"text": "下次见面我要换个话题", "dim": "观察", "feedback": "已经在规划下一次对话深度了。"}
                ]
            },
            {
                "question": "半夜 2 点睡不着，你通常在干嘛？",
                "options": [
                    {"text": "刷手机，越刷越睡不着", "dim": "状态", "feedback": "深夜是思绪发散的时间，你被它困住。"},
                    {"text": "想事情，想到第 8 圈还没想明白", "dim": "思考", "feedback": "高 token 消耗型，深夜用来想明白白天不想的事。"},
                    {"text": "看别人的朋友圈", "dim": "观察", "feedback": "深夜是观察他人生活的最佳时段。"},
                    {"text": "听播客或者白噪音", "dim": "充电", "feedback": "用声音把脑子塞满，就不用想了。"}
                ]
            }
        ]
    }


def _mock_generate(answers: list) -> dict:
    """Mock：根据 5 个 answer 生成完整说明书（V1.3 朋友观察版）"""
    # 根据答案推断一些基本特征（简化版）
    has_low_energy = any("能量" in str(a.get("dim", "")) and ("累" in a.get("text", "") or "独处" in a.get("text", "") or "关机" in a.get("text", "")) for a in answers)
    has_high_observe = any("观察" in str(a.get("dim", "")) for a in answers)
    has_slow_warm = any("防火墙" in str(a.get("dim", "")) or "已读不回" in a.get("text", "") for a in answers)

    if has_low_energy and has_slow_warm:
        main_type = "独处续电员"
        one_liner = "你的社交电量和手机一样，5% 的时候才想起充电器"
    elif has_high_observe:
        main_type = "人间观察员"
        one_liner = "你永远在收集别人的数据，但自己不上场"
    else:
        main_type = "慢热型处理器"
        one_liner = "你是一杯温水，不烫不冷，但要时间才能感觉到"

    return {
        "main_type": main_type,
        "tags": ["低耗能高续航", "深度交流型", "观察后发言"],
        "one_liner": one_liner,
        "main_type_reason": "你慢热、节能、不主动。这不是缺点，是操作系统。",
        "stats": {
            "token": "99/100",
            "token_status": "前台休息，后台思考",
            "firewall": "半透明玻璃墙",
            "firewall_status": "看得见你，但想靠近需要时间",
            "energy": "独处回血型",
            "energy_status": "热闹消耗能量，安静恢复电量",
            "permission": "观察者模式",
            "permission_status": "先看看你怎么玩，再决定加入"
        },
        "bug": "明明想被看见，却假装不需要",
        "skill": "能听懂别人没说出口的话",
        "instruction": {
            "start": "别一上来就发长消息，先用表情包测试水温",
            "interact": "少问'在吗'，直接抛一个话题",
            "charging": "给 TA 独处的时间，不要追问 '你为什么不说话'",
            "forbidden": "不要强迫 TA 立刻表态，TA 需要后台运算"
        },
        "others_view": {
            "first_impression": "高冷，客气，保持距离",
            "familiar": "其实很会接话，熟了话还不少",
            "miss_you": "走了才想找 TA 聊天"
        },
        "share_quotes": [
            "你不是冷漠，你只是把热情算得清清楚楚",
            "低耗能高续航，是你的活法",
            "慢热不是延迟，是你的防伪标志"
        ]
    }


def _mock_regenerate(instruction: dict, perspective: str = "close_friend") -> dict:
    """Mock：换视角重生成（基于原始 instruction + 视角）"""
    perspective_names = {
        "close_friend": "🤝 老朋友观察版",
        "bestie": "👯 闺蜜毒舌版",
        "first_meet": "👋 第一次见面版",
        "ai_analyst": "🤖 AI 分析师版"
    }
    pname = perspective_names.get(perspective, "🤝 老朋友观察版")

    # 保留原始数据，修改视角相关字段
    new_data = dict(instruction)  # 浅拷贝
    if perspective == "bestie":
        new_data["bug"] = "嘴硬心软，明明想你了不说"
        new_data["one_liner"] = "你的嘴和心隔了一个世纪"
        new_data["share_quotes"] = [
            "闺蜜就是：骂你最多，但护你最狠",
            "你说不要，其实是要",
            "你的嘴硬程度比你的 bug 还硬"
        ]
    elif perspective == "first_meet":
        new_data["bug"] = "第一次见会给人感觉太冷"
        new_data["one_liner"] = "你的初次见面像开了省电模式"
        new_data["share_quotes"] = [
            "第一次见面别期待 TA 话多",
            "TA 不是高冷，是还没开机",
            "熟了以后，TA 比谁都话多"
        ]
    elif perspective == "ai_analyst":
        new_data["bug"] = "认知资源分配不均 - 全部用在观察上"
        new_data["one_liner"] = "你是一个 24 小时运转的传感器"
        new_data["share_quotes"] = [
            "你的 CPU 主要跑在'观察'这个进程上",
            "你不是在社交，你是在做田野调查",
            "你的输入 > 输出 10 倍，迟早需要 dump"
        ]
    else:  # close_friend
        new_data["bug"] = "明明最懂别人，却不懂自己"
        new_data["one_liner"] = "你像一本人肉《读心术》，但你看不到自己的封面"
        new_data["share_quotes"] = [
            "认识 8 年，我最怕的不是你不理我，是你不相信自己",
            "你的所有'算了'后面都有个没说出口的'但是'",
            "你不是没脾气，是把脾气藏在了后台"
        ]

    # 保留主数据
    new_data["main_type"] = instruction.get("main_type", new_data.get("main_type"))
    new_data["tags"] = instruction.get("tags", new_data.get("tags"))
    new_data["stats"] = instruction.get("stats", new_data.get("stats"))
    new_data["main_type_reason"] = instruction.get("main_type_reason", new_data.get("main_type_reason"))
    new_data["others_view"] = instruction.get("others_view", {
        "first_impression": f"{pname}视角下的第一印象",
        "familiar": "熟了以后",
        "miss_you": "离开以后"
    })
    new_data["instruction"] = instruction.get("instruction", new_data.get("instruction", {}))

    return new_data


def _mock_fusion(user_profile: dict, reviews: list) -> dict:
    """Mock：AI 融合总结（朋友视角 + AI 原始）"""
    main_type = user_profile.get("main_type", "你")
    review_count = len(reviews)
    review_summary = "、".join([
        r.get("nickname", "朋友") + ":" + r.get("comment", "")[:20]
        for r in reviews[:3]
    ]) or f"{review_count} 位朋友的观察"

    return {
        "v1_ai_initial": f"AI 最初看到的是{main_type}，一个标准的低耗能高续航人类，靠独处回血，靠观察世界。",
        "v1_friend_observations": f"朋友们补充说：{review_summary}。这些是 AI 算法看不出来的部分。",
        "v2_fusion_summary": f"AI 的分析（{main_type}，慢热节能）和朋友们的观察（你其实很容易被打动，只是藏得深）融合后，更立体的你是：表面是低耗能处理器，底下是个希望被看见但不愿主动的人。",
        "new_insight": "你比你自己以为的更需要被主动关心。"
    }


def _get_param(profile: dict, key: str) -> str:
    """从 profile 提取运行参数（适配新老 schema）"""
    if not profile:
        return "未知"
    # 新 schema: profile.stats.{key}
    stats = profile.get("stats", {})
    if stats.get(key):
        return stats.get(key)
    # 老 schema: profile.params.{key} 或 profile.running_params.{key}
    params = profile.get("params", profile.get("running_params", {}))
    if isinstance(params, dict) and params.get(key):
        return params.get(key)
    return "未知"


# ============================================================
# 统一调用入口
# ============================================================

def ai_call(
    scenario: str,                # 'summon' | 'icebreaker' | 'relationship' | 'social_map'
    user_profile: dict,
    mock_user: Optional[dict] = None,
    mock_user_summaries: Optional[list] = None,
    matches: Optional[list] = None,
    extra: Optional[dict] = None,
    prompt: Optional[str] = None,
    messages: Optional[list] = None,
    temperature: float = 0.85,
    max_tokens: int = 2000,
    max_retry: int = 2,
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    统一 AI 调用入口

    返回 dict 包含：
        ok: bool
        data: dict (AI 返回的 JSON)
        elapsed: float
        error: str
        mode: 'mock' | 'deepseek'
    """
    t0 = time.time()

    # 选模式
    if AI_MODE == "mock":
        return _call_mock(scenario, user_profile, mock_user, mock_user_summaries, matches, extra, t0)

    # deepseek 模式
    admin_key = get_admin_api_key()
    if not admin_key:
        return {
            "ok": False,
            "error": "AI 正在休息，请稍后再试（管理员 Key 未配置）",
            "code": "admin_key_missing",
            "mode": "deepseek",
            "elapsed": 0,
        }

    return _call_deepseek(scenario, admin_key, messages, prompt, t0, temperature, max_tokens, max_retry, timeout)


def _call_mock(scenario, user_profile, mock_user, mock_user_summaries, matches, extra, t0):
    """Mock 模式：直接返回预设数据"""
    if scenario == "summon":
        data = _mock_summon(user_profile, mock_user_summaries or [])
    elif scenario == "icebreaker":
        data = _mock_icebreaker(
            user_profile,
            mock_user,
            regenerate=bool(extra and extra.get("regenerate"))
        )
    elif scenario == "relationship":
        data = _mock_relationship(user_profile, mock_user)
    elif scenario == "social_map":
        data = _mock_social_map(user_profile, matches or [])
    elif scenario == "start_interview":
        data = _mock_start_interview()
    elif scenario == "generate":
        data = _mock_generate((extra or {}).get("answers", []))
    elif scenario == "regenerate":
        data = _mock_regenerate(
            (extra or {}).get("instruction", {}),
            (extra or {}).get("perspective", "close_friend")
        )
    elif scenario == "fusion":
        data = _mock_fusion(user_profile, mock_user_summaries or [])
    else:
        return {
            "ok": False,
            "error": f"未知 scenario: {scenario}",
            "mode": "mock",
            "elapsed": 0,
        }

    # Mock 也加一点延迟，更真实
    time.sleep(0.5)

    return {
        "ok": True,
        "data": data,
        "elapsed": round(time.time() - t0, 2),
        "mode": "mock",
    }


def _call_deepseek(scenario, api_key, messages, prompt, t0, temperature, max_tokens, max_retry, timeout):
    """DeepSeek 模式：调真实 API"""
    if not messages:
        messages = [{"role": "user", "content": prompt or "请根据用户信息生成结果"}]

    # 强制保证 DeepSeek json_object 模式校验通过
    combined_text = " ".join(
        m.get("content", "")
        for m in messages
    )

    if "json" not in combined_text.lower():
        messages = [
            {
                "role": "system",
                "content": "请严格按照 json 格式输出结果。"
            }
        ] + messages

    last_error = None
    for attempt in range(max_retry):
        try:
            payload = {
                "model": DEEPSEEK_MODEL,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": temperature,
                "top_p": 0.9,
                "max_tokens": max_tokens,
                "stream": False,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=timeout)
            elapsed = round(time.time() - t0, 2)

            if resp.status_code != 200:
                return {
                    "ok": False,
                    "error": f"DeepSeek 返回 {resp.status_code}: {resp.text[:300]}",
                    "elapsed": elapsed,
                    "mode": "deepseek",
                }

            result = resp.json()
            content = result["choices"][0]["message"]["content"]

            try:
                data = json.loads(content)
                return {
                    "ok": True,
                    "data": data,
                    "elapsed": elapsed,
                    "mode": "deepseek",
                }
            except json.JSONDecodeError as e:
                last_error = f"JSON 解析失败: {e}"
                continue

        except requests.exceptions.Timeout:
            last_error = "DeepSeek 调用超时"
        except Exception as e:
            last_error = f"调用异常: {e}"

    return {
        "ok": False,
        "error": last_error or "未知错误",
        "elapsed": round(time.time() - t0, 2),
        "mode": "deepseek",
    }


# ============================================================
# 工具函数
# ============================================================
def get_mode() -> str:
    """返回当前 AI 模式（用于前端展示）"""
    return AI_MODE


def is_mock() -> bool:
    """是否 mock 模式"""
    return AI_MODE == "mock"
