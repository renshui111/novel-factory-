# ═══════════════════════════════════════════════════════════
# 手动分步流程 - 新增5个生成函数
# ═══════════════════════════════════════════════════════════

def generate_outline(topic: str, genre: str, num_chapters: int,
                     words_per_chapter: int, book_dir: str,
                     log_callback=None) -> str:
    """Step 1: 生成大纲"""
    from prompts import OUTLINE_GENERATION
    prompt = OUTLINE_GENERATION.format(
        topic=topic, genre=genre, num_chapters=num_chapters,
        words_per_chapter=words_per_chapter)
    if log_callback:
        log_callback("正在生成大纲...")
    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的网文作家，擅长规划长篇小说的结构。请严格按照要求的Markdown格式输出。")
    write_file(os.path.join(book_dir, "大纲.md"), result)
    if log_callback:
        log_callback(f"大纲完成 ({count_words(result)} 字)")
    return result


def generate_world_building(outline: str, genre: str, book_dir: str,
                            log_callback=None) -> str:
    """Step 2: 生成世界观设定"""
    from prompts import WORLD_BUILDING_PROMPT
    prompt = WORLD_BUILDING_PROMPT.format(outline=outline[:6000], genre=genre)
    if log_callback:
        log_callback("正在生成世界观设定...")
    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的网文设定师。请详细具体地输出世界观设定，不要笼统概括。")
    write_file(os.path.join(book_dir, "世界观.md"), result)
    if log_callback:
        log_callback(f"世界观完成 ({count_words(result)} 字)")
    return result


def generate_characters(outline: str, world_setting: str, genre: str,
                        book_dir: str, log_callback=None) -> str:
    """Step 3: 生成人物设定"""
    from prompts import CHARACTER_GENERATION
    prompt = CHARACTER_GENERATION.format(
        outline=outline[:4000], world_setting=world_setting[:3000], genre=genre)
    if log_callback:
        log_callback("正在生成人物设定...")
    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的网文人设师。请为每个角色输出详细的具体描述。")
    write_file(os.path.join(book_dir, "人物设定.md"), result)
    if log_callback:
        log_callback(f"人物设定完成 ({count_words(result)} 字)")
    return result


def generate_organizations(outline: str, world_setting: str,
                           characters: str, genre: str, book_dir: str,
                           log_callback=None) -> str:
    """Step 4: 生成组织/势力设定"""
    from prompts import ORGANIZATION_GENERATION
    prompt = ORGANIZATION_GENERATION.format(
        outline=outline[:3000], world_setting=world_setting[:2500],
        characters=characters[:2500], genre=genre)
    if log_callback:
        log_callback("正在生成组织设定...")
    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的网文设定师。请详细输出组织体系设定。")
    write_file(os.path.join(book_dir, "组织设定.md"), result)
    if log_callback:
        log_callback(f"组织设定完成 ({count_words(result)} 字)")
    return result


def generate_relationships(outline: str, characters: str,
                           organizations: str, genre: str, book_dir: str,
                           log_callback=None) -> str:
    """Step 5: 生成人物关系+组织关系"""
    from prompts import RELATIONSHIP_GENERATION
    prompt = RELATIONSHIP_GENERATION.format(
        outline=outline[:3000], characters=characters[:3000],
        organizations=organizations[:2000], genre=genre)
    if log_callback:
        log_callback("正在生成关系网络...")
    result = llm_invoke_ada(prompt,
        system_msg="你是一位专业的网文设定师。请详细输出人物关系和组织关系图。")
    write_file(os.path.join(book_dir, "关系图谱.md"), result)
    if log_callback:
        log_callback(f"关系图谱完成 ({count_words(result)} 字)")
    return result
