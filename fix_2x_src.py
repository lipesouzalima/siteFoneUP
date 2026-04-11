import os
import re

base_dir = '/home/lipesouzalima/Landing Pages/siteFoneUP'

for folder in os.listdir(base_dir):
    html_path = os.path.join(base_dir, folder, 'index.html')
    if not os.path.exists(html_path):
        continue

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find ALL instances of src pointing to a -2x image
    # We want to replace -2x.ext with .ext in the src string ONLY.
    
    # Regex explanation:
    # (src\s*=\s*["'].*?)-2x(\.(?:png|jpg|jpeg|webp|gif)["'])
    # Replaced with: \1\2
    
    pattern = r'(src\s*=\s*["\'][^"\']*)-2x(\.(?:png|jpg|jpeg|webp|gif)["\'])'
    
    new_content, count = re.subn(pattern, r'\1\2', content)

    if count > 0:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"[{folder}] Stripped -2x from {count} src attributes.")
