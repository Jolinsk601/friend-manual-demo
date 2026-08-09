#!/usr/bin/env python3
"""
朋友说明书 AI - 预编译 Tailwind CSS 生成器
覆盖项目里实际用到的所有 class (168 个)
完全脱离 tailwind.js 运行时
"""
import re

# ============== 设计 token ==============
SPACING = {
    '0': '0px', '0.5': '0.125rem', '1': '0.25rem', '1.5': '0.375rem',
    '2': '0.5rem', '2.5': '0.625rem', '3': '0.75rem', '3.5': '0.875rem',
    '4': '1rem', '5': '1.25rem', '6': '1.5rem', '7': '1.75rem',
    '8': '2rem', '9': '2.25rem', '10': '2.5rem', '11': '2.75rem',
    '12': '3rem', '14': '3.5rem', '16': '4rem', '20': '5rem',
    '24': '6rem', '28': '7rem', '32': '8rem', '36': '9rem',
    '40': '10rem', '44': '11rem', '48': '12rem', '52': '13rem',
    '56': '14rem', '60': '15rem', '64': '16rem', '72': '18rem',
    '80': '20rem', '96': '24rem',
}

COLORS = {
    'white': '#ffffff',
    'black': '#000000',
    'transparent': 'transparent',
    'gray': {200: '#e5e7eb', 300: '#d1d5db', 400: '#9ca3af', 500: '#6b7280', 600: '#4b5563'},
    'purple': {100: '#f3e8ff', 200: '#e9d5ff', 300: '#d8b4fe', 400: '#c084fc',
               500: '#a855f7', 600: '#9333ea'},
    'pink': {500: '#ec4899'},
    'blue': {300: '#93c5fd', 500: '#3b82f6'},
    'red': {300: '#fca5a5'},
    'yellow': {300: '#fde047', 400: '#facc15', 500: '#eab308'},
    'orange': {300: '#fdba74', 400: '#fb923c'},
}

FONT_SIZE = {
    'xs': ('0.75rem', '1rem'),
    'sm': ('0.875rem', '1.25rem'),
    'base': ('1rem', '1.5rem'),
    'lg': ('1.125rem', '1.75rem'),
    'xl': ('1.25rem', '1.75rem'),
    '2xl': ('1.5rem', '2rem'),
    '3xl': ('1.875rem', '2.25rem'),
    '4xl': ('2.25rem', '2.5rem'),
    '5xl': ('3rem', '1'),
    '6xl': ('3.75rem', '1'),
    '7xl': ('4.5rem', '1'),
}

LINE_HEIGHT = {
    'none': '1', 'tight': '1.25', 'snug': '1.375', 'normal': '1.5',
    'relaxed': '1.625', 'loose': '2',
}

TRACKING = {
    'tighter': '-0.05em', 'tight': '-0.025em', 'normal': '0em',
    'wide': '0.025em', 'wider': '0.05em', 'widest': '0.1em',
}

RADIUS = {
    'sm': '0.125rem', 'DEFAULT': '0.25rem', 'md': '0.375rem',
    'lg': '0.5rem', 'xl': '0.75rem', '2xl': '1rem', '3xl': '1.5rem',
    'full': '9999px',
}

# ============== CSS 容器 ==============
css_rules = []

def emit(css):
    css_rules.append(css)

# ============== 1. 基础 reset 和 body ==============
emit("""
*, *::before, *::after { box-sizing: border-box; }
html { line-height: 1.5; -webkit-text-size-adjust: 100%; tab-size: 4; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #16213e 100%);
    min-height: 100vh;
    color: #eaeaea;
    margin: 0;
    -webkit-font-smoothing: antialiased;
}
h1, h2, h3, h4, h5, h6, p { margin: 0; }
button { cursor: pointer; background: transparent; border: 0; color: inherit; font: inherit; }
input, textarea { font: inherit; color: inherit; }
a { color: inherit; text-decoration: inherit; }
img, svg { display: block; vertical-align: middle; max-width: 100%; }
""")

