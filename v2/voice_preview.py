# -*- coding: utf-8 -*-
"""voice_preview.py --- AI配音 + 有声书预览
生成TTS脚本、角色音色分配、语速标记
注意：实际音频生成需配合TTS引擎（edge-tts/azure等），此模块生成标注脚本
"""

import re, json

def generate_voice_script(chapter_text: str, chapter_num: int = 1,
                           narrator_voice: str = "沉稳男声",
                           default_voice: str = "清亮男声") -> dict:
    """生成配音脚本：解析对话→分配角色音色→标记语速/情绪
    
    Returns:
        {script_lines: [{text, voice, speed, emotion}], 
         character_voices: {角色名: 音色},
         stats: {total_duration_estimate, dialogue_count}}
    """
    lines = chapter_text.split('\n')
    script = []
    character_voices = {}
    voice_pool = ["温柔女声", "清冷女声", "活泼少女", "沧桑男声", "阴沉男声", 
                  "豪迈男声", "少年音", "老者音", "冷漠声线", "妩媚女声"]
    voice_idx = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            script.append({"text": "", "voice": "pause", "speed": "normal", "emotion": "neutral"})
            continue
        
        # Check if it's dialogue
        dialogue_match = re.findall(r'["""''""]([^""''""\n]+)["""''""]', line)
        
        if dialogue_match:
            # Try to identify speaker
            speaker = _identify_speaker(line)
            
            for d_text in dialogue_match:
                # Assign voice to character
                if speaker and speaker not in character_voices:
                    if voice_idx < len(voice_pool):
                        character_voices[speaker] = voice_pool[voice_idx]
                        voice_idx += 1
                    else:
                        character_voices[speaker] = default_voice
                
                voice = character_voices.get(speaker, default_voice) if speaker else default_voice
                
                # Detect emotion
                emotion = _detect_emotion(line)
                speed = _detect_speed(line)
                
                script.append({
                    "text": d_text,
                    "voice": voice,
                    "speaker": speaker,
                    "speed": speed,
                    "emotion": emotion,
                    "type": "dialogue",
                })
        else:
            # Narration
            script.append({
                "text": line,
                "voice": narrator_voice,
                "speed": _detect_speed(line),
                "emotion": _detect_emotion(line),
                "type": "narration",
            })
    
    # Stats
    dialogue_count = sum(1 for s in script if s.get("type") == "dialogue")
    total_chars = sum(len(s["text"]) for s in script if s["text"])
    estimated_seconds = total_chars * 0.3  # ~3 char/sec for Chinese
    
    return {
        "script_lines": script,
        "character_voices": character_voices,
        "stats": {
            "total_duration_estimate_seconds": round(estimated_seconds, 1),
            "total_duration_estimate_minutes": round(estimated_seconds / 60, 1),
            "dialogue_count": dialogue_count,
            "total_lines": len(script),
            "unique_characters": len(character_voices),
        },
        "chapter_num": chapter_num,
    }


def _identify_speaker(line: str) -> str:
    """从对话行中提取说话人"""
    # Pattern: XXX说/道/问/喊...
    patterns = [
        r'([^\s""''""]{1,4})(?:说|道|问|喊|叫|吼|低语|喃喃|笑道|怒道|冷声|淡淡道|开口道)',
    ]
    for p in patterns:
        m = re.search(p, line)
        if m:
            return m.group(1)
    return ""


def _detect_emotion(line: str) -> str:
    """检测情绪"""
    emotions = {
        "angry": ["怒", "吼", "骂", "恨", "愤", "喝道", "厉声"],
        "sad": ["哭", "泪", "悲", "叹", "哀", "黯然", "低落"],
        "happy": ["笑", "喜", "乐", "欢", "哈哈", "开心", "欣喜"],
        "tense": ["紧张", "危险", "急", "快", "猛地", "突然", "猛地"],
        "cold": ["冷", "淡", "漠", "面无表情", "哼"],
        "gentle": ["柔", "温", "轻", "细", "软", "呢喃"],
    }
    for emotion, keywords in emotions.items():
        if any(k in line for k in keywords):
            return emotion
    return "neutral"


def _detect_speed(line: str) -> str:
    """检测语速"""
    if any(k in line for k in ["急", "快", "冲", "跑", "追", "杀", "战", "喊"]):
        return "fast"
    if any(k in line for k in ["慢", "缓", "静", "沉思", "沉默", "久久"]):
        return "slow"
    return "normal"


def export_voice_script_as_text(script: dict, fmt: str = "plain") -> str:
    """导出配音脚本为可读文本"""
    lines = script["script_lines"]
    
    if fmt == "plain":
        result = []
        for item in lines:
            if item["voice"] == "pause":
                result.append("")
            elif item.get("type") == "dialogue":
                result.append(f"[{item.get('speaker','?')}|{item['voice']}|{item['emotion']}|{item['speed']}] \"{item['text']}\"")
            else:
                result.append(f"[旁白|{item['voice']}|{item['emotion']}|{item['speed']}] {item['text']}")
        return "\n".join(result)
    
    elif fmt == "ssml":
        # Simple SSML-like format for TTS
        result = ['<speak version="1.0">']
        for item in lines:
            if item["voice"] == "pause":
                result.append('<break time="500ms"/>')
            else:
                speed_map = {"fast": "120%", "slow": "80%", "normal": "100%"}
                s = speed_map.get(item["speed"], "100%")
                result.append(f'<prosody rate="{s}">{item["text"]}</prosody>')
        result.append('</speak>')
        return "\n".join(result)
    
    return ""


def preview_first_lines(script: dict, count: int = 10) -> str:
    """预览配音脚本前N行"""
    lines = script["script_lines"][:count]
    result = []
    for item in lines:
        if item["voice"] == "pause":
            result.append("[停顿]")
        else:
            icon = {"angry": "😤", "sad": "😢", "happy": "😊", "tense": "😰",
                    "cold": "😐", "gentle": "🌸"}.get(item["emotion"], "  ")
            result.append(f'{icon} [{item["voice"]}] {item["text"][:60]}')
    return "\n".join(result)
