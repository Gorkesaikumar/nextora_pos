import os, re
fa_icons = set()
bi_icons = set()
svgs = set()
for root, _, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                content = f.read()
                fa_matches = re.findall(r'class=".*?(fa-[^ ]+).*?"', content)
                bi_matches = re.findall(r'class=".*?(bi-[^ ]+).*?"', content)
                svg_matches = re.findall(r'<svg.*?</svg>', content, re.DOTALL)
                fa_icons.update(fa_matches)
                bi_icons.update(bi_matches)
                if svg_matches:
                    svgs.add(file)
print('FA:', fa_icons)
print('BI:', bi_icons)
print('SVG Files:', svgs)