# ============== 2. Spacing: padding / margin ==============
# padding
for k, v in SPACING.items():
    emit(f".p-{k} {{ padding: {v}; }}")
    emit(f".px-{k} {{ padding-left: {v}; padding-right: {v}; }}")
    emit(f".py-{k} {{ padding-top: {v}; padding-bottom: {v}; }}")
    emit(f".pt-{k} {{ padding-top: {v}; }}")
    emit(f".pb-{k} {{ padding-bottom: {v}; }}")
    emit(f".pl-{k} {{ padding-left: {v}; }}")
    emit(f".pr-{k} {{ padding-right: {v}; }}")
# margin (with negative support)
for k, v in SPACING.items():
    emit(f".m-{k} {{ margin: {v}; }}")
    emit(f".mx-{k} {{ margin-left: {v}; margin-right: {v}; }}")
    if k != '0':
        emit(f".my-{k} {{ margin-top: {v}; margin-bottom: {v}; }}")
    emit(f".mt-{k} {{ margin-top: {v}; }}")
    emit(f".mb-{k} {{ margin-bottom: {v}; }}")
    emit(f".ml-{k} {{ margin-left: {v}; }}")
    emit(f".mr-{k} {{ margin-right: {v}; }}")
# mx-auto 特殊值（不在 spacing scale 里）
emit(".mx-auto { margin-left: auto; margin-right: auto; }")
emit(".my-auto { margin-top: auto; margin-bottom: auto; }")
# ml-auto / mr-auto 单边 auto
emit(".ml-auto { margin-left: auto; }")
emit(".mr-auto { margin-right: auto; }")
# space-y-N
for k, v in SPACING.items():
    if k != '0':
        emit(f".space-y-{k} > * + * {{ margin-top: {v}; }}")

# ============== 3. Typography ==============
for k, (size, lh) in FONT_SIZE.items():
    emit(f".text-{k} {{ font-size: {size}; line-height: {lh}; }}")
emit(".font-bold { font-weight: 700; }")
emit(".font-semibold { font-weight: 600; }")
emit(".font-medium { font-weight: 500; }")
emit(".font-mono { font-family: ui-monospace, SFMono-Regular, \"SF Mono\", Menlo, monospace; }")
for k, v in LINE_HEIGHT.items():
    emit(f".leading-{k} {{ line-height: {v}; }}")
for k, v in TRACKING.items():
    emit(f".tracking-{k} {{ letter-spacing: {v}; }}")
emit(".italic { font-style: italic; }")
emit(".text-center { text-align: center; }")
emit(".text-left { text-align: left; }")
emit(".text-right { text-align: right; }")

# ============== 4. Colors: text / bg / border / placeholder ==============
def get_color(spec):
    """解析 color/N 或 color/N% 形式"""
    if spec == 'transparent':
        return 'transparent'
    if '/' in spec:
        name, alpha = spec.split('/')
        if name == 'white':
            r, g, b = 255, 255, 255
        elif name == 'black':
            r, g, b = 0, 0, 0
        else:
            # 处理 'purple-500/20'
            parts = name.split('-')
            color_name = parts[0]
            color_num = int(parts[1])
            hex_color = COLORS[color_name][color_num]
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        a = int(alpha) / 100
        return f"rgba({r}, {g}, {b}, {a})"
    if '-' in spec:
        parts = spec.split('-')
        if len(parts) == 2 and parts[1].isdigit():
            return COLORS[parts[0]][int(parts[1])]
    return COLORS.get(spec, spec)

# text color: text-purple-400, text-gray-300, text-white, text-purple-500/20
text_colors = ['white', 'black', 'gray-200', 'gray-300', 'gray-400', 'gray-500', 'gray-600',
               'purple-100', 'purple-200', 'purple-300', 'purple-400', 'purple-500',
               'blue-300', 'red-300', 'yellow-300']
for c in text_colors:
    color_val = get_color(c)
    emit(f".text-{c} {{ color: {color_val}; }}")

# bg color
bg_colors = ['white/5', 'white/10', 'white/15', 'white/20', 'black/30',
             'purple-400', 'purple-500/10', 'purple-500/20', 'purple-500/30', 'purple-500/50',
             'blue-500/20', 'yellow-500/20', 'yellow-400/50', 'orange-400/50',
             'transparent']
for c in bg_colors:
    color_val = get_color(c)
    cls = c.replace('/', '\\/')
    emit(f".bg-{cls} {{ background-color: {color_val}; }}")

