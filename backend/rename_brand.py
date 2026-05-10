import os, re

root = r"d:\Program Files\EVIDRA\frontend"

replacements = [
    ("AIVENTRA FORENSIC INTELLIGENCE REPORT", "FORENSIQ INTELLIGENCE REPORT"),
    ("AIVENTRA", "ForensIQ"),
    ("aiventra_token", "forensiq_token"),
    ("Aiventra", "ForensIQ"),
]

for dirpath, dirnames, filenames in os.walk(root):
    if "node_modules" in dirpath or ".next" in dirpath:
        continue
    for fname in filenames:
        if fname.endswith((".js", ".jsx", ".css", ".json")):
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                original = content
                for old, new in replacements:
                    content = content.replace(old, new)
                if content != original:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"Updated: {fpath}")
            except Exception as e:
                print(f"Skip: {fpath} ({e})")

print("\nDone!")
