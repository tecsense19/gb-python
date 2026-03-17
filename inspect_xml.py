def inspect_xml(xml_path, encoding='utf-16le'):
    try:
        with open(xml_path, 'r', encoding=encoding) as f:
            content = f.read()
        print(f"--- {xml_path} ---")
        print(content[:1000]) # First 1000 chars
    except Exception as e:
        print(f"Error reading {xml_path}: {e}")

if __name__ == "__main__":
    import sys
    inspect_xml(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'utf-16le')