# border color
border_colors = ['white/5', 'white/10', 'white/15', 'white/20', 'purple-400/30', 'purple-400/50',
                 'orange-400/50', 'yellow-400/50']
for c in border_colors:
    color_val = get_color(c)
    cls = c.replace('/', '\\/')
    emit(f".border-{cls} {{ border-color: {color_val}; }}")

# placeholder color
for c in ['gray-500', 'gray-600']:
    color_val = get_color(c)
    emit(f".placeholder-{c}::placeholder {{ color: {color_val}; opacity: 1; }}")

# ============== 5. Size ==============
# width
width_sizes = {'full': '100%', 'auto': 'auto', 'screen': '100vw',
               '2': SPACING['2'], '8': SPACING['8']}
for k, v in width_sizes.items():
    emit(f".w-{k} {{ width: {v}; }}")
emit(".w-2 { width: 0.5rem; }")
emit(".w-8 { width: 2rem; }")
emit(".w-24 { width: 6rem; }")
emit(".min-w-0 { min-width: 0px; }")
emit(".min-w-\\[64px\\] { min-width: 64px; }")
emit(".min-w-\\[80px\\] { min-width: 80px; }")
emit(".max-w-md { max-width: 28rem; }")
emit(".max-w-xs { max-width: 20rem; }")
emit(".max-w-2xl { max-width: 42rem; }")
emit(".max-w-\\[85\\%\\] { max-width: 85%; }")

# height
emit(".h-1 { height: 0.25rem; }")
emit(".h-2 { height: 0.5rem; }")
emit(".h-8 { height: 2rem; }")
emit(".h-full { height: 100%; }")

# ============== 6. Layout: flex / grid ==============
emit(".flex { display: flex; }")
emit(".inline-flex { display: inline-flex; }")
emit(".inline-block { display: inline-block; }")
emit(".block { display: block; }")
emit(".hidden { display: none; }")
emit(".grid { display: grid; }")
emit(".flex-1 { flex: 1 1 0%; }")
emit(".flex-shrink-0 { flex-shrink: 0; }")
emit(".flex-wrap { flex-wrap: wrap; }")
emit(".items-center { align-items: center; }")
emit(".items-start { align-items: flex-start; }")
emit(".items-baseline { align-items: baseline; }")
emit(".justify-center { justify-content: center; }")
emit(".justify-between { justify-content: space-between; }")
emit(".justify-end { justify-content: flex-end; }")
emit(".grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }")
emit(".grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }")
for k, v in SPACING.items():
    emit(f".gap-{k} {{ gap: {v}; }}")

# ============== 7. Border / Radius ==============
emit(".border { border-width: 1px; }")
emit(".border-t { border-top-width: 1px; }")
emit(".border-0 { border-width: 0; }")
for k, v in RADIUS.items():
    if k == 'DEFAULT':
        emit(f".rounded {{ border-radius: {v}; }}")
    else:
        emit(f".rounded-{k} {{ border-radius: {v}; }}")
emit(".rounded-tl-sm { border-top-left-radius: 0.125rem; }")

# ============== 8. Position ==============
emit(".static { position: static; }")
emit(".fixed { position: fixed; }")
emit(".absolute { position: absolute; }")
emit(".relative { position: relative; }")
emit(".sticky { position: sticky; }")
emit(".inset-0 { top: 0; right: 0; bottom: 0; left: 0; }")
emit(".z-50 { z-index: 50; }")

# ============== 9. Misc ==============
emit(".overflow-hidden { overflow: hidden; }")
emit(".resize-none { resize: none; }")
emit(".outline-none { outline: 2px solid transparent; outline-offset: 2px; }")
emit(".cursor-pointer { cursor: pointer; }")
emit(".cursor-not-allowed { cursor: not-allowed; }")
emit(".transition { transition-property: color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter; transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1); transition-duration: 150ms; }")
emit(".transition-all { transition-property: all; transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1); transition-duration: 150ms; }")
emit(".duration-500 { transition-duration: 500ms; }")

# ============== 10. Animation ==============
emit("""
.animate-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
.fade-in { animation: fadeIn 0.4s ease-out; }
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
.fade-in-up { animation: fadeInUp 0.5s ease-out; }
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}
""")

