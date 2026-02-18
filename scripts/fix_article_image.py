
import os

article_path = r"d:\Projets\2026\TRIX-WMA\docs\article.html"
import base64

article_path = r"d:\Projets\2026\TRIX-WMA\docs\article.html"
png_path = r"amzn_equity_curve.png"

# Read PNG and encode
with open(png_path, "rb") as f:
    b64_str = base64.b64encode(f.read()).decode('utf-8')

# Read Article
with open(article_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Target Line (1-based index 477 -> 0-based index 476)
target_idx = 476

# Verify it looks like the src line to be safe
if "src=\"data:image/png;base64," in lines[target_idx]:
    print(f"Found target line at index {target_idx}: {lines[target_idx][:50]}...")
    
    # Construct new line
    # Preserve indentation (16 spaces based on view_file output)
    new_line = f"                src=\"data:image/png;base64,{b64_str}\" />\n"
    
    lines[target_idx] = new_line
    
    # Write back
    with open(article_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Successfully patched article.html")
else:
    print(f"ERROR: Target line at index {target_idx} does not look like a src attribute:")
    print(lines[target_idx])
