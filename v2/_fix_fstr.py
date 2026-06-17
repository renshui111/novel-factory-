with open("novel.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Fix line 845-847: the f-string with literal newline
# Replace with concatenation
for i in range(len(lines)):
    if 'current_summary = f"{current_summary}' in lines[i] and '\\n' not in lines[i]:
        lines[i] = '            current_summary = current_summary + "\\n\\n" + snap_ctx\n'
        # Remove the next two lines (the literal newline and closing)
        if i + 2 < len(lines) and 'snap_ctx}"' in lines[i+2]:
            lines[i+1] = ''
            lines[i+2] = ''

with open("novel.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Fixed f-string")
