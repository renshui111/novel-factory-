# stylist.py --- 风格预设管理：平台风格 + 小说风格
"""自定义写作风格管理，支持用户创建/编辑/删除风格预设"""

import os, json
from core.config import load_config, save_config

# ======================== 内置预设 ========================
BUILTIN_PLATFORM_STYLES = {
    "番茄爽文": {
        "description": "快节奏、打脸爽文，每章有爽点，对话多、描写少",
        "tone": "轻松直白，口语化强",
        "pacing": "极快，每章至少一个爽点或反转",
        "dialogue_ratio": "高（60%以上对话）",
        "chapter_end": "每章结尾留悬念/钩子",
        "target_audience": "番茄小说读者（18-35岁男性为主）",
        "prompt_addon": "写作风格：番茄爽文。节奏极快，每章必须有至少一个爽点或打脸情节。对话占比60%以上，减少环境描写和心理描写。每章结尾留钩子。文笔直白口语化，不使用生僻词。目标读者是番茄小说平台用户。"
    },
    "起点精品": {
        "description": "设定扎实、逻辑自洽，世界观完整，爽点合理分布",
        "tone": "稳重但不沉闷，适当文采",
        "pacing": "中快，每3-5章一个高潮",
        "dialogue_ratio": "中等（40-50%对话）",
        "chapter_end": "自然收束，偶尔留悬念",
        "target_audience": "起点中文网读者（20-40岁男性为主）",
        "prompt_addon": "写作风格：起点精品。设定要扎实，逻辑必须自洽。节奏中快，每3-5章安排一个高潮情节。对话占比40-50%，适当加入环境描写和世界观细节。文笔稳重但不沉闷，可以有一定文采。目标读者是起点中文网资深读者。"
    },
    "番茄甜宠": {
        "description": "甜宠恋爱、轻松治愈，男女主人设讨喜",
        "tone": "甜蜜温馨，轻松幽默",
        "pacing": "中速，注重情感递进",
        "dialogue_ratio": "高（55%以上对话）",
        "chapter_end": "温馨收尾或小悬念",
        "target_audience": "番茄小说女性读者（18-30岁）",
        "prompt_addon": "写作风格：番茄甜宠。以恋爱线为主，风格甜蜜温馨、轻松幽默。男女主人设要讨喜，互动要有化学反应。对话占比55%以上。注重情感递进，避免虐心情节。每章结尾温馨或有小期待。目标读者是女性向读者。"
    },
    "纵横玄幻": {
        "description": "大世界观、修炼体系完整，战斗描写精彩",
        "tone": "大气磅礴，热血激昂",
        "pacing": "中速偏快，修炼突破+战斗交替",
        "dialogue_ratio": "中等（35-45%对话）",
        "chapter_end": "突破/战斗预告",
        "target_audience": "纵横中文网读者（玄幻爱好者）",
        "prompt_addon": "写作风格：纵横玄幻。世界观要大，修炼体系必须完整且逻辑自洽。战斗描写要精彩详细，修炼突破要有仪式感。节奏中速偏快，修炼+战斗交替推进。文笔大气磅礴、热血激昂。目标读者是资深玄幻读者。"
    },
    "严肃文学": {
        "description": "文学性强，注重人物心理、社会深度、语言艺术",
        "tone": "沉稳内敛，富有文学性",
        "pacing": "慢，注重细节铺陈",
        "dialogue_ratio": "低（20-30%对话）",
        "chapter_end": "留白或意境收尾",
        "target_audience": "文学爱好者",
        "prompt_addon": "写作风格：严肃文学。注重文学性和思想深度。人物心理描写要细腻深入，社会背景要有厚度。节奏可以慢，注重细节铺陈和氛围营造。对话占比20-30%。文笔沉稳内敛，富有文学性。避免网文套路和爽文模式。"
    },
    "轻小说": {
        "description": "日式轻小说风格，轻松日常+奇幻冒险",
        "tone": "轻松活泼，带吐槽风",
        "pacing": "中速，日常与事件交错",
        "dialogue_ratio": "极高（65%以上对话）",
        "chapter_end": "轻松收尾或小悬念",
        "target_audience": "二次元/轻小说读者",
        "prompt_addon": "写作风格：轻小说。采用日式轻小说的叙事方式，第一人称或第三人称皆可。风格轻松活泼，可以加入吐槽和内心独白。对话占比65%以上。日常描写与奇幻冒险交错。角色要有鲜明的萌属性。目标读者是二次元爱好者。"
    },
}

