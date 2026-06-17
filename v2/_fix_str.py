with open("novel.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Fix lines 845-847: merge the broken f-string
for i in range(len(lines)):
    if 'current_summary = f"{current_summary}' in lines[i] and lines[i].strip().endswith('{current_summary}'):
        lines[i] = '            current_summary = current_summary + "\\n\\n" + snap_ctx\n'
        # Remove the next two lines (empty + snap_ctx)
        if i+1 < len(lines) and lines[i+1].strip() == '':
            del lines[i+1]
        if i+1 < len(lines) and '{snap_ctx}' in lines[i+1]:
            del lines[i+1]
        break

with open("novel.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Fixed broken f-string")
