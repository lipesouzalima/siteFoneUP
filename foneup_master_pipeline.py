import os
import re
import urllib.request
import argparse

"""
FoneUP - Master Pipeline de Migração e Sanitização
Uso: Coloque este script dentro da raiz do Landing Pages (junto das páginas) e execute:
python3 foneup_master_pipeline.py --folder "nome-da-pasta" --modelo "iphone17" --nice-name "iPhone 17"
"""

def process_landing_page(folder, foneup_code, nice_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, folder, 'index.html')
    
    if not os.path.exists(html_path):
        print(f"Erro: index.html não encontrado em {folder}")
        return

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    img_dir = f"{folder}_files"
    img_dir_path = os.path.join(base_dir, folder, img_dir)
    if not os.path.exists(img_dir_path):
        os.makedirs(img_dir_path)

    # 1. Strip raw html duplicates inside _files (if user dumped them there)
    for root, dirs, files in os.walk(img_dir_path):
        for file in files:
            if file.endswith('.html'):
                os.remove(os.path.join(root, file))
                print(f"Lixo limpo: {os.path.join(root, file)}")

    # 2. Extract and download all external assets
    pattern = r'(?:https://www\.iplace\.com\.br/)?file/general/([^"\'\s>\)?]+?\.(?:png|jpg|jpeg|svg|webp|mp4|gif))(?:\?[a-zA-Z0-9]+)?'
    matches = re.finditer(pattern, content)

    url_map = {}
    for m in matches:
        full_match = m.group(0)
        filename = m.group(1).split('/')[-1]
        download_url = 'https://www.iplace.com.br/file/general/' + m.group(1)
        url_map[full_match] = (download_url, filename)

    print(f"Encontrados {len(url_map)} assets iPlace.")

    for original_str, (url, filename) in url_map.items():
        new_name = filename
        
        # Mapeamento e limpeza do prefixo nativo
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
            
        new_path = os.path.join(img_dir_path, new_name)
        
        # Faz o download das imagens (Preservando a Resolução Nativa Apple - SEM Pillow/Resize)
        if not os.path.exists(new_path):
            try:
                # print(f"Baixando: {url}")
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as response, open(new_path, 'wb') as out_file:
                    out_file.write(response.read())
            except Exception as e:
                print(f"Falha ao baixar {url}: {e}")
                continue
                
        local_rel_path = f'./{img_dir}/{new_name}'
        content = content.replace(original_str, local_rel_path)

    # 3. Purgar Fingerprints de Download ("saved from url")
    content = re.sub(r'<!--\s*saved from url=.*?\s*-->', '', content, flags=re.IGNORECASE)

    # 4. Fallback Seguro Mobile (WebKit bug fix para imagens 2X explodindo)
    # Transforma 'src="...-2x.png"' em 'src="...1x.png"'
    pattern_2x = r'(src\s*=\s*["\'][^"\']*)-2x(\.(?:png|jpg|jpeg|webp|gif)["\'])'
    content = re.sub(pattern_2x, r'\1\2', content)

    # 5. Converter rotas absolutas antigas para arquivo local
    content = content.replace('https://www.iplace.com.br/file/general/', f'./{img_dir}/')
    content = content.replace('file/general/', f'./{img_dir}/')

    # 6. Remover Scripts de Tracking e Monitoramento de Análise Institucional
    content = re.sub(r'<script>\s*try\s*\{\s*const\s*referrer\s*=\s*document\.referrer;.*?catch\s*\(err\)\s*\{\}\s*</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'const refUrl = new URL\(referrer\);.*?if \(refUrl\.origin\.includes.*?\}', '', content, flags=re.DOTALL)

    # 7. Limpeza e Automação de Links Comerciais FoneUP
    content = re.sub(r'href="https://www\.iplace\.com\.br/?.*?"', lambda m: 'href="https://www.foneup.com.br/iphone"' if 'cat' in m.group(0) else 'href="https://www.foneup.com.br"', content)

    # 8. Injeção de Roteamento Padrão FoneUP na Vercel
    content = re.sub(r'<!--\s*<base[^>]*>\s*-->', '', content)
    content = re.sub(r'<base[^>]*>', '', content)
    base_tag = f'<base href="/{folder}/" target="_top">'
    content = re.sub(r'(?i)(<head[^>]*>)', r'\1\n    ' + base_tag, content, count=1)

    # 9. Injeção Silenciosa do Frame de SEO FoneUP
    if '<title>' not in content.lower():
        seo_injection = f"""<title>FoneUP | Compre o novo {nice_name}</title>
    <meta name="description" content="Descubra o novo {nice_name} na FoneUP. Desempenho absurdo, câmeras avançadas e o melhor ecossistema do mercado. Compre agora com as melhores condições e entrega veloz.">"""
        
        if '<meta charset="UTF-8">' in content:
            content = content.replace('<meta charset="UTF-8">', f'<meta charset="UTF-8">\n    {seo_injection}')
        elif '<head>' in content:
            content = content.replace('<head>', f'<head>\n    {seo_injection}')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[{nice_name}] Sanitização completa e payload injetado com sucesso!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FoneUP Universal Landing Page Migrator")
    parser.add_argument("--folder", required=True, help="Nome do diretório (ex: macbook-pro)")
    parser.add_argument("--modelo", required=True, help="Prefixo dos arquivos (ex: mpro)")
    parser.add_argument("--nice-name", required=True, help="Nome Bonito para SEO (ex: MacBook Pro 16)")
    args = parser.parse_args()
    
    process_landing_page(args.folder, args.modelo, args.nice_name)
