import os
import re

models = {
    'iphone-air': 'iphoneair',
    'iphone-17-pro': 'iphone17pro',
    'iphone-17': 'iphone17',
    'iphone-17e': 'iphone17e',
    'iphone-16-pro': 'iphone16pro',
    'iphone-16': 'iphone16',
    'iphone-16e': 'iphone16e',
    'iphone-15': 'iphone15',
    'iphone-14': 'iphone14',
    'iphone-13': 'iphone13'
}

base_dir = '/home/lipesouzalima/Landing Pages/siteFoneUP'

for folder, foneup_code in models.items():
    html_path = os.path.join(base_dir, folder, 'index.html')
    if not os.path.exists(html_path):
        continue

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pre-clean the absolute prefixes so we only deal with relative paths
    content = content.replace('https://www.iplace.com.br/file/general/', f'./{folder}_files/')
    content = content.replace('file/general/', f'./{folder}_files/')

    # Now find all instances of iplaceprd|iplaceapp that end in an extension
    pattern = r'iplace(?:prd|app)[A-Za-z0-9_-]+?\.(?:png|jpg|jpeg|svg|webp|gif|mp4)'
    matches = set(re.findall(pattern, content))

    count = 0
    for match in matches:
        new_name = match
        
        # apply existing sanitization rules from download.py
        new_name = re.sub(r'^iplaceapp-17e-\d+-', '', new_name)
        new_name = re.sub(r'^iplaceprd_\d+_[a-zA-Z0-9]+_', '', new_name)
        new_name = re.sub(r'^iplaceprd_[a-zA-Z0-9]+_', '', new_name)
        new_name = re.sub(r'iplace', '', new_name, flags=re.IGNORECASE)
        
        if new_name.startswith('_') or new_name.startswith('-'): 
            new_name = new_name[1:]
            
        if not new_name.startswith(f"foneup-{foneup_code}-"):
            if new_name.startswith(f"{foneup_code}-"):
                new_name = 'foneup-' + new_name
            else:
                new_name = f'foneup-{foneup_code}-' + new_name.replace('_', '-')
        
        # Replace strictly the text occurrence
        content = content.replace(match, new_name)
        count += 1
        
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"[{folder}] Replaced {count} unpatched iplace references.")
