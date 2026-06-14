with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Update _ai_generate_step to collect and pass extra_requirements
# Find the section where generation functions are called
old1 = """                if step_key == "step1":
                    book_dir = prepare_book_dir(topic)
                    self._book_dir = book_dir
                    result = generate_outline(topic, genre, num_ch, wc, book_dir,
                                              log_callback=lambda m: self._log(self._create_log, m))
                elif step_key == "step2":
                    outline = self._step_results.get("step1", "")
                    result = generate_world_building(outline, genre, self._book_dir,
                                                     log_callback=lambda m: self._log(self._create_log, m))
                elif step_key == "step3":
                    outline = self._step_results.get("step1", "")
                    world = self._step_results.get("step2", "")
                    result = generate_characters(outline, world, genre, self._book_dir,
                                                 log_callback=lambda m: self._log(self._create_log, m))
                elif step_key == "step4":
                    outline = self._step_results.get("step1", "")
                    world = self._step_results.get("step2", "")
                    chars = self._step_results.get("step3", "")
                    result = generate_organizations(outline, world, chars, genre, self._book_dir,
                                                    log_callback=lambda m: self._log(self._create_log, m))
                elif step_key == "step5":
                    outline = self._step_results.get("step1", "")
                    chars = self._step_results.get("step3", "")
                    orgs = self._step_results.get("step4", "")
                    result = generate_relationships(outline, chars, orgs, genre, self._book_dir,
                                                    log_callback=lambda m: self._log(self._create_log, m))"""

new1 = """                # Collect extra requirements
                extra = ""
                if hasattr(self, '_extra_req_text'):
                    extra = self._extra_req_text.get("1.0", "end-1c").strip()
                    # Remove placeholder text
                    if extra.startswith("例如：") or extra.startswith("输入你的"):
                        extra = ""
                self._step_extra[step_key] = extra

                if step_key == "step1":
                    book_dir = prepare_book_dir(topic)
                    self._book_dir = book_dir
                    result = generate_outline(topic, genre, num_ch, wc, book_dir,
                                              log_callback=lambda m: self._log(self._create_log, m),
                                              extra_requirements=extra)
                elif step_key == "step2":
                    outline = self._step_results.get("step1", "")
                    result = generate_world_building(outline, genre, self._book_dir,
                                                     log_callback=lambda m: self._log(self._create_log, m),
                                                     extra_requirements=extra)
                elif step_key == "step3":
                    outline = self._step_results.get("step1", "")
                    world = self._step_results.get("step2", "")
                    result = generate_characters(outline, world, genre, self._book_dir,
                                                 log_callback=lambda m: self._log(self._create_log, m),
                                                 extra_requirements=extra)
                elif step_key == "step4":
                    outline = self._step_results.get("step1", "")
                    world = self._step_results.get("step2", "")
                    chars = self._step_results.get("step3", "")
                    result = generate_organizations(outline, world, chars, genre, self._book_dir,
                                                    log_callback=lambda m: self._log(self._create_log, m),
                                                    extra_requirements=extra)
                elif step_key == "step5":
                    outline = self._step_results.get("step1", "")
                    chars = self._step_results.get("step3", "")
                    orgs = self._step_results.get("step4", "")
                    result = generate_relationships(outline, chars, orgs, genre, self._book_dir,
                                                    log_callback=lambda m: self._log(self._create_log, m),
                                                    extra_requirements=extra)"""

if old1 in content:
    content = content.replace(old1, new1)
    print("_ai_generate_step updated with extra_requirements")
else:
    print("Pattern not found")
    # Debug: find the section
    idx = content.find("step_key == \"step1\"")
    if idx >= 0:
        print("step1 block found at index", idx)
        print(content[idx:idx+200])

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
