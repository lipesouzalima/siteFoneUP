import urllib.request
import re
import os
import concurrent.futures

models = {
    'iphone-air': [('iphoneair', 'iphoneair')],
    'iphone-17-pro': [('iphone17p', 'iphone17pro'), ('iphone17pro', 'iphone17pro')],
    'iphone-17': [('iphone17', 'iphone17')],
    'iphone-17e': [('iphone17e', 'iphone17e')],
    'iphone-16-pro': [('iphone16p', 'iphone16pro'), ('iphone16pro', 'iphone16pro')],
    'iphone-16': [('iphone16', 'iphone16')],
    'iphone-16e': [('iphone16e', 'iphone16e')]
}

base_dir = '/home/lipesouzalima/Landing Pages/siteFoneUP'

def download_image(args):
    img_dir, mappings, suffix = args
    foneup_code = mappings[0][1]
    new_name = f"foneup-{foneup_code}-{suffix}"
    out_path = os.path.join(img_dir, new_name)
    
    orig_suffix = suffix.replace('-', '_')
    
    for iplace_code, _ in mappings:
        for prefix in [f"iplaceprd_130126_{iplace_code}_", f"iplaceprd_{iplace_code}_"]:
            orig_name = f"{prefix}{orig_suffix}"
            url = f"https://www.iplace.com.br/file/general/{orig_name}"
            
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                    with open(out_path, 'wb') as out_f:
                        out_f.write(data)
                    return (new_name, True, None)
            except Exception as e:
                pass
                
    return (new_name, False, "Not found anywhere")

for folder, mappings in models.items():
    html_path = os.path.join(base_dir, folder, 'index.html')
    if not os.path.exists(html_path):
        continue

    with open(html_path, 'r') as f:
        html = f.read()

    foneup_code = mappings[0][1]
    pattern = r'foneup-' + foneup_code + r'-([^"\'\s>\)?]+\.(?:png|jpg|jpeg|webp|mp4))'
    matches = set(re.findall(pattern, html))
    
    print(f"[{folder}] Found {len(matches)} files to restore.")
    img_dir = os.path.join(base_dir, folder, f"{folder}_files")
    
    args_list = [(img_dir, mappings, suffix) for suffix in matches]
    
    success_count = 0
    fail_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        for new_name, success, err in executor.map(download_image, args_list):
            if success:
                success_count += 1
            else:
                fail_count += 1
                # print(f"Failed: {new_name}")
                
    print(f"[{folder}] Restored: {success_count}, Failed: {fail_count}")
