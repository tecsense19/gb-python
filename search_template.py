import re

with open("template_debug.xml", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# Find all occurrences of name="c1_1"
matches = list(re.finditer(r'name="c1_1"', content))
print(f"Found {len(matches)} occurrences of name=\"c1_1\"")

for i, m in enumerate(matches):
    start = max(0, m.start() - 200)
    end = min(len(content), m.end() + 1000)
    chunk = content[start:end]
    print(f"\n--- Match {i} ---")
    # Try to find the enclosing <field> or <exclGroup>
    # Simple search for the next </field>
    field_end = chunk.find("</field>", 200)
    if field_end != -1:
        print(chunk[:field_end+8])
    else:
        print(chunk[:500])
