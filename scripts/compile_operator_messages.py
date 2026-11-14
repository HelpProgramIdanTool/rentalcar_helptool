"""Build standard Django gettext catalogs without a system gettext installation."""
import json
import struct
from pathlib import Path


def compile_catalog(messages):
    keys = sorted(messages)
    originals = b''
    translations = b''
    ids = []
    values = []
    offset = 28 + 16 * len(keys)
    for key in keys:
        encoded = key.encode('utf-8')
        ids.append((len(encoded), offset + len(originals)))
        originals += encoded + b'\0'
    offset += len(originals)
    for key in keys:
        encoded = messages[key].encode('utf-8')
        values.append((len(encoded), offset + len(translations)))
        translations += encoded + b'\0'
    return (struct.pack('<7I', 0x950412de, 0, len(keys), 28, 28 + len(keys) * 8, 0, 0)
            + b''.join(struct.pack('<2I', *row) for row in ids + values) + originals + translations)


def main():
    root = Path(__file__).resolve().parents[1]
    rows = [line.split('\t') for line in (root/'locale/operator-translations.tsv').read_text(encoding='utf-8').splitlines() if line]
    for index, language in [(1, 'pl'), (2, 'en')]:
        messages = {row[0]: row[index] for row in rows}
        messages[''] = f'Content-Type: text/plain; charset=UTF-8\nLanguage: {language}\nPlural-Forms: nplurals=2; plural=(n != 1);\n'
        folder = root/'locale'/language/'LC_MESSAGES'
        folder.mkdir(parents=True, exist_ok=True)
        po = '\n\n'.join('msgid '+json.dumps(key, ensure_ascii=False)+'\nmsgstr '+json.dumps(value, ensure_ascii=False) for key,value in sorted(messages.items()))
        (folder/'django.po').write_text(po+'\n', encoding='utf-8')
        (folder/'django.mo').write_bytes(compile_catalog(messages))
    print(f'Compiled {len(rows)} operator messages in Polish and English.')


if __name__ == '__main__':
    main()
