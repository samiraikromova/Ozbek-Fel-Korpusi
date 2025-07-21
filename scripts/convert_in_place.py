# scripts/convert_in_place.py
import os, chardet

# Compute the absolute path to media/articles
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, 'media', 'articles')
)

print(f"🚀 Starting conversion. Looking in: {BASE_DIR!r}")

if not os.path.isdir(BASE_DIR):
    print("❌ ERROR: media/articles directory not found. Check that path and try again.")
    exit(1)

styles = os.listdir(BASE_DIR)
print(f"Found style subdirs: {styles}")

for style in styles:
    style_dir = os.path.join(BASE_DIR, style)
    if not os.path.isdir(style_dir):
        print(f" Skipping {style!r} (not a directory)")
        continue

    files = [f for f in os.listdir(style_dir) if f.lower().endswith('.txt')]
    print(f" • In '{style}': {len(files)} .txt files -> {files}")

    for fname in files:
        path = os.path.join(style_dir, fname)
        raw = open(path, 'rb').read()
        enc = chardet.detect(raw)['encoding'] or 'utf-8'
        text = raw.decode(enc, errors='ignore')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"   ✔ Re-encoded {style}/{fname} (from {enc})")

print("✅ All done.")
