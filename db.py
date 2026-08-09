"""
朋友说明书 AI - 数据存储 (V1.4)
SQLite 轻量封装
"""
import sqlite3
import json
import uuid
import time
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'friend_manual.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表（V2.0：加 report_id + fusion_summaries）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE NOT NULL,
        share_id TEXT UNIQUE NOT NULL,
        report_id INTEGER,                       -- V2.0：用户自己的报告 ID（数字）
        profile_json TEXT NOT NULL,
        answers_json TEXT,
        current_perspective TEXT,
        created_time INTEGER NOT NULL
    )''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_share_id ON users(share_id)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_user_id ON users(user_id)''')
    # V2.0：老表升级（先加列，再建索引）
    _ensure_column(c, 'users', 'report_id', 'INTEGER')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_report_id ON users(report_id)''')
    # V1.4 P1 预留：兼容度关系表
    c.execute('''CREATE TABLE IF NOT EXISTS friendships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_a TEXT NOT NULL,
        user_b TEXT NOT NULL,
        compatibility_json TEXT,
        created_time INTEGER NOT NULL,
        UNIQUE(user_a, user_b)
    )''')
    # V1.5：朋友评价表
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_user_name TEXT NOT NULL,
        target_user_id TEXT NOT NULL,
        share_id TEXT NOT NULL,
        choice TEXT,                              -- V2.0：可空（只有 comment 也能提交）
        comment TEXT,
        created_time INTEGER NOT NULL
    )''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_review_share_id ON reviews(share_id)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_review_created ON reviews(created_time DESC)''')
    # V2.0 迁移：把老 reviews.choice 从 NOT NULL 改成 NULL
    _migrate_reviews_choice_nullable(c)
    # V2.0：AI 融合总结缓存
    c.execute('''CREATE TABLE IF NOT EXISTS fusion_summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL UNIQUE,
        summary_json TEXT NOT NULL,
        review_count INTEGER NOT NULL,
        created_time INTEGER NOT NULL,
        updated_time INTEGER NOT NULL
    )''')
    # V1.7：召唤同类匹配结果
    c.execute('''CREATE TABLE IF NOT EXISTS summon_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        mock_user_id TEXT NOT NULL,
        rank INTEGER NOT NULL,                      -- 1/2/3 名次
        score_total REAL NOT NULL,                  -- 总分 0-100
        score_token REAL,                           -- Token 兼容
        score_energy REAL,                          -- 能量兼容
        score_firewall REAL,                        -- 防火墙兼容
        score_interest REAL,                        -- 兴趣兼容
        score_value REAL,                           -- 价值观兼容
        ai_explanation TEXT,                        -- AI 解释为什么匹配
        relationship_types_json TEXT,               -- 关系类型 [{type, score, scenario}, ...]
        created_time INTEGER NOT NULL,
        UNIQUE(report_id, mock_user_id)
    )''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_summon_report ON summon_matches(report_id, rank)''')
    # V1.8：升级 summon_matches 表加 detailed_analysis_json 列（兼容老 DB）
    _ensure_column(c, 'summon_matches', 'detailed_analysis_json', 'TEXT')
    # V1.8.1：双人关系说明书（关系资产沉淀）
    c.execute('''CREATE TABLE IF NOT EXISTS relationships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        mock_user_id TEXT NOT NULL,
        match_score INTEGER,
        relationship_json TEXT NOT NULL,
        has_report INTEGER DEFAULT 0,
        created_time INTEGER NOT NULL,
        updated_time INTEGER NOT NULL,
        UNIQUE(report_id, mock_user_id)
    )''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_relationship_report ON relationships(report_id, created_time DESC)''')
    # V1.7：破冰话题
    c.execute('''CREATE TABLE IF NOT EXISTS summon_icebreakers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        mock_user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        created_time INTEGER NOT NULL,
        UNIQUE(report_id, mock_user_id)
    )''')
    # V1.5：限流记录（按 IP + 端点 + 日期 统计）
    c.execute('''CREATE TABLE IF NOT EXISTS rate_limits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT NOT NULL,
        endpoint TEXT NOT NULL,                -- summary / match / chat
        date TEXT NOT NULL,                    -- YYYY-MM-DD
        count INTEGER NOT NULL DEFAULT 0,
        UNIQUE(ip, endpoint, date)
    )''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_rate_lookup ON rate_limits(ip, endpoint, date)''')
    conn.commit()
    conn.close()


def _migrate_reviews_choice_nullable(c):
    """V2.0 迁移：把 reviews.choice 从 NOT NULL 改成 NULL（重建表）"""
    c.execute("PRAGMA table_info(reviews)")
    cols = {row[1]: row[3] for row in c.fetchall()}  # name -> notnull (0 或 1)
    if not cols:
        return  # 表还没建
    if cols.get('choice') == 0:
        return  # 已经可空

    # 重建表
    c.execute('''CREATE TABLE reviews_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_user_name TEXT NOT NULL,
        target_user_id TEXT NOT NULL,
        share_id TEXT NOT NULL,
        choice TEXT,
        comment TEXT,
        created_time INTEGER NOT NULL
    )''')
    c.execute('INSERT INTO reviews_new SELECT * FROM reviews')
    c.execute('DROP TABLE reviews')
    c.execute('ALTER TABLE reviews_new RENAME TO reviews')
    c.execute('CREATE INDEX IF NOT EXISTS idx_review_share_id ON reviews(share_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_review_created ON reviews(created_time DESC)')


def _ensure_column(c, table, column, col_type):
    """SQLite ALTER TABLE 加列（如果不存在）"""
    c.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in c.fetchall()]
    if column not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def upgrade_db():
    """V2.0 升级：给老 users 表加 report_id 字段，并补一个 report_id"""
    conn = get_conn()
    c = conn.cursor()
    _ensure_column(c, 'users', 'report_id', 'INTEGER')
    conn.commit()

    # 给所有 report_id IS NULL 的老用户补一个 report_id（用自增模拟）
    c.execute('SELECT user_id FROM users WHERE report_id IS NULL ORDER BY id')
    rows = c.fetchall()
    next_id = _next_report_id(c)
    for row in rows:
        c.execute('UPDATE users SET report_id = ? WHERE user_id = ?', (next_id, row['user_id']))
        next_id += 1
    conn.commit()
    conn.close()


def _next_report_id(c):
    """生成下一个 report_id（用时间戳 + 随机数，保证唯一且易记）"""
    import random
    # 6 位数字（100000-999999）
    while True:
        rid = random.randint(100000, 999999)
        c.execute('SELECT 1 FROM users WHERE report_id = ?', (rid,))
        if not c.fetchone():
            return rid


def generate_short_id(length=8):
    """生成易记的随机 ID（8 位）"""
    # 用 uuid4 拿 hex 字符（无 0/o/1/l 等易混字符问题，但可读性稍差）
    # 这里用 uuid hex 截断，简单且足够
    return uuid.uuid4().hex[:length]


def save_user(profile, answers=None, perspective=None):
    """保存用户说明书

    返回 (user_id, share_id, report_id)
    """
    user_id = 'u_' + uuid.uuid4().hex[:12]
    share_id = generate_short_id(8)
    report_id = None

    # 防止 share_id 极小概率冲突，重试一次
    conn = get_conn()
    c = conn.cursor()
    for _ in range(3):
        try:
            report_id = _next_report_id(c)
            c.execute('''INSERT INTO users
                (user_id, share_id, report_id, profile_json, answers_json, current_perspective, created_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (user_id, share_id, report_id,
                 json.dumps(profile, ensure_ascii=False),
                 json.dumps(answers, ensure_ascii=False) if answers else None,
                 perspective,
                 int(time.time())))
            conn.commit()
            break
        except sqlite3.IntegrityError:
            share_id = generate_short_id(8)
    conn.close()

    return user_id, share_id, report_id