# ============== 11. Gradient backgrounds ==============
emit(".bg-gradient-to-r { background-image: linear-gradient(to right, var(--tw-gradient-stops)); }")
emit(".bg-gradient-to-br { background-image: linear-gradient(to bottom right, var(--tw-gradient-stops)); }")
emit(".from-purple-500 { --tw-gradient-from: #a855f7; --tw-gradient-to: rgb(168 85 247 / 0); --tw-gradient-stops: var(--tw-gradient-from), var(--tw-gradient-to); }")
emit(".to-pink-500 { --tw-gradient-to: #ec4899; }")

# ============== 12. Hover variants ==============
emit("""
.hover\\:bg-white\\/5:hover { background-color: rgba(255, 255, 255, 0.05); }
.hover\\:bg-white\\/10:hover { background-color: rgba(255, 255, 255, 0.1); }
.hover\\:bg-white\\/15:hover { background-color: rgba(255, 255, 255, 0.15); }
.hover\\:bg-white\\/20:hover { background-color: rgba(255, 255, 255, 0.2); }
.hover\\:bg-black\\/30:hover { background-color: rgba(0, 0, 0, 0.3); }
.hover\\:bg-black\\/50:hover { background-color: rgba(0, 0, 0, 0.5); }
.hover\\:bg-purple-500\\/20:hover { background-color: rgba(168, 85, 247, 0.2); }
.hover\\:bg-purple-500\\/30:hover { background-color: rgba(168, 85, 247, 0.3); }
.hover\\:bg-purple-500\\/50:hover { background-color: rgba(168, 85, 247, 0.5); }
.hover\\:border-orange-400\\/50:hover { border-color: rgba(251, 146, 60, 0.5); }
.hover\\:border-purple-400\\/50:hover { border-color: rgba(192, 132, 252, 0.5); }
.hover\\:border-yellow-400\\/50:hover { border-color: rgba(250, 204, 21, 0.5); }
.hover\\:text-white:hover { color: #ffffff; }
.hover\\:text-purple-300:hover { color: #d8b4fe; }
.hover\\:text-purple-400:hover { color: #c084fc; }
""")