BUILTIN_GENRE_STYLES = {
    "玄幻": {
        "elements": ["修炼体系", "丹药法宝", "宗门势力", "秘境探索"],
        "tropes": ["废材逆袭", "奇遇不断", "扮猪吃虎", "越级挑战"],
        "prompt_addon": "类型特征：玄幻。必须包含完整的修炼体系（境界划分），有丹药、法宝、功法等设定。可以加入废材逆袭或扮猪吃虎等经典桥段。战斗描写要有层次感。"
    },
    "仙侠": {
        "elements": ["修仙境界", "法宝灵器", "仙门宗派", "天劫渡劫"],
        "tropes": ["凡人修仙", "剑道独尊", "阵法符箓", "飞升仙界"],
        "prompt_addon": "类型特征：仙侠。包含完整的修仙境界体系（练气→筑基→金丹→元婴→化神→渡劫→大乘），有法宝灵器设定。修真氛围浓厚，注重心性修炼和道法感悟。"
    },
    "科幻": {
        "elements": ["未来科技", "星际文明", "AI/机器人", "基因改造"],
        "tropes": ["末世生存", "星际殖民", "虚拟现实", "时间穿越"],
        "prompt_addon": "类型特征：科幻。科技设定要有一定科学依据，不能过于魔幻。可以涉及AI、星际殖民、基因改造、虚拟现实等主题。逻辑必须自洽，技术描述要有细节感。"
    },
    "都市": {
        "elements": ["现代都市", "商业职场", "异能系统", "校园生活"],
        "tropes": ["重生逆袭", "神医高手", "总裁豪门", "系统流"],
        "prompt_addon": "类型特征：都市。背景为现代都市，可以加入异能、系统、重生等元素。注重现实感和代入感，人物行为逻辑要符合现代人思维。商业、职场、校园等场景描写要真实。"
    },
    "末世": {
        "elements": ["丧尸/变异", "生存基地", "异能觉醒", "资源争夺"],
        "tropes": ["末世重生", "基地建设", "丧尸进化", "人性考验"],
        "prompt_addon": "类型特征：末世。世界已陷入末日危机（丧尸、病毒、天灾等）。注重生存压力和人性考验。有基地建设、资源争夺、异能觉醒等元素。氛围紧张压抑但留希望。"
    },
    "历史": {
        "elements": ["真实朝代", "权谋斗争", "科举官场", "战争军事"],
        "tropes": ["穿越改造", "辅佐明君", "商战崛起", "科技兴国"],
        "prompt_addon": "类型特征：历史。基于真实历史背景或架空历史。注重历史细节和时代氛围，人物言行要符合时代特征。可以加入权谋、战争、改革等元素。考据要扎实。"
    },
    "游戏": {
        "elements": ["虚拟游戏", "等级装备", "公会团战", "职业系统"],
        "tropes": ["全服第一", "隐藏职业", "BUG利用", "游戏入侵现实"],
        "prompt_addon": "类型特征：游戏/电竞。以虚拟游戏世界为主要舞台，有完整的等级、装备、技能、职业系统。可以加入公会战、副本攻略、竞技对战等元素。游戏设定要详细且有趣。"
    },
    "言情": {
        "elements": ["恋爱关系", "情感冲突", "家庭背景", "成长蜕变"],
        "tropes": ["欢喜冤家", "虐恋情深", "先婚后爱", "破镜重圆"],
        "prompt_addon": "类型特征：言情。以恋爱关系为主线，注重情感描写和人物心理变化。男女主人设要立体讨喜，情感发展要自然合理。可以加入家庭、职场等支线丰富故事。文笔细腻温暖。"
    },
}

# ======================== 用户自定义风格 ========================
def get_all_platform_styles() -> dict:
    """获取所有平台风格（内置 + 用户自定义）"""
    cfg = load_config()
    user_styles = cfg.get("custom_platform_styles", {})
    all_styles = dict(BUILTIN_PLATFORM_STYLES)
    all_styles.update(user_styles)
    return all_styles

def get_all_genre_styles() -> dict:
    """获取所有类型风格（内置 + 用户自定义）"""
    cfg = load_config()
    user_styles = cfg.get("custom_genre_styles", {})
    all_styles = dict(BUILTIN_GENRE_STYLES)
    all_styles.update(user_styles)
    return all_styles

def save_custom_platform_style(name: str, style_data: dict):
    """保存自定义平台风格"""
    cfg = load_config()
    if "custom_platform_styles" not in cfg:
        cfg["custom_platform_styles"] = {}
    cfg["custom_platform_styles"][name] = style_data
    save_config()

def save_custom_genre_style(name: str, style_data: dict):
    """保存自定义类型风格"""
    cfg = load_config()
    if "custom_genre_styles" not in cfg:
        cfg["custom_genre_styles"] = {}
    cfg["custom_genre_styles"][name] = style_data
    save_config()

def delete_custom_platform_style(name: str):
    """删除自定义平台风格"""
    cfg = load_config()
    if name in cfg.get("custom_platform_styles", {}):
        del cfg["custom_platform_styles"][name]
        save_config()

def delete_custom_genre_style(name: str):
    """删除自定义类型风格"""
    cfg = load_config()
    if name in cfg.get("custom_genre_styles", {}):
        del cfg["custom_genre_styles"][name]
        save_config()

def build_style_prompt(platform_style: str = "", genre_style: str = "") -> str:
    """根据选中的风格构建附加 prompt"""
    parts = []
    
    platform_styles = get_all_platform_styles()
    if platform_style and platform_style in platform_styles:
        parts.append(platform_styles[platform_style].get("prompt_addon", ""))
    
    genre_styles = get_all_genre_styles()
    if genre_style and genre_style in genre_styles:
        parts.append(genre_styles[genre_style].get("prompt_addon", ""))
    
    return "\n\n".join(parts)

def get_style_template() -> dict:
    """返回新建风格的空白模板"""
    return {
        "description": "",
        "tone": "",
        "pacing": "",
        "dialogue_ratio": "",
        "chapter_end": "",
        "target_audience": "",
        "prompt_addon": ""
    }