import re

def parse_xml_robust(xml_path):
    # Try reading as UTF-16LE (common for PowerShell redirects)
    try:
        with open(xml_path, 'rb') as f:
            raw = f.read()
        
        # Check for BOM
        if raw.startswith(b'\xff\xfe'):
            content = raw.decode('utf-16-le')
        elif raw.startswith(b'\xfe\xff'):
            content = raw.decode('utf-16-be')
        else:
            content = raw.decode('utf-8', errors='ignore')
            
        tags = re.findall(r'<([a-zA-Z0-9_]+)', content)
        unique_tags = sorted(list(set(tags)))
        
        with open(xml_path.replace('.xml', '_tags.txt'), 'w', encoding='utf-8') as f:
            for tag in unique_tags:
                f.write(tag + '\n')
        print(f"Extracted {len(unique_tags)} tags from {xml_path}")
        
    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")

if __name__ == "__main__":
    import sys
    parse_xml_robust(sys.argv[1])
