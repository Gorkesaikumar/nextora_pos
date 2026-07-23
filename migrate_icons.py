import os
import re

def migrate_icons():
    # We will regex search for <i data-lucide="ICON_NAME" class="CLASSES"></i>
    # and replace with {% include "icons/ICON_NAME.html" with class="CLASSES" %}
    
    # Simple regex for standard static names:
    pattern_static = re.compile(r'<i\s+data-lucide="([\w-]+)"\s+class="([^"]*)"[^>]*>\s*</i>')
    
    # Regex for reversed attribute order: class="..." data-lucide="..."
    pattern_static_rev = re.compile(r'<i\s+class="([^"]*)"\s+data-lucide="([\w-]+)"[^>]*>\s*</i>')
    
    # Regex for dynamic ones like data-lucide="{{ item.icon|default:'circle' }}"
    pattern_dynamic = re.compile(r'<i\s+data-lucide="({{.*?}})"\s+class="([^"]*)"[^>]*>\s*</i>')
    
    count = 0
    
    for root, _, files in os.walk('templates'):
        if 'icons' in root: continue # skip the generated icons directory itself
        for file in files:
            if not file.endswith('.html'): continue
            
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original = content
            
            def replace_static(m):
                icon_name = m.group(1)
                classes = m.group(2)
                return f'{{% include "icons/{icon_name}.html" with class="{classes}" %}}'

            def replace_static_rev(m):
                classes = m.group(1)
                icon_name = m.group(2)
                return f'{{% include "icons/{icon_name}.html" with class="{classes}" %}}'

            def replace_dynamic(m):
                django_var = m.group(1)
                classes = m.group(2)
                # Since it's like {{ item.icon|default:'circle' }}, we can't easily concat inside the string 
                # but we can use Django's {% with %} block, or we just leave it for manual if it's too complex.
                # Actually, wait, item.icon is a variable.
                # We can do: <span class="{classes}">{% include "icons/placeholder.html" %}</span>
                # Let's just print a warning for dynamic ones so I can fix them manually.
                print(f"WARNING: Dynamic icon found in {filepath}: {django_var}")
                return m.group(0)
            
            content = pattern_static.sub(replace_static, content)
            content = pattern_static_rev.sub(replace_static_rev, content)
            content = pattern_dynamic.sub(replace_dynamic, content)
            
            if content != original:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                count += 1
                print(f"Migrated {filepath}")
                
    print(f"Total files migrated: {count}")

if __name__ == '__main__':
    migrate_icons()
