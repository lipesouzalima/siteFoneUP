import os

repo_dir = '/home/lipesouzalima/Landing Pages/siteFoneUP'

def rename_and_patch(page_folder, files_folder, file_prefix, new_file_prefix):
    img_dir = os.path.join(repo_dir, page_folder, files_folder)
    html_file = os.path.join(repo_dir, page_folder, "index.html")
    
    renamed_count = 0
    # 1. Rename files in the dictionary
    if os.path.exists(img_dir):
        for filename in os.listdir(img_dir):
            if filename.startswith(file_prefix):
                new_name = filename.replace(file_prefix, new_file_prefix, 1)
                os.rename(os.path.join(img_dir, filename), os.path.join(img_dir, new_name))
                renamed_count += 1
                
    # 2. Patch HTML
    if os.path.exists(html_file):
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        content = content.replace(file_prefix, new_file_prefix)
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
    print(f"[{page_folder}] Renamed {renamed_count} files and patched HTML.")

rename_and_patch("iphone-air", "iphone-air_files", "iphoneair-", "foneup-iphoneair-")
rename_and_patch("iphone-17-pro", "iphone-17-pro_files", "iphone17p-", "foneup-iphone17p-")
