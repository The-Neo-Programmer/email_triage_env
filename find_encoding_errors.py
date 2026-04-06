import os

skip_dirs = {'.git', 'venv', '__pycache__', '.egg-info', 'egg-info'}
skip_extensions = {'.pyc', '.lock', '.png', '.jpg', '.webp'}

for root, dirs, files in os.walk('.'):
    # Prune skipped directories
    dirs[:] = [d for d in dirs if d not in skip_dirs and not d.endswith('.egg-info')]
    
    for fname in files:
        if any(fname.endswith(ext) for ext in skip_extensions):
            continue
        fpath = os.path.join(root, fname)
        try:
            with open(fpath, 'r', encoding='cp1252') as fh:
                fh.read()
        except UnicodeDecodeError as e:
            print(f"ENCODING ERROR [{e}]: {fpath}")
        except PermissionError:
            pass

print("Scan complete.")
