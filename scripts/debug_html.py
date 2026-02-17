
import re

def debug_imgs():
    path = "docs/article.html"
    try:
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()
            
        print(f"File read: {len(html)} bytes")
        
        # Find all img tags
        imgs = re.findall(r'<img[^>]+>', html)
        print(f"Found {len(imgs)} image tags.")
        
        for i, img in enumerate(imgs):
            alt_match = re.search(r'alt="([^"]*)"', img)
            if alt_match:
                print(f"{i+1}: {alt_match.group(1)}")
            else:
                print(f"{i+1}: NO ALT")
            
            # Context
            # print(f"Tag: {img[:100]}...")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_imgs()
