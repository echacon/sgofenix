# convert_yaml_to_utf8.py
from pathlib import Path
import chardet

def convert_file(filepath):
    with open(filepath, 'rb') as f:
        raw = f.read()
        result = chardet.detect(raw)
        encoding = result['encoding']
    if encoding != 'utf-8':
        content = raw.decode(encoding)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Convertido: {filepath} ({encoding} -> utf-8)")

for yaml_file in Path("ontologia/empresa").glob("*.yaml"):
    convert_file(yaml_file)