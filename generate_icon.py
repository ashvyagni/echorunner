from PIL import Image, ImageDraw
img = Image.new('RGBA', (256, 256), (15, 15, 35, 255))
d = ImageDraw.Draw(img)
d.ellipse((32, 32, 224, 224), outline=(120, 230, 255), width=16)
d.ellipse((64, 64, 192, 192), outline=(180, 140, 255), width=8)
import os
os.makedirs('assets', exist_ok=True)
img.save('assets/icon.ico', format='ICO')
img.save('assets/icon.png', format='PNG')
try:
    img.save('assets/icon.icns', format='ICNS')
except Exception as e:
    print(e)
