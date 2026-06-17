with open("novel.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add import at top
old_import = "from deslop import rule_based_deslop"
new_import = "from deslop import rule_based_deslop\nfrom snapshot import should_snapshot, take_snapshot, get_snapshot_context"
content = content.replace(old_import, new_import)

# 2. In generate_novel: after each batch summary update, check snapshot
old_batch = '''                save_checkpoint(book_dir, chapters_done, new_summary or current_summ)'''
new_batch = '''                save_checkpoint(book_dir, chapters_done, new_summary or current_summ)
                
                # 角色状态快照（每10章）
                if should_snapshot(chapters_done):
                    take_snapshot(book_dir, chapters_done, log_callback=log_callback)'''
content = content.replace(old_batch, new_batch)

# 3. In continue_novel: inject snapshot context
old_cont = '''        # 从目录获取章节标题
        ch_title = f"续写第{ch_num}章"

        prompt = CHAPTER_GENERATION.format(
            chapter_num=ch_num, novel_setting=novel_setting,
            directory=directory_text, summary_text=current_summary,
            chapter_title=ch_title, chapter_desc="续写内容，承接前文",
            target_words=target_words)'''
new_cont = '''        # 从目录获取章节标题
        ch_title = f"续写第{ch_num}章"

        # 注入角色快照（优先于全文摘要）
        snap_ctx = get_snapshot_context(book_dir, max_chars=1500)
        if snap_ctx:
            current_summary = f"{current_summary}\n\n{snap_ctx}"

        prompt = CHAPTER_GENERATION.format(
            chapter_num=ch_num, novel_setting=novel_setting,
            directory=directory_text, summary_text=current_summary,
            chapter_title=ch_title, chapter_desc="续写内容，承接前文",
            target_words=target_words)'''
content = content.replace(old_cont, new_cont)

# 4. In continue_novel: also take snapshots every 10 chapters
old_cont_save = '''        save_checkpoint(book_dir, chapters_done, summary)'''
new_cont_save = '''        save_checkpoint(book_dir, chapters_done, summary)
        
        # 角色状态快照
        if should_snapshot(chapters_done):
            take_snapshot(book_dir, chapters_done, log_callback=log_callback)'''
content = content.replace(old_cont_save, new_cont_save)

with open("novel.py", "w", encoding="utf-8") as f:
    f.write(content)
print("novel.py: snapshot integration done")
