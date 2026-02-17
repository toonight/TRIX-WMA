
import re

def find_contexts():
    print("--- Finding Chart Contexts ---")
    try:
        with open('docs/article.html', 'r', encoding='utf-8') as f:
            html = f.read()
            
        tickers = ["NVDA", "GOOGL", "MSFT", "META", "AMZN"]
        for t in tickers:
            print(f"\nContext for {t}:")
            # Regex to find img tag with alt containing ticker
            # <img alt="NVIDIA ... src="...">
            # We want to capture the whole tag to replace it, or at least identify it uniquely.
            
            # Simple search for now
            pattern = re.compile(f'<img[^>]*alt="[^"]*{t}[^"]*"[^>]*>', re.IGNORECASE)
            match = pattern.search(html)
            if match:
                print(f"MATCH: {match.group(0)[:100]}...")
            else:
                print("NO MATCH found in img tags.")
                # Fallback: check text context
                idx = html.find(t)
                if idx != -1:
                    print(f"Text context: ...{html[idx-50:idx+50]}...")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_contexts()
