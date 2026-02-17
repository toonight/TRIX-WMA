
import base64
import re
import os
from pathlib import Path

def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def patch_article():
    print("--- Patching Article ---")
    
    # Paths
    base_dir = Path("d:/Projets/2026/TRIX-WMA")
    html_path = base_dir / "docs/article.html"
    img_dir = base_dir / "trix_wma_robustness/reports/figures"
    
    # Data
    ticker_map = {
        "NVDA": "NVIDIA",
        "AMZN": "Amazon",
        "GOOGL": "Google",
        "MSFT": "Microsoft",
        "META": "Meta"
    }
    
    # Parameters and Results (Hardcoded from optimization)
    # NVDA: T=8, W=20, S=10 | CAGR=54.55%
    # GOOGL: T=10, W=30, S=10 | CAGR=18.60%
    # MSFT: T=8, W=20, S=10 | CAGR=30.73%
    # META: T=8, W=25, S=10 | CAGR=32.82%
    # AMZN: T=8, W=30, S=10 | CAGR=16.21%
    
    ticker_data = {
        "NVDA": {"cagr": "54.55%", "params": "TRIX=8 / WMA=20 / Shift=10"},
        "AMZN": {"cagr": "16.21%", "params": "TRIX=8 / WMA=30 / Shift=10"},
        "GOOGL": {"cagr": "18.60%", "params": "TRIX=10 / WMA=30 / Shift=10"},
        "MSFT": {"cagr": "30.73%", "params": "TRIX=8 / WMA=20 / Shift=10"},
        "META": {"cagr": "32.82%", "params": "TRIX=8 / WMA=25 / Shift=10"},
    }

    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
            
        missing_images = []
        insertion_point_found = False
        
        # Order matters for insertion: NVDA, AMZN (exist), then GOOGL, MSFT, META
        # Actually we process all.
        
        for ticker in ["NVDA", "AMZN", "GOOGL", "MSFT", "META"]:
            name = ticker_map[ticker]
            data = ticker_data[ticker]
            print(f"Processing {ticker} ({name})...")
            
            # Update Table Stats
            # Pattern: <td><strong>TICKER</strong></td>\s*<td[^>]*>OLD_VAL</td>
            table_pattern = f'(<td><strong>{ticker}</strong></td>\\s*<td[^>]*>)([^<]*)(</td>)'
            if re.search(table_pattern, html, re.IGNORECASE):
                html = re.sub(table_pattern, f'\\g<1>{data["cagr"]}\\g<3>', html, count=1, flags=re.IGNORECASE)
                print(f"  - Table CAGR updated to {data['cagr']}.")
            else:
                print(f"  - WARNING: Could not find table row for {ticker}")

            # Prepare Image
            img_path = img_dir / f"equity_curves_{ticker}.png"
            if not img_path.exists():
                print(f"  - ERROR: Image not found: {img_path}")
                continue
                
            b64 = get_base64_image(img_path)
            data_uri = f"data:image/png;base64,{b64}"
            
            # Try to replace existing image
            # Pattern: <img alt="NVIDIA ... Growth Profile..." src="...">
            # We look for 'alt="{name} ... Growth Profile'
            img_pattern = f'(<img[^>]*alt="[^"]*{name}[^"]*Growth Profile[^"]*"[^>]*src=")([^"]*)(")'
            
            if re.search(img_pattern, html, re.IGNORECASE):
                html = re.sub(img_pattern, f'\\g<1>{data_uri}\\g<3>', html, count=1, flags=re.IGNORECASE)
                print(f"  - Image patched.")
            else:
                print(f"  - Image NOT found. Will queue for insertion.")
                # Create HTML chunk
                alt_text = f"{name} — Growth Profile. {data['params']}. CAGR {data['cagr']} vs Buy & Hold."
                chunk = f'<p><img alt="{alt_text}" src="{data_uri}"></p>'
                missing_images.append(chunk)

        # Insert missing images after Amazon's chart
        if missing_images:
            print(f"Inserting {len(missing_images)} new charts...")
            
            # Find insertion point: Before "<h2>Monte Carlo"
            # This is safer than regex.
            anchor = "<h2>Monte Carlo"
            idx = html.find(anchor)
            
            if idx != -1:
                insertion_html = "\n        ".join(missing_images)
                # Insert before the anchor
                html = html[:idx] + insertion_html + "\n\n        " + html[idx:]
                print("  - Insertion successful (via string injection).")
            else:
                print("  - CRITICAL: Could not find insertion anchor '<h2>Monte Carlo'.")
        
        # Write back
        
        # Write back
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print("Article updated successfully.")

    except Exception as e:
        print(f"Error patching article: {e}")

if __name__ == "__main__":
    patch_article()
