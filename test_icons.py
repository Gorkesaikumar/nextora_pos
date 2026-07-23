import os, re
icons = set()
for root, _, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                content = f.read()
                matches = re.findall(r'data-lucide="([^"]+)"', content)
                icons.update(matches)
print(','.join(sorted(icons)))