# ============== 13. 项目自定义组件 ==============
emit("""
/* ===== 玻璃面板 ===== */
.glass {
    background: rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
}
/* ===== 紫色光晕 ===== */
.glow {
    box-shadow: 0 0 50px rgba(139, 92, 246, 0.25);
}
/* ===== 渐变文字 ===== */
.gradient-text {
    background: linear-gradient(135deg, #a78bfa 0%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    color: transparent;
}
/* ===== 主按钮（V1.8.2 移动端优化）===== */
.btn-primary {
    background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%);
    transition: all 0.2s ease;
    color: white;
    border: none;
    cursor: pointer;
    text-align: center;
    display: inline-block;
    line-height: 1.25;
    /* V1.8.2: 移动端最小点击区域 44px */
    min-height: 44px;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 500;
    padding: 10px 20px;
    -webkit-tap-highlight-color: transparent;
    user-select: none;
    -webkit-user-select: none;
    position: relative;
    overflow: hidden;
}
.btn-primary:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(139, 92, 246, 0.35);
}
.btn-primary:active:not(:disabled) {
    transform: translateY(0);
    box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3);
    opacity: 0.92;
}
.btn-primary:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}

/* ===== V1.8.2 大尺寸主按钮（页面底部主操作）===== */
.btn-lg {
    height: 56px;
    border-radius: 16px;
    font-size: 18px;
    font-weight: 600;
    padding: 0 24px;
}

/* ===== 次要按钮（V1.8.2）===== */
.btn-secondary {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(167, 139, 250, 0.3);
    color: white;
    cursor: pointer;
    text-align: center;
    display: block;
    line-height: 1.25;
    height: 48px;
    border-radius: 14px;
    font-size: 16px;
    font-weight: 500;
    min-height: 44px;
    -webkit-tap-highlight-color: transparent;
    transition: all 0.2s ease;
}
.btn-secondary:hover:not(:disabled) {
    background: rgba(139, 92, 246, 0.15);
    border-color: rgba(139, 92, 250, 0.5);
}
.btn-secondary:active:not(:disabled) {
    transform: scale(0.98);
}

/* ===== V1.8.2 移动端 App 容器 ===== */
.app-container {
    max-width: 480px;
    margin: 0 auto;
    padding: 16px;
    padding-bottom: 100px;  /* 给底部固定栏留空间 */
    min-height: 100vh;
    position: relative;
}

/* ===== V1.8.2 移动端精致卡片 ===== */
.app-card {
    background: rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 16px;
}

/* ===== V1.8.2 紧凑卡（无 padding，由 HTML 控制）===== */
.app-card-tight {
    background: rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    margin-bottom: 16px;
}

/* ===== V1.8.2 底部固定操作栏（手机体验）===== */
.bottom-action-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(15, 8, 30, 0.92);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-top: 1px solid rgba(167, 139, 250, 0.15);
    padding: 12px 16px;
    padding-bottom: max(12px, env(safe-area-inset-bottom));  /* iPhone 安全区 */
    z-index: 50;
    max-width: 480px;
    margin: 0 auto;
}
.bottom-action-bar .btn-primary {
    margin-top: 0;
}

/* ===== V1.8.2 大字号渐变标题（24px 核心人格）===== */
.hero-title {
    font-size: 24px;
    font-weight: 700;
    line-height: 1.3;
    background: linear-gradient(135deg, #c4b5fd 0%, #f9a8d4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    color: transparent;
    margin: 0 0 8px 0;
}

/* ===== V1.9 身份卡 3D 翻转 ===== */
.identity-card {
    perspective: 1200px;
    width: 100%;
    height: 320px;
    margin: 0 auto 20px auto;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
}
.identity-card-inner {
    position: relative;
    width: 100%;
    height: 100%;
    transition: transform 0.7s cubic-bezier(0.4, 0.0, 0.2, 1);
    transform-style: preserve-3d;
}
.identity-card.flipped .identity-card-inner {
    transform: rotateY(180deg);
}
.identity-card-front,
.identity-card-back {
    position: absolute;
    width: 100%;
    height: 100%;
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
    border-radius: 24px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden;
}
.identity-card-front {
    background: linear-gradient(160deg,
        rgba(139, 92, 246, 0.4) 0%,
        rgba(236, 72, 153, 0.3) 40%,
        rgba(99, 102, 241, 0.25) 100%);
    border: 1.5px solid rgba(196, 181, 253, 0.5);
    box-shadow:
        0 20px 50px rgba(139, 92, 246, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.2);
    text-align: center;
}
.identity-card-back {
    background: linear-gradient(160deg,
        rgba(99, 102, 241, 0.3) 0%,
        rgba(139, 92, 246, 0.25) 50%,
        rgba(236, 72, 153, 0.2) 100%);
    border: 1.5px solid rgba(196, 181, 253, 0.4);
    box-shadow:
        0 20px 50px rgba(139, 92, 246, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.2);
    transform: rotateY(180deg);
    text-align: left;
    justify-content: space-between;
    gap: 8px;
}
.identity-card-emoji {
    font-size: 56px;
    line-height: 1;
    margin-bottom: 12px;
    filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3));
}
.identity-card-name {
    font-size: 26px;
    font-weight: 700;
    background: linear-gradient(135deg, #fff 0%, #f9a8d4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    color: transparent;
    margin-bottom: 8px;
    line-height: 1.2;
}
.identity-card-tagline {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.75);
    line-height: 1.4;
    margin-bottom: 16px;
    font-style: italic;
}
.identity-card-params {
    display: flex;
    justify-content: space-around;
    gap: 8px;
    padding: 12px 8px;
    background: rgba(0, 0, 0, 0.25);
    border-radius: 12px;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
}
.identity-card-param {
    flex: 1;
    text-align: center;
}
.identity-card-param-label {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.identity-card-param-value {
    font-size: 12px;
    color: #fff;
    font-weight: 500;
    line-height: 1.2;
}
.identity-card-hint {
    position: absolute;
    bottom: 8px;
    right: 12px;
    font-size: 10px;
    color: rgba(255, 255, 255, 0.4);
    z-index: 5;
}
.identity-card-back-section {
    margin-bottom: 8px;
}
.identity-card-back-label {
    font-size: 10px;
    color: rgba(196, 181, 253, 0.9);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 2px;
}
.identity-card-back-text {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.9);
    line-height: 1.4;
}
.identity-flip-btn {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(196, 181, 253, 0.3);
    color: rgba(255, 255, 255, 0.8);
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 12px;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: all 0.2s;
    display: inline-flex;
    align-items: center;
    gap: 4px;
}
.identity-flip-btn:hover {
    background: rgba(139, 92, 246, 0.2);
    border-color: rgba(196, 181, 253, 0.5);
}
.identity-flip-btn:active {
    transform: scale(0.95);
}

/* ===== V1.9 入口大卡（身份卡下面 3 个核心动作）===== */
.entry-card {
    background: rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 16px 20px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 14px;
    text-decoration: none;
    color: inherit;
    transition: all 0.2s ease;
    -webkit-tap-highlight-color: transparent;
}
.entry-card:hover {
    background: rgba(139, 92, 246, 0.1);
    border-color: rgba(196, 181, 253, 0.3);
    transform: translateX(2px);
}
.entry-card:active {
    transform: scale(0.99);
}
.entry-card-icon {
    font-size: 28px;
    flex-shrink: 0;
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(139, 92, 246, 0.15);
    border-radius: 12px;
}
.entry-card-content {
    flex: 1;
    min-width: 0;
}
.entry-card-title {
    font-size: 15px;
    font-weight: 600;
    color: #fff;
    margin-bottom: 2px;
}
.entry-card-desc {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.55);
    line-height: 1.3;
}
.entry-card-arrow {
    color: rgba(196, 181, 253, 0.7);
    font-size: 18px;
    flex-shrink: 0;
}

/* ===== V1.9 顶部 Tab 导航（轻量）===== */
.tab-bar {
    display: flex;
    background: rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 4px;
    margin-bottom: 16px;
}
.tab-item {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 10px 8px;
    border-radius: 10px;
    color: rgba(255, 255, 255, 0.55);
    text-decoration: none;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s ease;
    -webkit-tap-highlight-color: transparent;
    cursor: pointer;
}
.tab-item:hover {
    color: rgba(255, 255, 255, 0.8);
}
.tab-item.active {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.4) 0%, rgba(236, 72, 153, 0.3) 100%);
    color: #fff;
    box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3);
}
.tab-item-icon {
    font-size: 14px;
}

/* ===== V1.9 身份卡正面（3 标签型）===== */
.identity-card-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    justify-content: center;
    margin-bottom: 14px;
}
.identity-card-tag {
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.18);
    color: #fff;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.15);
}

/* ===== V1.9 同类分布图 ===== */
.distribution-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    font-size: 13px;
}
.distribution-label {
    width: 88px;
    flex-shrink: 0;
    color: rgba(255, 255, 255, 0.8);
}
.distribution-bar {
    flex: 1;
    height: 8px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 999px;
    overflow: hidden;
}
.distribution-fill {
    height: 100%;
    background: linear-gradient(90deg, #8b5cf6 0%, #ec4899 100%);
    border-radius: 999px;
    transition: width 0.5s ease;
}
.distribution-pct {
    width: 40px;
    text-align: right;
    color: rgba(196, 181, 253, 0.9);
    font-weight: 600;
    flex-shrink: 0;
}

/* ===== V1.9 评价快捷按钮 ===== */
.quick-rating-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 8px;
    margin-bottom: 12px;
}
.quick-rating-btn {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 10px 6px;
    text-align: center;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: all 0.2s ease;
    color: #fff;
    font-size: 11px;
    line-height: 1.3;
}
.quick-rating-btn:hover {
    background: rgba(139, 92, 246, 0.15);
    border-color: rgba(196, 181, 253, 0.4);
}
.quick-rating-btn.active {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.4) 0%, rgba(236, 72, 153, 0.3) 100%);
    border-color: rgba(196, 181, 253, 0.6);
}
.quick-rating-emoji {
    font-size: 22px;
    display: block;
    margin-bottom: 4px;
}

/* ===== V1.9 说明书分区 ===== */
.manual-section {
    margin-bottom: 20px;
}
.manual-section-label {
    font-size: 10px;
    color: rgba(196, 181, 253, 0.9);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 6px;
}
.manual-section-title {
    font-size: 15px;
    font-weight: 600;
    color: #fff;
    margin-bottom: 10px;
}
.manual-section-text {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.85);
    line-height: 1.6;
}
/* ===== 主人格卡 ===== */
.hero-card {
    background: linear-gradient(160deg,
        rgba(139, 92, 246, 0.18) 0%,
        rgba(236, 72, 153, 0.12) 50%,
        rgba(255, 255, 255, 0.02) 100%);
    border: 1px solid rgba(167, 139, 250, 0.4);
}
/* ===== AI 反馈气泡 ===== */
.feedback-bubble {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(236, 72, 153, 0.15) 100%);
    border: 1px solid rgba(167, 139, 250, 0.4);
    animation: feedbackPop 0.4s ease-out;
}
@keyframes feedbackPop {
    0% { opacity: 0; transform: scale(0.9) translateY(8px); }
    100% { opacity: 1; transform: scale(1) translateY(0); }
}
/* ===== 视角按钮 ===== */
.perspective-btn {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: all 0.2s;
    color: white;
    cursor: pointer;
}
.perspective-btn:hover:not(:disabled) {
    background: rgba(139, 92, 246, 0.15);
    border-color: rgba(139, 92, 246, 0.5);
    transform: translateY(-1px);
}
.perspective-btn.active {
    background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%);
    border-color: transparent;
    box-shadow: 0 4px 16px rgba(139, 92, 246, 0.4);
}
.perspective-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}
/* ===== 选项按钮 ===== */
.option-btn {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: all 0.2s;
    color: white;
    cursor: pointer;
    text-align: left;
}
.option-btn:hover {
    background: rgba(139, 92, 246, 0.1);
    border-color: rgba(139, 92, 246, 0.5);
    transform: translateX(2px);
}
.option-btn.selected {
    background: rgba(139, 92, 246, 0.2);
    border-color: #a78bfa;
    box-shadow: 0 0 0 2px rgba(167, 139, 250, 0.3);
}
.option-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
}
/* ===== choice-btn (用于 page-interview 选项) ===== */
.choice-btn {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: all 0.2s;
    color: white;
    cursor: pointer;
    text-align: left;
    display: block;
    width: 100%;
}
.choice-btn:hover {
    background: rgba(139, 92, 246, 0.1);
    border-color: rgba(139, 92, 246, 0.5);
}
.choice-btn.selected {
    background: rgba(139, 92, 246, 0.2);
    border-color: #a78bfa;
}
/* ===== 自定义输入区 ===== */
.custom-input-area textarea {
    background: transparent;
    color: white;
    width: 100%;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.5rem;
    padding: 0.75rem;
    resize: vertical;
    min-height: 80px;
}
.custom-input-area textarea:focus {
    outline: none;
    border-color: #a78bfa;
}
/* ===== typing dot ===== */
.typing-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.6);
    margin: 0 2px;
    animation: typing 1.4s infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing {
    0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
    30% { opacity: 1; transform: translateY(-4px); }
}
/* ===== version-tag (版本号标签) ===== */
.version-tag {
    display: inline-block;
    font-size: 0.7rem;
    color: #6b7280;
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 2px 6px;
    border-radius: 4px;
    margin-left: 8px;
    vertical-align: middle;
}
/* ===== focus 状态 ===== */
input:focus, textarea:focus, button:focus-visible {
    outline: none;
    border-color: #a78bfa !important;
    box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
}
""")

# ============== 14. 兜底 page 隐藏（不依赖任何 JS）==============
# 注意：不要用 ID 选择器强制 display: none，会和 JS 兜底逻辑冲突
# 改用 :not(.shown) 选择器，JS 切换时只需加/移 .shown class
# 但更简单：HTML 初始就带 class="hidden"，配合 .hidden { display: none } 即可
# 不需要额外的 ID 规则
# （删掉这段兜底，避免和 showPage 函数的 inline style 兜底冲突）

# ============== 输出 ==============
output = '\n'.join(css_rules)
# 压缩一下：去掉连续空行
output = re.sub(r'\n{3,}', '\n\n', output)

with open('static/app.css', 'w') as f:
    f.write(output)

selectors = set(re.findall(r'\.[a-zA-Z][\w\\/\[\\]-]+', output))
print(f"✅ 生成 static/app.css: {len(output)} 字符, {output.count(chr(10))} 行")
print(f"✅ 覆盖 {len(selectors)} 个 CSS 选择器")