def get_user_by_report_id(report_id):
    """通过 report_id 获取用户（V2.0 新增）

    返回 {'user_id', 'share_id', 'profile', 'answers', 'current_perspective', 'created_time'} 或 None
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT user_id, share_id, profile_json, answers_json, current_perspective, created_time
                FROM users WHERE report_id = ?''', (report_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'user_id': row['user_id'],
        'share_id': row['share_id'],
        'report_id': report_id,
        'profile': json.loads(row['profile_json']),
        'answers': json.loads(row['answers_json']) if row['answers_json'] else None,
        'current_perspective': row['current_perspective'],
        'created_time': row['created_time']
    }


def get_user_by_share_id(share_id):
    """通过 share_id 获取用户说明书

    返回 {'user_id', 'report_id', 'profile', 'current_perspective', 'created_time', 'answers'} 或 None
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT user_id, report_id, profile_json, answers_json, current_perspective, created_time
                FROM users WHERE share_id = ?''', (share_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'user_id': row['user_id'],
        'report_id': row['report_id'],
        'profile': json.loads(row['profile_json']),
        'answers': json.loads(row['answers_json']) if row['answers_json'] else None,
        'current_perspective': row['current_perspective'],
        'created_time': row['created_time']
    }


def update_user_perspective(user_id, perspective):
    """更新用户当前视角（V1.4 - 用户切视角后保存）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET current_perspective = ? WHERE user_id = ?',
              (perspective, user_id))
    conn.commit()
    conn.close()


def get_user_count():
    """统计用户数（运营用）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    n = c.fetchone()[0]
    conn.close()
    return n


# ============================================================
# V1.5：朋友评价
# ============================================================

# 评价选项常量
CHOICE_ACCURATE = 'accurate'        # 🔥 太准了
CHOICE_PARTIAL = 'partial'           # 🤔 有点像但少了点
CHOICE_MISUNDERSTAND = 'misunderstand'  # 😂 AI 误会了

CHOICE_LABELS = {
    CHOICE_ACCURATE: ('🔥', '太准了，被 AI 偷听了'),
    CHOICE_PARTIAL: ('🤔', '有点像，但少了点东西'),
    CHOICE_MISUNDERSTAND: ('😂', 'AI 误会 TA 了'),
}


def save_review(review_user_name, target_user_id, share_id, choice=None, comment=None):
    """保存朋友评价（V2.0：choice 可空，只评论也能提交）"""
    # V2.0 校验：choice 和 comment 至少有一个
    choice = (choice or '').strip() or None
    comment = (comment or '').strip() or None
    if choice is None and comment is None:
        raise ValueError("choice 和 comment 至少要有一个")

    # 校验 choice 必须是合法值（如果有）
    if choice is not None and choice not in CHOICE_LABELS:
        raise ValueError(f"choice 必须是 {list(CHOICE_LABELS.keys())} 之一")

    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT INTO reviews
        (review_user_name, target_user_id, share_id, choice, comment, created_time)
        VALUES (?, ?, ?, ?, ?, ?)''',
        ((review_user_name or '匿名朋友').strip()[:20],
         target_user_id,
         share_id,
         choice,
         comment[:500] if comment else None,
         int(time.time())))
    conn.commit()
    review_id = c.lastrowid
    conn.close()
    return review_id


