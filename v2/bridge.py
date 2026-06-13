# -*- coding: utf-8 -*-
"""bridge.py --- 拆书→写书桥梁
将拆书分析结果转换为可用的写作参数：风格迁移、大纲生成、角色模板
"""

import os, json
# core imports moved to function level

# ---------------------------------------------------------------------------
# Style migration: "以此风格写新书"
# ---------------------------------------------------------------------------

def extract_style_profile(analysis_report_path: str) -> dict:
    """从分析报告提取可量化的风格参数"""
    if not os.path.exists(analysis_report_path):
        return {}
    
    report = json.loads(read_file(analysis_report_path))
    syn = report.get("synthesized", {})
    
    style_text = syn.get("style", "")
    if not style_text:
        return {}
    
    prompt = f"""从以下写作风格分析中提取可量化的参数：

{style_text[:3000]}

返回JSON格式：
{{
  "sentence_length": "短/中/长",
  "paragraph_length": "短/中/长", 
  "dialogue_density": "低/中/高",
  "description_density": "低/中/高",
  "pace": "快/中/慢",
  "tone": "严肃/轻松/幽默/沉重/热血/悬疑",
  "person": "第一人称/第三人称",
  "key_techniques": ["技法1", "技法2", "技法3"],
  "writing_rules": ["应遵循的规则1", "规则2"],
  "avoid_list": ["应避免的1", "应避免的2"]
}}

只返回JSON。"""

    try:
        result = llm_invoke_ada(prompt)
        import re
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass
    
    return {}


def build_style_prompt(profile: dict) -> str:
    """将风格参数转为写作prompt"""
    if not profile:
        return ""
    
    lines = ["[模仿风格要求]"]
    
    mapping = {
        "sentence_length": ("句长", {"短": "多用短句（10-20字），少用长句",
                                       "中": "长短句结合，自然交替",
                                       "长": "适当使用长句描写，增加文学性"}),
        "dialogue_density": ("对话密度", {"低": "以叙述和描写为主，对话精简",
                                           "中": "对话与叙述平衡",
                                           "高": "用对话推动剧情，多写人物交流"}),
        "pace": ("节奏", {"快": "快节奏，减少冗长描写，直奔剧情",
                          "中": "张弛有度", "慢": "从容铺陈，注重氛围"}),
        "tone": ("语气", {}),
    }
    
    for key, (label, options) in mapping.items():
        val = profile.get(key, "")
        if val in options:
            lines.append(f"- {label}: {options[val]}")
        elif val:
            lines.append(f"- {label}: {val}")
    
    for tech in profile.get("key_techniques", []):
        lines.append(f"- 技法: {tech}")
    
    for rule in profile.get("writing_rules", []):
        lines.append(f"- 规则: {rule}")
    
    if profile.get("avoid_list"):
        lines.append("- 避免: " + "; ".join(profile["avoid_list"]))
    
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Outline generation from analysis
# ---------------------------------------------------------------------------

def generate_outline_from_analysis(report_path: str, num_chapters: int = 30,
                                    custom_topic: str = "") -> str:
    """从拆书分析中生成新书大纲"""
    if not os.path.exists(report_path):
        return ""
    
    report = json.loads(read_file(report_path))
    syn = report.get("synthesized", {})
    
    plot_text = syn.get("plot", "")[:3000]
    char_text = syn.get("characters", "")[:2000]
    style_text = syn.get("style", "")[:1000]
    
    topic_hint = f"新书主题: {custom_topic}" if custom_topic else "请根据分析报告的风格和结构，为新书设计主题"
    
    prompt = f"""根据以下全书分析报告，为新书生成完整的章节大纲：

{plot_text}

角色参考：
{char_text}

风格参考：
{style_text}

{topic_hint}

要求：
1. 生成{num_chapters}章的大纲
2. 每章包含: 章标题 + 50字概要
3. 格式: 第XXX章: 标题 — 概要
4. 整体要有起承转合的结构
5. 前3章要抓人，中间要有高潮，结尾要有收束"""

    try:
        return llm_invoke_ada(prompt) or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Character template extraction
# ---------------------------------------------------------------------------

def extract_character_templates(report_path: str) -> list:
    """从分析报告中提取角色模板"""
    if not os.path.exists(report_path):
        return []
    
    report = json.loads(read_file(report_path))
    char_text = report.get("synthesized", {}).get("characters", "")
    
    if not char_text:
        return []
    
    prompt = f"""从以下角色分析中提取角色模板：

{char_text[:3000]}

返回JSON数组，每个元素包含：
{{
  "name": "角色名",
  "archetype": "原型（英雄/导师/反叛/恋人/智者/小丑/守护者等）",
  "personality": "性格关键词",
  "motivation": "核心动机",
  "arc": "成长弧线描述",
  "strengths": ["优点"],
  "flaws": ["缺点"],
  "template_for_new": "总结为通用模板的一句话"
}}

只返回JSON数组。"""

    try:
        result = llm_invoke_ada(prompt)
        import re
        json_match = re.search(r'\[[\s\S]*\]', result)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass
    
    return []


# ---------------------------------------------------------------------------
# One-click: analyze, then create
# ---------------------------------------------------------------------------

def analyze_then_create(filepath: str, num_chapters: int = 30,
                         custom_topic: str = "", log_callback=None) -> dict:
    """一键流程：拆书→提取风格→生成大纲→返回写书配置"""
    from splitter import full_analyze
    
    # Step 1: Analyze
    if log_callback:
        log_callback("=== 第一步：分析原书 ===")
    
    output_dir = os.path.dirname(filepath)
    report_dir = os.path.join(output_dir, "analysis_output")
    report = full_analyze(filepath, report_dir, log_callback)
    
    report_path = os.path.join(report_dir, f"{os.path.splitext(os.path.basename(filepath))[0]}_分析报告.json")
    
    # Step 2: Extract style
    if log_callback:
        log_callback("\n=== 第二步：提取风格 ===")
    profile = extract_style_profile(report_path)
    
    # Step 3: Generate outline
    if log_callback:
        log_callback("\n=== 第三步：生成大纲 ===")
    outline = generate_outline_from_analysis(report_path, num_chapters, custom_topic)
    
    # Step 4: Extract character templates
    if log_callback:
        log_callback("\n=== 第四步：提取角色模板 ===")
    char_templates = extract_character_templates(report_path)
    
    result = {
        "style_profile": profile,
        "style_prompt": build_style_prompt(profile),
        "outline": outline,
        "character_templates": char_templates,
        "report_path": report_path,
    }
    
    # Save bundled config
    config_path = os.path.join(report_dir, "写书配置.json")
    write_file(config_path, json.dumps(result, ensure_ascii=False, indent=2))
    
    if log_callback:
        log_callback(f"\n写书配置已保存: {config_path}")
    
    return result
