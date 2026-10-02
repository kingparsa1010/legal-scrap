"""
Automated build script for standalone portable executable (LegalScrap.exe).
Configures PyInstaller, custom application icons, hidden imports, and Windows packaging.
"""
import sys
import os
import subprocess


def prepare_icon(assets_dir: str) -> str:
    """Ensure logo.ico is generated with multi-size resolutions from logo.png."""
    ico_path = os.path.join(assets_dir, "logo.ico")
    png_path = os.path.join(assets_dir, "logo.png")

    if not os.path.exists(ico_path) and os.path.exists(png_path):
        try:
            from PIL import Image
            img = Image.open(png_path)
            # Save multiple icon sizes for crisp display on desktop and Windows taskbar
            icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            img.save(ico_path, format="ICO", sizes=icon_sizes)
            print("[+] logo.ico generated successfully from logo.png.")
        except Exception as e:
            print(f"[!] Failed to generate icon: {e}")

    return ico_path if os.path.exists(ico_path) else ""


def run_build():
    print("=" * 65)
    print("  Building Single-file Portable Executable (LegalScrap.exe)")
    print("=" * 65)

    # 1. Check and install PyInstaller if needed
    try:
        import PyInstaller
        print(f"[+] PyInstaller found (v{PyInstaller.__version__})")
    except ImportError:
        print("[!] PyInstaller not found. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[+] PyInstaller installed successfully.")

    root_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(root_dir, "assets")

    # 2. Prepare custom application icon
    ico_path = prepare_icon(assets_dir)

    # 3. Optimized PyInstaller parameters for Windows
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",           # Produce single standalone executable
        "--windowed",          # Do not show black console window in GUI mode
        "--name", "LegalScrap",
        # Core UI & Web dependencies
        "--hidden-import", "PyQt6",
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "webview",
        "--hidden-import", "webview.platforms.winforms",
        "--hidden-import", "webview.platforms.edgechromium",
        # Document & Parsing dependencies
        "--hidden-import", "openpyxl",
        "--hidden-import", "rapidfuzz",
        "--hidden-import", "docx",
        "--hidden-import", "jdatetime",
        "--hidden-import", "requests",
        "--hidden-import", "urllib3",
        "--hidden-import", "bs4",
        # GUI modules
        "--hidden-import", "gui",
        "--hidden-import", "gui.app",
        # Scanner package & all submodules
        "--hidden-import", "scanner",
        "--hidden-import", "scanner.auth",
        "--hidden-import", "scanner.client",
        "--hidden-import", "scanner.comparator",
        "--hidden-import", "scanner.database",
        "--hidden-import", "scanner.declaration_worker",
        "--hidden-import", "scanner.detail_viewer",
        "--hidden-import", "scanner.exporter",
        "--hidden-import", "scanner.logger",
        "--hidden-import", "scanner.login_window",
        "--hidden-import", "scanner.parser",
        "--hidden-import", "scanner.similarity",
        "--hidden-import", "scanner.store",
        "--hidden-import", "scanner.word_exporter",
        "--hidden-import", "scanner.worker",
        # Services package & all submodules
        "--hidden-import", "services",
        "--hidden-import", "services.declaration_completion_service",
        "--hidden-import", "services.declaration_scan_service",
        "--hidden-import", "services.scan_persistence_service",
        "--hidden-import", "services.search_request_service",
        "--hidden-import", "services.targeted_scan_service",
        # Collect pywebview templates/assets
        "--collect-data", "webview",
        # Exclude unused operating system backends and heavy packages to reduce binary size
        "--exclude-module", "webview.platforms.android",
        "--exclude-module", "webview.platforms.cocoa",
        "--exclude-module", "webview.platforms.gtk",
        "--exclude-module", "webview.platforms.qt",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "torch",
    ]

    # 4. Attach official application icon
    if ico_path:
        cmd.extend(["--icon", ico_path])
        print(f"[+] EXE icon configured: {ico_path}")

    # 5. Embed assets directory (logos and icons) inside the bundle
    # Note: User data is NOT embedded; all runtime data is stored in the external 'data' directory.
    if os.path.exists(assets_dir):
        cmd.extend(["--add-data", f"{assets_dir};assets"])
        print(f"[+] Embedded assets folder: {assets_dir}")

    # 6. Main application entry point
    cmd.append("main.py")

    print("\n[+] Compiling and packaging executable... (please wait)")
    result = subprocess.run(cmd, cwd=root_dir)

    if result.returncode == 0:
        exe_path = os.path.join(root_dir, "dist", "LegalScrap.exe")
        print("\n" + "=" * 65)
        print(" [+] Build completed successfully!")
        print(" Output executable:")
        print(f" {exe_path}")
        print("=" * 65)
        print("Standalone executable is ready for Windows 10/11.")
        print("Persistent application storage will be created dynamically")
        print("in the 'data' directory alongside LegalScrap.exe.")
    else:
        print("\n[-] Error occurred during executable build.")


if __name__ == "__main__":
    run_build()
