call .venv/Scripts/activate
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
pyinstaller backend.spec --distpath src-tauri/bin --clean --noconfirm --log-level ERROR