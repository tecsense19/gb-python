import re

def parse_xml(xml_path):
    with open(xml_path, 'r', encoding='utf-16le') as f:
        content = f.read()
    
    # Simple regex to find top-level tags in topmostSubform
    # Based on previous dump, they look like <f1_1 />, <c1_1>0</c1_1>, etc.
    tags = re.findall(r'<([a-zA-Z0-9_]+)[\s/]*>', content)
    unique_tags = sorted(list(set(tags)))
    
    for tag in unique_tags:
        print(tag)

if __name__ == "__main__":
    parse_xml('xfa_dump.xml')
