import os
files = os.listdir('/home/lipesouzalima/Landing Pages/siteFoneUP/iphone-16e/iphone-16e_files')
from PIL import Image
for f in files:
    if f.endswith('.png') or f.endswith('.jpg'):
        with Image.open(f'/home/lipesouzalima/Landing Pages/siteFoneUP/iphone-16e/iphone-16e_files/{f}') as img:
            print(f, img.size)
            break
