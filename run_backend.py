import subprocess

def run_script(script_name):
    print(f"\n{'='*50}\nMenjalankan {script_name}...\n{'='*50}")
    subprocess.run(["python", f"modules/{script_name}"], check=True)

def main():
    scripts = [
        "preprocessing.py",
        "interpolation.py",
        "distance.py",
        "reclassify.py",
        "smce_model.py"
    ]
    
    print("Mulai Pemrosesan Data Backend Risiko Banjir...")
    for script in scripts:
        run_script(script)
    print("\nSemua proses backend selesai dengan sukses!")

if __name__ == '__main__':
    main()
