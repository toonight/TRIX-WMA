
import re
from pathlib import Path

def main():
    article_path = Path("d:/Projets/2026/TRIX-WMA/docs/article.html")
    b64_path = Path("d:/Projets/2026/TRIX-WMA/gold_b64_utf8.txt")
    
    print("Reading files...")
    with open(article_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    with open(b64_path, "r", encoding="utf-8") as f:
        new_src = f.read().strip()
        
    # Replace Image
    # Target alt text substr: "Gold — Similar CAGR to Buy & Hold"
    # Regex to find the src attribute of this img tag
    
    pattern = r'(<img alt="Gold [^"]+"[^>]*src=")([^"]+)(")'
    
    match = re.search(pattern, content)
    if not match:
        print("Error: Could not find Gold image tag.")
        return
        
    print("Found Gold image tag. Replacing src...")
    # match.group(2) is the old b64
    new_content = content[:match.start(2)] + new_src + content[match.end(2):]
    
    # Replace Text Statistics
    # +6.5% -> +9.2%
    # +0.7% -> +3.4%
    # We need to be careful not to replace other 6.5s.
    # The table row context:
    # <td><strong>Gold</strong></td>
    # <td style="text-align: center;">+6.5%</td>
    
    table_pattern = r'(<td><strong>Gold</strong></td>\s*<td[^>]*>)\+6\.5%</td>'
    if re.search(table_pattern, new_content):
        print("Found Gold CAGR +6.5%. Updating to +9.2%...")
        new_content = re.sub(table_pattern, r'\g<1>+9.2%</td>', new_content)
    else:
        print("Warning: Could not find Gold CAGR +6.5% to update.")

    alpha_pattern = r'(<td><strong>Gold</strong></td>.*?<td[^>]*>\+5\.8%</td>\s*<td[^>]*>)\+0\.7%</td>'
    # Need dotall for multiline matching
    if re.search(alpha_pattern, new_content, re.DOTALL):
        print("Found Gold Alpha +0.7%. Updating to +3.4%...")
        new_content = re.sub(alpha_pattern, r'\g<1>+3.4%</td>', new_content, flags=re.DOTALL)
    else:
        print("Warning: Could not find Gold Alpha +0.7% to update.")

    print("Writing updated article...")
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Done.")

if __name__ == "__main__":
    main()