def get_reviews_by_share_id(share_id):
    """获取一份说明书的所有朋友评价（按时间倒序）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT id, review_user_name, choice, comment, created_time
                FROM reviews WHERE share_id = ? ORDER BY created_time DESC''',
              (share_id,))
    rows = c.fetchall()
    conn.close()

    return [{
        'id': r['id'],
        'review_user_name': r['review_user_name'],
        'choice': r['choice'],
        'comment': r['comment'] or '',
        'created_time': r['created_time']
    } for r in rows]


def get_review_stats(share_id):
    """统计评价分布"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT choice, COUNT(*) as cnt FROM reviews
                WHERE share_id = ? GROUP BY choice''', (share_id,))
    rows = c.fetchall()
    conn.close()

    stats = {CHOICE_ACCURATE: 0, CHOICE_PARTIAL: 0, CHOICE_MISUNDERSTAND: 0}
    for r in rows:
        stats[r['choice']] = r['cnt']
    return stats


# ============================================================
# V2.0：AI 融合总结（手动触发 + 缓存）
# ============================================================

def save_fusion_summary(report_id, summary_json, review_count):
    """保存 AI 融合总结（覆盖更新）"""
    conn = get_conn()
    c = conn.cursor()
    now = int(time.time())
    # 用 INSERT OR REPLACE 覆盖
    c.execute('''INSERT OR REPLACE INTO fusion_summaries
        (report_id, summary_json, review_count, created_time, updated_time)
        VALUES (?, ?, ?,
                COALESCE((SELECT created_time FROM fusion_summaries WHERE report_id = ?), ?),
                ?)''',
        (report_id, json.dumps(summary_json, ensure_ascii=False), review_count,
         report_id, now, now))
    conn.commit()
    conn.close()


def get_fusion_summary(report_id):
    """获取 AI 融合总结（V2.0）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT summary_json, review_count, created_time, updated_time
                FROM fusion_summaries WHERE report_id = ?''', (report_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'summary': json.loads(row['summary_json']),
        'review_count': row['review_count'],
        'created_time': row['created_time'],
        'updated_time': row['updated_time']
    }


