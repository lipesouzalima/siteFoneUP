import os
import re

base_dir = '/home/lipesouzalima/Landing Pages/siteFoneUP'

# Model name mappings for generic nice titles
model_titles = {
    'iphone-air': 'iPhone Air',
    'iphone-17-pro': 'iPhone 17 Pro',
    'iphone-17': 'iPhone 17',
    'iphone-17e': 'iPhone 17e',
    'iphone-16-pro': 'iPhone 16 Pro',
    'iphone-16': 'iPhone 16',
    'iphone-16e': 'iPhone 16e',
    'iphone-15': 'iPhone 15',
    'iphone-14': 'iPhone 14',
    'iphone-13': 'iPhone 13'
}

for folder, nice_name in model_titles.items():
    html_path = os.path.join(base_dir, folder, 'index.html')
    if not os.path.exists(html_path):
        continue

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove all 'saved from' comments anywhere in the file
    content = re.sub(r'<!--\s*saved from url=.*?\s*-->', '', content, flags=re.IGNORECASE)

    # 2. Add SEO Title and Meta description if not present
    if '<title>' not in content.lower():
        seo_injection = f"""<title>FoneUP | Compre o novo {nice_name}</title>
    <meta name="description" content="Descubra o novo {nice_name} na FoneUP. Desempenho absurdo, câmeras avançadas e o melhor ecossistema do mercado. Compre agora com as melhores condições.">"""
        
        # Inject right after <head> or <meta charset>
        if '<meta charset="UTF-8">' in content:
            content = content.replace('<meta charset="UTF-8">', f'<meta charset="UTF-8">\n    {seo_injection}')
        elif '<head>' in content:
            content = content.replace('<head>', f'<head>\n    {seo_injection}')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"[{folder}] Sanitized and injected SEO.")
