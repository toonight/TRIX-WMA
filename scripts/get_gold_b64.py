
import base64
from pathlib import Path

def main():
    img_path = Path("d:/Projets/2026/TRIX-WMA/reports/figures/equity_curves_GC=F.png")
    with open(img_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode('utf-8')
        with open("gold_b64_utf8.txt", "w", encoding="utf-8") as out:
            out.write(f"data:image/png;base64,{b64}")

if __name__ == "__main__":
    main()