# ============================================================
# V1.7：召唤同类（匹配结果 + 破冰话题）
# ============================================================

def save_summon_match(report_id, mock_user_id, rank, scores, explanation, relationship_types, detailed_analysis=None):
    """保存一条匹配结果（V1.7）

    scores: dict {token, energy, firewall, interest, value, total}
    relationship_types: list [{type, score, scenario}, ...]
    detailed_analysis: V1.8 dict {energy, social, value} -> {common_ground, why_fit}
    """
    conn = get_conn()
    c = conn.cursor()
    now = int(time.time())
    c.execute('''INSERT OR REPLACE INTO summon_matches
        (report_id, mock_user_id, rank, score_total, score_token, score_energy,
         score_firewall, score_interest, score_value, ai_explanation,
         relationship_types_json, detailed_analysis_json, created_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (report_id, mock_user_id, rank,
         scores['total'], scores.get('token', 0), scores.get('energy', 0),
         scores.get('firewall', 0), scores.get('interest', 0), scores.get('value', 0),
         explanation,
         json.dumps(relationship_types, ensure_ascii=False),
         json.dumps(detailed_analysis or {}, ensure_ascii=False),
         now))
    conn.commit()
    conn.close()


def clear_summon_matches(report_id):
    """清空某个 report_id 的所有匹配（重新召唤时用）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM summon_matches WHERE report_id = ?', (report_id,))
    c.execute('DELETE FROM summon_icebreakers WHERE report_id = ?', (report_id,))
    conn.commit()
    conn.close()


def get_summon_matches(report_id):
    """获取某 report 的所有匹配（按 rank 排序）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT mock_user_id, rank, score_total, score_token, score_energy,
                score_firewall, score_interest, score_value, ai_explanation,
                relationship_types_json, detailed_analysis_json, created_time
                FROM summon_matches WHERE report_id = ?
                ORDER BY rank ASC''', (report_id,))
    rows = c.fetchall()
    conn.close()
    results = []
    for r in rows:
        results.append({
            'mock_user_id': r['mock_user_id'],
            'rank': r['rank'],
            'scores': {
                'total': r['score_total'],
                'token': r['score_token'],
                'energy': r['score_energy'],
                'firewall': r['score_firewall'],
                'interest': r['score_interest'],
                'value': r['score_value'],
            },
            'explanation': r['ai_explanation'],
            'relationship_types': json.loads(r['relationship_types_json']) if r['relationship_types_json'] else [],
            'detailed_analysis': json.loads(r['detailed_analysis_json']) if r['detailed_analysis_json'] else {},
            'created_time': r['created_time'],
        })
    return results


