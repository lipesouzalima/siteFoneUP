import os
from PIL import Image

repo_dir = '/home/lipesouzalima/Landing Pages/siteFoneUP'

def optimize_images_and_fix_names(page_folder, files_folder, old_prefix, new_prefix, max_dim=1920):
    img_dir = os.path.join(repo_dir, page_folder, files_folder)
    html_file = os.path.join(repo_dir, page_folder, "index.html")
    
    renamed_count = 0
    resized_count = 0
    
    if os.path.exists(img_dir):
        for filename in os.listdir(img_dir):
            old_path = os.path.join(img_dir, filename)
            
            # Skip non-images
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                continue
            
            # Step 1: Rename
            new_name = filename
            if old_prefix and new_prefix and filename.startswith(old_prefix):
                new_name = filename.replace(old_prefix, new_prefix, 1)
                new_path = os.path.join(img_dir, new_name)
                os.rename(old_path, new_path)
                renamed_count += 1
                current_img_path = new_path
            else:
                current_img_path = old_path
                
            # Step 2: Resize
            try:
                with Image.open(current_img_path) as img:
                    width, height = img.size
                    if width > max_dim or height > max_dim:
                        # Resize using LANCZOS for high quality
                        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                        img.save(current_img_path, optimize=True)
                        resized_count += 1
                        print(f"Resized: {new_name} (from {width}x{height})")
            except Exception as e:
                print(f"Failed to process image {new_name}: {e}")
                
    # Step 3: Patch HTML
    if old_prefix and new_prefix and os.path.exists(html_file):
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        content = content.replace(old_prefix, new_prefix)
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
    print(f"[{page_folder}] Renamed {renamed_count} files, Resized {resized_count} files.")

# Execute for Air (no rename needed, old_prefix/new_prefix = None)
optimize_images_and_fix_names("iphone-air", "iphone-air_files", None, None)

# Execute for 17 Pro (rename 'foneup-iphone17p-' to 'foneup-iphone17pro-')
optimize_images_and_fix_names("iphone-17-pro", "iphone-17-pro_files", "foneup-iphone17p-", "foneup-iphone17pro-")
