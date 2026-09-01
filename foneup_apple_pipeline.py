import os
import re
import urllib.request
import urllib.parse
import argparse
import subprocess
import concurrent.futures

"""
FoneUP - Pipeline para Landing Pages Diretas da Apple
Sanitiza e migra páginas capturadas diretamente do www.apple.com/br/
"""

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def clean_asset_filename(raw_url, foneup_code):
    clean = raw_url.split('?')[0].split('#')[0]
    filename = clean.split('/')[-1]
    
    # Se for arquivo de estilo regional (/br/...)
    if '/br/' in raw_url and 'overview.built.css' in filename:
        filename = 'overview-locale.built.css'
    elif '/br/' in raw_url and 'main.built.css' in filename:
        filename = 'main-locale.built.css'
        
    filename = re.sub(r'__[a-z0-9]{10,16}', '', filename)
    filename = re.sub(r'^[a-z0-9]{10,16}_', '', filename)
    filename = re.sub(r'apple', 'foneup', filename, flags=re.IGNORECASE)
    filename = re.sub(r'[_]+', '-', filename)
    
    if filename.startswith('-'):
        filename = filename[1:]
        
    if not filename.startswith(f"foneup-{foneup_code}-"):
        filename = f"foneup-{foneup_code}-{filename}"
        
    return filename

def download_asset(url, dest_path):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return True
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=25) as resp, open(dest_path, 'wb') as f:
            f.write(resp.read())
        return True
    except Exception as e:
        return False