def save_icebreaker(report_id, mock_user_id, content):
    """保存破冰话题（V1.7）"""
    conn = get_conn()
    c = conn.cursor()
    now = int(time.time())
    c.execute('''INSERT OR REPLACE INTO summon_icebreakers
        (report_id, mock_user_id, content, created_time)
        VALUES (?, ?, ?, ?)''',
        (report_id, mock_user_id, content, now))
    conn.commit()
    conn.close()


def get_icebreaker(report_id, mock_user_id):
    """获取破冰话题"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT content, created_time FROM summon_icebreakers
                WHERE report_id = ? AND mock_user_id = ?''', (report_id, mock_user_id))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {'content': row['content'], 'created_time': row['created_time']}


# ============================================================
# V1.8.1：双人关系说明书（关系资产沉淀）
# ============================================================

def save_relationship(report_id, mock_user_id, relationship_analysis, match_score=None, has_report=True):
    """保存双人关系说明书（V1.8.1）

    relationship_analysis: dict {match_summary, why_fit, possible_relationships, advice}
    """
    conn = get_conn()
    c = conn.cursor()
    now = int(time.time())
    c.execute('''INSERT OR REPLACE INTO relationships
        (report_id, mock_user_id, match_score, relationship_json, has_report, created_time, updated_time)
        VALUES (?, ?, ?, ?, ?,
                COALESCE((SELECT created_time FROM relationships WHERE report_id = ? AND mock_user_id = ?), ?),
                ?)''',
        (report_id, mock_user_id, match_score,
         json.dumps(relationship_analysis, ensure_ascii=False),
         1 if has_report else 0,
         report_id, mock_user_id, now, now))
    conn.commit()
    conn.close()


def get_relationship(report_id, mock_user_id):
    """获取双人关系说明书"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT match_score, relationship_json, has_report, created_time, updated_time
                FROM relationships WHERE report_id = ? AND mock_user_id = ?''',
                (report_id, mock_user_id))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'match_score': row['match_score'],
        'analysis': json.loads(row['relationship_json']),
        'has_report': bool(row['has_report']),
        'created_time': row['created_time'],
        'updated_time': row['updated_time'],
    }


def get_all_relationships(report_id):
    """获取某 report 的所有关系（按 updated_time 倒序）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT mock_user_id, match_score, relationship_json, updated_time
                FROM relationships WHERE report_id = ?
                ORDER BY updated_time DESC''', (report_id,))
    rows = c.fetchall()
    conn.close()
    return [
        {
            'mock_user_id': r['mock_user_id'],
            'match_score': r['match_score'],
            'analysis': json.loads(r['relationship_json']),
            'updated_time': r['updated_time'],
        }
        for r in rows
    ]


# ============================================================
# V1.5：限流（按 IP + endpoint + 日期 统计）
# ============================================================

def _today_str() -> str:
    """返回 YYYY-MM-DD（用本地时间，公网部署可改成 UTC）"""
    import datetime
    return datetime.date.today().isoformat()


def get_rate_limit_count(ip: str, endpoint: str) -> int:
    """查询某 IP 当天某端点已用次数"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT count FROM rate_limits
                WHERE ip = ? AND endpoint = ? AND date = ?''',
              (ip, endpoint, _today_str()))
    row = c.fetchone()
    conn.close()
    return row['count'] if row else 0


def increment_rate_limit(ip: str, endpoint: str) -> int:
    """自增并返回最新次数（用于拦截后立即 +1）"""
    conn = get_conn()
    c = conn.cursor()
    today = _today_str()
    c.execute('''INSERT INTO rate_limits (ip, endpoint, date, count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(ip, endpoint, date)
                DO UPDATE SET count = count + 1''',
              (ip, endpoint, today))
    conn.commit()
    c.execute('''SELECT count FROM rate_limits
                WHERE ip = ? AND endpoint = ? AND date = ?''',
              (ip, endpoint, today))
    row = c.fetchone()
    conn.close()
    return row['count'] if row else 1
