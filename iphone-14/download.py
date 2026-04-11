import os
import re
import urllib.request
import concurrent.futures

html_path = 'index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

img_dir = 'iphone-14_files'
if not os.path.exists(img_dir):
    os.makedirs(img_dir)

# Find all relative or absolute iplace paths. Handles query strings.
pattern = r'(?:https://www\.iplace\.com\.br/)?file/general/([^"\'\s>\)?]+?\.(?:png|jpg|jpeg|svg|webp|mp4))(?:\?[a-zA-Z0-9]+)?'
matches = list(re.finditer(pattern, content))

url_map = {}
for m in matches:
    full_match = m.group(0)
    filename = m.group(1).split('/')[-1]
    download_url = 'https://www.iplace.com.br/file/general/' + m.group(1)
    url_map[full_match] = (download_url, filename)

print(f"Found {len(url_map)} unique external assets.")

def process_file(entry):
    original_str, (url, filename) = entry
    
    new_name = filename
    new_name = re.sub(r'^iplaceprd_\d+_iphone14_', '', new_name)
    new_name = re.sub(r'iplace', '', new_name, flags=re.IGNORECASE)
    if new_name.startswith('_') or new_name.startswith('-'): new_name = new_name[1:]
    
    if not new_name.startswith('foneup-iphone14-'):
        if new_name.startswith('iphone14-'):
            new_name = 'foneup-' + new_name
        else:
            new_name = 'foneup-iphone14-' + new_name.replace('_', '-')
            
    new_path = os.path.join(img_dir, new_name)
    
    if not os.path.exists(new_path):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response, open(new_path, 'wb') as out_file:
                out_file.write(response.read())
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            return original_str, None
            
    return original_str, new_name

print("Downloading concurrently...")
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    results = list(executor.map(process_file, url_map.items()))

# Replace HTML synchronously
for original_str, new_name in results:
    if new_name:
        local_rel_path = f'./{img_dir}/{new_name}'
        content = content.replace(original_str, local_rel_path)

# Commercial links cleanup
content = re.sub(r'href="https://www\.iplace\.com\.br/?.*?"', lambda m: 'href="https://www.foneup.com.br/iphone"' if 'cat' in m.group(0) else 'href="https://www.foneup.com.br"', content)

# Base target explicit override
# We remove any commented base tags first
content = re.sub(r'<!--\s*<base[^>]*>\s*-->', '', content)
content = re.sub(r'<base[^>]*>', '', content)
base_tag = '<base href="/iphone-14/" target="_top">'
content = re.sub(r'(?i)(<head[^>]*>)', r'\1\n    ' + base_tag, content, count=1)

# Remove tracking scripts
content = re.sub(r'<script>\s*try\s*\{\s*const\s*referrer\s*=\s*document\.referrer;.*?catch\s*\(err\)\s*\{\}\s*</script>', '', content, flags=re.DOTALL)
content = re.sub(r'const refUrl = new URL\(referrer\);.*?if \(refUrl\.origin\.includes.*?\}', '', content, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Finished downloading and patching.")
