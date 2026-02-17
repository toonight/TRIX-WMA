
import os

def read_results():
    if not os.path.exists('tech_growth_results.txt'):
        print("File not found.")
        return

    content = ""
    try:
        with open('tech_growth_results.txt', 'r', encoding='utf-16') as f:
            content = f.read()
    except:
        try:
            with open('tech_growth_results.txt', 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error: {e}")
            return
    
    print("--- CONTENT START ---")
    print(content)
    print("--- CONTENT END ---")

if __name__ == "__main__":
    read_results()