def process_apple_landing_page(source_html_path, folder, foneup_code, nice_name, push=True):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_folder_path = os.path.join(base_dir, folder)
    target_html_path = os.path.join(target_folder_path, 'index.html')
    img_dir = f"{folder}_files"
    img_dir_path = os.path.join(target_folder_path, img_dir)
    
    os.makedirs(target_folder_path, exist_ok=True)
    os.makedirs(img_dir_path, exist_ok=True)
    
    with open(source_html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    print(f"[{nice_name}] Iniciando processamento a partir do Apple Source...")

    # 1. Remover Global Header do site da Apple (tudo entre <body...> e o início da navegação do produto)
    html = re.sub(r'(<body[^>]*>).*?(<input[^>]*id="ac-ln-menustate"|<nav[^>]*id="ac-localnav")', r'\1\n\t\2', html, flags=re.DOTALL)
    
    # 2. Remover o footer institucional/sitemap e copyright da Apple (manter apenas notas/disclaimers sosumi)
    html = re.sub(r'<nav\s+class="ac-gf-breadcrumbs".*?</footer>', r'</div>\n\t</footer>', html, flags=re.DOTALL)
    html = re.sub(r'<nav\s+class="ac-gf-directory".*?</footer>', r'</div>\n\t</footer>', html, flags=re.DOTALL)
    
    # 3. Remover scripts de telemetria, analytics, tags hreflang e dados globais residuais
    html = re.sub(r'<link[^>]*globalheader\.css[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<script[^>]*globalheader[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<script[^>]*metrics[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<script[^>]*ac-analytics[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<script[^>]*data-relay[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<script[^>]*localeswitcher[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<script[^>]*autopricing[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<script\s+id="__ACGH_DATA__"[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<script\s+id="globalheader-data"[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<meta\s+name="globalnav-[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<link\s+rel="alternate"[^>]*>', '', html, flags=re.IGNORECASE)

    # 4. Remover <source data-empty ...> que bloqueiam a renderização direta das imagens de fallback
    html = re.sub(r'<source\s+data-empty[^>]*>', '', html, flags=re.IGNORECASE)

    # 5. Coletar e Mapear todos os Assets (HTML + CSS)
    all_raw_urls = set()
    
    for m in re.finditer(r'(?:srcset|data-srcset)\s*=\s*["\']([^"\'>]+)["\']', html):
        raw_val = m.group(1)
        for entry in raw_val.split(','):
            entry = entry.strip()
            if entry:
                url_part = entry.split(' ')[0].strip()
                if url_part and not url_part.startswith('data:'):
                    all_raw_urls.add(url_part)

    for m in re.finditer(r'(?:src|href|content|poster|data-src)\s*=\s*["\']([^"\'>\s]+)["\']', html):
        val = m.group(1).strip()
        if not val.startswith('data:') and not val.startswith('#') and not val.startswith('mailto:') and not val.startswith('tel:'):
            if any(val.lower().endswith(ext) or (ext + '?') in val.lower() or ext in val.lower() for ext in ['.png', '.jpg', '.jpeg', '.svg', '.webp', '.mp4', '.gif', '.css', '.js', '.woff', '.woff2', '.ttf']):
                all_raw_urls.add(val)

    for m in re.finditer(r'url\(["\']?([^"\'\)]+)["\']?\)', html):
        val = m.group(1).strip()
        if not val.startswith('data:'):
            all_raw_urls.add(val)

    print(f"[{nice_name}] Total de referências encontradas: {len(all_raw_urls)}")

    url_to_local_map = {}
    download_tasks = []

    for raw_url in all_raw_urls:
        if raw_url.startswith('//'):
            full_url = 'https:' + raw_url
        elif raw_url.startswith('/'):
            full_url = 'https://www.apple.com' + raw_url
        elif raw_url.startswith('http://') or raw_url.startswith('https://'):
            full_url = raw_url
        else:
            full_url = 'https://www.apple.com/br/airpods-max/' + raw_url

        if 'analytics' in full_url or 'metrics' in full_url or 'data-relay' in full_url or 'globalheader' in full_url:
            continue

        clean_name = clean_asset_filename(raw_url, foneup_code)
        local_file_path = os.path.join(img_dir_path, clean_name)
        local_rel_path = f'./{img_dir}/{clean_name}'
        
        url_to_local_map[raw_url] = (full_url, local_file_path, local_rel_path, clean_name)
        download_tasks.append((full_url, local_file_path))

    # Baixar vídeos MP4 das animações interativas
    video_resolutions = ['large.mp4', 'large_2x.mp4', 'medium.mp4', 'small.mp4', 'xlarge.mp4']
    video_folders = [
        ('https://www.apple.com/105/media/us/airpods-max/2024/e8f376d6-82b2-40ca-8a22-5f87de755d6b/anim/highlights-anc/', 'highlights-anc'),
        ('https://www.apple.com/105/media/us/airpods-max/2024/e8f376d6-82b2-40ca-8a22-5f87de755d6b/anim/max-loop/', 'max-loop'),
    ]
    for base_v_url, v_folder in video_folders:
        for res_name in video_resolutions:
            full_v_url = base_v_url + res_name
            dest_v_file = os.path.join(img_dir_path, v_folder, res_name)
            download_tasks.append((full_v_url, dest_v_file))

    print(f"[{nice_name}] Baixando {len(download_tasks)} assets em paralelo...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(download_asset, u, p) for u, p in download_tasks]
        concurrent.futures.wait(futures)

    # 6. Processar CSS locais para baixar sub-assets (fontes, SVGs em url())
    css_files = [f for f in os.listdir(img_dir_path) if f.endswith('.css')]
    for css_file in css_files:
        css_path = os.path.join(img_dir_path, css_file)
        with open(css_path, 'r', encoding='utf-8', errors='ignore') as f:
            css_content = f.read()

        css_sub_urls = re.findall(r'url\(["\']?([^"\'\)]+)["\']?\)', css_content)
        for sub_url in css_sub_urls:
            if sub_url.startswith('data:'):
                continue
            
            if sub_url.startswith('http'):
                full_sub_url = sub_url
            elif sub_url.startswith('/'):
                full_sub_url = 'https://www.apple.com' + sub_url
            else:
                full_sub_url = urllib.parse.urljoin('https://www.apple.com/v/airpods-max/k/built/styles/', sub_url)

            sub_clean_name = clean_asset_filename(sub_url, foneup_code)
            sub_local_path = os.path.join(img_dir_path, sub_clean_name)
            
            download_asset(full_sub_url, sub_local_path)
            css_content = css_content.replace(sub_url, f'./{sub_clean_name}')

        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)

    # 7. Substituir URLs no HTML
    for raw_url, (full_url, local_file_path, local_rel_path, clean_name) in url_to_local_map.items():
        html = html.replace(raw_url, local_rel_path)

    # Mapear caminhos de vídeo das animações
    html = html.replace('/105/media/us/airpods-max/2024/e8f376d6-82b2-40ca-8a22-5f87de755d6b/anim/highlights-anc/', f'./{img_dir}/highlights-anc/')
    html = html.replace('/105/media/us/airpods-max/2024/e8f376d6-82b2-40ca-8a22-5f87de755d6b/anim/max-loop/', f'./{img_dir}/max-loop/')

    # 8. Sanitização de Links Comerciais & Navegação
    html = re.sub(r'https?://(?:www\.)?apple\.com/br/shop/goto/buy_airpods[^\s"\'<>]*', 'https://www.foneup.com.br/airpods', html, flags=re.IGNORECASE)
    html = re.sub(r'/br/shop/goto/buy_airpods[^\s"\'<>]*', 'https://www.foneup.com.br/airpods', html, flags=re.IGNORECASE)
    html = re.sub(r'https?://(?:www\.)?apple\.com/br/airpods[^\s"\'<>]*', 'https://www.foneup.com.br/airpods', html, flags=re.IGNORECASE)
    html = re.sub(r'/br/airpods[^\s"\'<>]*', 'https://www.foneup.com.br/airpods', html, flags=re.IGNORECASE)
    html = re.sub(r'https?://(?:www\.)?apple\.com/br/shop[^\s"\'<>]*', 'https://www.foneup.com.br', html, flags=re.IGNORECASE)
    html = re.sub(r'/br/shop[^\s"\'<>]*', 'https://www.foneup.com.br', html, flags=re.IGNORECASE)
    html = re.sub(r'https?://(?:www\.)?apple\.com/br/?.*?"', 'https://www.foneup.com.br"', html, flags=re.IGNORECASE)
    html = re.sub(r'https?://(?:[a-zA-Z0-9_\.-]+\.)?apple\.com[^\s"\'<>]*', 'https://www.foneup.com.br', html, flags=re.IGNORECASE)
    html = re.sub(r'/br/search[^\s"\'<>]*', 'https://www.foneup.com.br', html, flags=re.IGNORECASE)
    html = re.sub(r'support\.apple\.com(?:/[a-zA-Z0-9_\.-]+)*', 'www.foneup.com.br', html, flags=re.IGNORECASE)
    html = re.sub(r'apple\.com', 'foneup.com.br', html, flags=re.IGNORECASE)

    # 9. Fallback Seguro Mobile (WebKit bug fix para imagens 2X)
    pattern_2x = r'(src\s*=\s*["\'][^"\']*)-2x(\.(?:png|jpg|jpeg|webp|gif)["\'])'
    html = re.sub(pattern_2x, r'\1\2', html)

    # 10. Ajuste Responsivo Mobile para Centralizar o Título "Inovação em alto e bom som."
    custom_styles = """
    <style>
        .subsection-hifi-sound .subsection-header,
        .subsection-hifi-sound .subsection-headline,
        .subsection-hifi-sound .subsection-header-subheadline {
            text-align: center !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }
    </style>
    """
    html = re.sub(r'(?i)(</head>)', custom_styles + r'\n\1', html, count=1)

    # 11. SEO, Title e Roteamento Vercel
    html = re.sub(r'<title>.*?</title>', f'<title>FoneUP | Compre o novo {nice_name}</title>', html, flags=re.DOTALL)
    if '<title>' not in html:
        html = re.sub(r'(?i)(<head[^>]*>)', r'\1\n    <title>FoneUP | Compre o novo ' + nice_name + '</title>', html, count=1)

    html = re.sub(r'<meta\s+name="description"[^>]*>', '', html, flags=re.IGNORECASE)
    seo_desc = f'<meta name="description" content="Descubra o novo {nice_name} na FoneUP. Áudio de alta fidelidade, Cancelamento Ativo de Ruído de nível profissional, novas cores e USB-C. Compre agora com as melhores condições e entrega veloz.">'
    html = re.sub(r'(?i)(<head[^>]*>)', r'\1\n    ' + seo_desc, html, count=1)

    html = re.sub(r'<!--\s*<base[^>]*>\s*-->', '', html)
    html = re.sub(r'<base[^>]*>', '', html)
    base_tag = f'<base href="/{folder}/" target="_top">'
    html = re.sub(r'(?i)(<head[^>]*>)', r'\1\n    ' + base_tag, html, count=1)

    # 12. Salvar HTML Final Sanitizado
    with open(target_html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[{nice_name}] Sanitização completa e payload injetado com sucesso em {target_html_path}!")

    # 13. Automação Git e Deploy Vercel
    if push:
        print(f"[{nice_name}] Enviando alterações para GitHub / Vercel...")
        try:
            subprocess.run(['git', 'add', 'foneup_apple_pipeline.py', folder], cwd=base_dir, check=True)
            subprocess.run(['git', 'commit', '-m', f"fix(airpods-max-2): remover footer institucional, centralizar headline mobile e corrigir videos/imagens"], cwd=base_dir, check=True)
            subprocess.run(['git', 'pull', '--rebase', 'origin', 'main'], cwd=base_dir, check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], cwd=base_dir, check=True)
            print(f"[{nice_name}] Commit e deploy na Vercel disparados com sucesso!")
        except Exception as e:
            print(f"Aviso ao realizar git push: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="FoneUP Apple Landing Page Master Pipeline")
    parser.add_argument('--source', required=True, help="Caminho do arquivo HTML original do Apple")
    parser.add_argument('--folder', required=True, help="Nome da pasta destino (ex: airpods-max-2)")
    parser.add_argument('--modelo', required=True, help="Código do modelo FoneUP (ex: airpodsmax2)")
    parser.add_argument('--nice-name', required=True, help="Nome amigável (ex: AirPods Max 2)")
    parser.add_argument('--no-push', action='store_true', help="Não realizar git push automático")

    args = parser.parse_args()
    process_apple_landing_page(args.source, args.folder, args.modelo, args.nice_name, push=not args.no_push)
