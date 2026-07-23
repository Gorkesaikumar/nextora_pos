import urllib.request, os

urls = {
    'github.html': 'https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/github.svg',
    'twitter.html': 'https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/twitter.svg',
    'linkedin.html': 'https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/linkedin.svg',
    'youtube.html': 'https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/youtube.svg'
}

for name, url in urls.items():
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            svg = response.read().decode('utf-8')
            svg = svg.replace('<svg', '<svg class="{{ class|default:\'w-5 h-5 text-neutral-400\' }}"')
            
            with open(os.path.join('templates', 'icons', name), 'w', encoding='utf-8') as f:
                f.write(svg)
            print(f'Saved {name}')
    except Exception as e:
        print(f'Failed {name}: {e}')
