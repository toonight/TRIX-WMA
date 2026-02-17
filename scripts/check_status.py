
import os

def read_results():
    print("--- Optimization Results ---")
    if not os.path.exists('tech_growth_results.txt'):
        print("tech_growth_results.txt not found.")
        return

    params = {}
    try:
        with open('tech_growth_results.txt', 'r', encoding='utf-16') as f:
            lines = f.readlines()
    except:
        try:
            with open('tech_growth_results.txt', 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading file: {e}")
            return

    for line in lines:
        if "TRIX=" in line and "|" in line:
            # Example: NVDA: TRIX=4, WMA=10, Shift=5 | CAGR=...
            parts = line.split(':')
            ticker = parts[0].strip()
            settings = parts[1].split('|')[0].strip()
            # Parse settings
            setting_parts = [s.strip() for s in settings.split(',')]
            trix = int(setting_parts[0].split('=')[1])
            wma = int(setting_parts[1].split('=')[1])
            shift = int(setting_parts[2].split('=')[1])
            params[ticker] = {"trix": trix, "wma": wma, "shift": shift}
            print(f"Parsed {ticker}: {params[ticker]}")
    
    return params

def check_html():
    print("\n--- HTML Check ---")
    try:
        with open('docs/article.html', 'r', encoding='utf-8') as f:
            html = f.read()
            
        tickers = ["NVDA", "GOOGL", "MSFT", "META", "AMZN"]
        for t in tickers:
            if t in html:
                count = html.count(t)
                print(f"{t}: found {count} times")
                # Check for image tag specifically
                if f'alt="{t}' in html or f'alt="{t}' in html: # Very basic check
                     print(f"  - Image likely present for {t}")
                else: 
                     # Check closer context
                     idx = html.find(t)
                     if idx != -1:
                         snippet = html[idx:idx+100]
                         # print(f"  - Context: {snippet}...")
            else:
                print(f"{t}: NOT found in HTML")
                
        # Check specific img alt patterns
        if '<img alt="NVIDIA' in html: print("Found NVIDIA Img")
        if '<img alt="Amazon' in html: print("Found Amazon Img")
        if '<img alt="Google' in html: print("Found Google Img") # Assuming Google for GOOGL
        if '<img alt="Microsoft' in html: print("Found Microsoft Img")
        if '<img alt="Meta' in html: print("Found Meta Img")

    except Exception as e:
        print(f"Error reading HTML: {e}")

if __name__ == "__main__":
    read_results()
    check_html()
