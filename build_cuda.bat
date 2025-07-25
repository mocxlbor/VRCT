call .venv_cuda/Scripts/activate
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
pyinstaller backend_cuda.spec --distpath src-tauri/bin --clean --noconfirm --log-level ERROR