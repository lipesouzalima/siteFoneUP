import os
import re
import urllib.request
import urllib.parse
import argparse
import subprocess
import concurrent.futures

"""
FoneUP - Pipeline Master para Landing Pages Diretas da Apple
"""

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

EMPTY_GIF = "data:image/gif;base64,R0lGODlhAQABAHAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="

def clean_asset_filename(raw_url, foneup_code):
    clean = raw_url.split('?')[0].split('#')[0]
    filename = clean.split('/')[-1]
    
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
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, 'wb') as f:
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

    print(f"[{nice_name}] Iniciando processamento do zero...")

    # 1. Remover Apple Global Nav Header
    html = re.sub(r'(<body[^>]*>).*?(<input[^>]*id="ac-ln-menustate")', r'\1\n\t\2', html, flags=re.DOTALL)
    
    # 2. SEÇÃO 1: Remover Rodapé Institucional da Apple
    html = re.sub(r'<nav\s+class="ac-gf-breadcrumbs".*?</footer>', r'</div>\n\t</footer>', html, flags=re.DOTALL)
    html = re.sub(r'<nav\s+class="ac-gf-directory".*?</footer>', r'</div>\n\t</footer>', html, flags=re.DOTALL)
    html = re.sub(r'<section\s+class="ac-gf-footer".*?</footer>', r'</div>\n\t</footer>', html, flags=re.DOTALL)
    html = re.sub(r'<h2\s+class="ac-gf-label"[^>]*>.*?</h2>', '', html, flags=re.DOTALL)

    # 3. SEÇÃO 2: Remover seção index vazia
    html = re.sub(r'<section\s+class="section\s+section-index".*?</section>', '', html, flags=re.DOTALL)
    html = html.replace('&quot;.section-index&quot;', '&quot;#ac-globalfooter&quot;')
    html = html.replace('".section-index"', '"#ac-globalfooter"')

    # 4. Remover telemetria e analytics
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

    # 5. Coletar e Mapear Assets
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

        if any(skip in full_url for skip in ['analytics', 'metrics', 'data-relay', 'globalheader', 'autopricing', 'localeswitcher']):
            continue

        clean_name = clean_asset_filename(raw_url, foneup_code)
        local_file_path = os.path.join(img_dir_path, clean_name)
        local_rel_path = f'./{img_dir}/{clean_name}'
        
        url_to_local_map[raw_url] = (full_url, local_file_path, local_rel_path, clean_name)
        download_tasks.append((full_url, local_file_path))

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

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(download_asset, u, p) for u, p in download_tasks]
        concurrent.futures.wait(futures)

    # 6. Processar CSS locais
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

        if 'globalfooter' in css_file:
            css_content = re.sub(r'@font-face\{[^}]+\}', '', css_content)

        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)

    # 7. Substituir URLs no HTML
    for raw_url, (full_url, local_file_path, local_rel_path, clean_name) in url_to_local_map.items():
        html = html.replace(raw_url, local_rel_path)

    html = html.replace('/105/media/us/airpods-max/2024/e8f376d6-82b2-40ca-8a22-5f87de755d6b/anim/highlights-anc/', f'./{img_dir}/highlights-anc/')
    html = html.replace('/105/media/us/airpods-max/2024/e8f376d6-82b2-40ca-8a22-5f87de755d6b/anim/max-loop/', f'./{img_dir}/max-loop/')

    # 8. Garantir base64 perfeito
    html = re.sub(r'<source\s+data-empty\s+srcset="[^"]*"\s+media="\(min-width:0px\)"\s*/>',
                  f'<source data-empty srcset="{EMPTY_GIF}" media="(min-width:0px)" />',
                  html)

    # Fix Print 1: Imagem do primeiro card da galeria
    html = re.sub(r'(<picture id="overview-media-card-anc-startframe-1"[^>]*>)\s*<source data-empty[^>]*>', r'\1', html)
    html = re.sub(r'(<picture id="overview-media-card-anc-endframe-1"[^>]*>)\s*<source data-empty[^>]*>', r'\1', html)

    # 9. Substituições Comerciais & Fala de Marca (FoneUP)
    html = html.replace('content="Apple (Brasil)"', 'content="FoneUP"')
    html = html.replace('content="@Apple"', 'content="@foneup"')
    html = html.replace('Motivos para comprar<br /> seus AirPods na Apple.', 'Motivos para comprar<br /> seus AirPods na FoneUP.')
    html = html.replace('Motivos para comprar seus AirPods na Apple.', 'Motivos para comprar seus AirPods na FoneUP.')
    html = html.replace('Na Apple Store ou online.', 'Na FoneUP ou online.')
    html = html.replace('Na Apple Store ou online.', 'Na FoneUP ou online.')
    html = html.replace('Especialistas da Apple estão a postos', 'Especialistas da FoneUP estão a postos')
    html = html.replace('Especialistas da Apple estão a postos', 'Especialistas da FoneUP estão a postos')
    html = html.replace('comprar online ou na Apple Store.', 'comprar online ou na FoneUP.')
    html = html.replace('comprar online ou na Apple Store.', 'comprar online ou na FoneUP.')
    html = html.replace('aria-label="Anterior, galeria Por que Apple"', 'aria-label="Anterior, galeria Por que FoneUP"')
    html = html.replace('aria-label="Próximo, galeria Por que Apple"', 'aria-label="Próximo, galeria Por que FoneUP"')

    # Remover o 4º card (App Apple Store / 'Uma experiência de compra...')
    html = re.sub(r'<li class="card tile tile-rounded card-hover icon-card gallery-item" id="gallery-item-apple-store".*?</li>\s*(?=<li|<button|</ul>)', '', html, flags=re.DOTALL)

    # Sanitização de Links
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

    # 10. Fallback Seguro Mobile
    pattern_2x = r'(src\s*=\s*["\'][^"\']*)-2x(\.(?:png|jpg|jpeg|webp|gif)["\'])'
    html = re.sub(pattern_2x, r'\1\2', html)

    html = re.sub(r\'<div class="media-container"[^>]*>.*?</section>\', hero_static.strip() + \'
		</section>\', html, flags=re.DOTALL)

    # 11. CSS Otimizado
    custom_styles = """
    <style>
        .subsection-hifi-sound .subsection-header,
        .subsection-hifi-sound .subsection-headline,
        .subsection-hifi-sound .subsection-header-subheadline {
            text-align: center !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }
        .section-contrast {
            padding-bottom: 40px !important;
            margin-bottom: 0 !important;
        }
        #ac-globalfooter {
            padding-top: 30px !important;
            margin-top: 0 !important;
        }
        .overview-media-card-anc-startframe img {
            opacity: 1 !important;
            display: block !important;
        }
        .section-product-stories .scroll-gallery .gallery-item-content.auto-detect {
            background-color: #f5f5f7 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            overflow: hidden !important;
        }
        .section-product-stories .scroll-gallery .gallery-item-content.auto-detect .gallery-item-image,
        .section-product-stories .scroll-gallery .gallery-item-content.auto-detect img {
            max-width: 100% !important;
            height: 100% !important;
            object-fit: contain !important;
            object-position: center !important;
            margin: 0 auto !important;
        }
    </style>
    """
    html = re.sub(r'(?i)(</head>)', custom_styles + r'\n\1', html, count=1)

    # 12. SEO, Title e Base Tag
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

    with open(target_html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    # 13. Scripts Multiplataforma
    head_js_file = os.path.join(img_dir_path, 'foneup-airpodsmax2-head.built.js')
    if os.path.exists(head_js_file):
        with open(head_js_file, 'r', encoding='utf-8') as f:
            hjs = f.read()
        injector = ';(function(){try{var d=document.documentElement;d.classList.remove("no-js","no-enhanced","no-inline-media","no-touch");d.classList.add("js","enhanced","inline-media");}catch(e){}})();\n'
        if 'enhanced' not in hjs[:200]:
            hjs = injector + hjs
            with open(head_js_file, 'w', encoding='utf-8') as f:
                f.write(hjs)

    main_js_file = os.path.join(img_dir_path, 'foneup-airpodsmax2-main.built.js')
    if os.path.exists(main_js_file):
        with open(main_js_file, 'r', encoding='utf-8') as f:
            mjs = f.read()
        mjs = mjs.replace('_fallbackToStatic(){this._items.forEach(e=>{e.showStaticFallback()}),document.documentElement.classList.toggle(this.model.FEATURE_CLASS_FOCUSABLE,!1)}', '_fallbackToStatic(){}')
        with open(main_js_file, 'w', encoding='utf-8') as f:
            f.write(mjs)

    print(f"[{nice_name}] Processamento concluído com sucesso!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="FoneUP Apple Landing Page Master Pipeline")
    parser.add_argument('--source', required=True, help="Caminho do arquivo HTML original do Apple")
    parser.add_argument('--folder', required=True, help="Nome da pasta destino (ex: airpods-max-2)")
    parser.add_argument('--modelo', required=True, help="Código do modelo FoneUP (ex: airpodsmax2)")
    parser.add_argument('--nice-name', required=True, help="Nome amigável (ex: AirPods Max 2)")

    args = parser.parse_args()
    process_apple_landing_page(args.source, args.folder, args.modelo, args.nice_name)
