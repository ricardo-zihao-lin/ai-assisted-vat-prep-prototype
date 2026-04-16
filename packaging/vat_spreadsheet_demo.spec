# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


PROJECT_ROOT = Path.cwd().resolve()
GRADIO_RUNTIME_PACKAGES = (
    "gradio",
    "gradio_client",
    "safehttpx",
    "groovy",
    "huggingface_hub",
)
RUNTIME_DEMO_FILES = (
    "README_RUN_FIRST.txt",
    "data/demo/sample_data.csv",
)


def collect_project_file(relative_path: str) -> list[tuple[str, str]]:
    """Collect a single runtime file conservatively for the demo bundle."""
    source_file = PROJECT_ROOT / relative_path
    if not source_file.exists():
        return []

    destination_dir = "." if source_file.parent == PROJECT_ROOT else str(source_file.parent.relative_to(PROJECT_ROOT))
    return [(str(source_file), destination_dir)]


def collect_runtime_demo_files(relative_paths: tuple[str, ...]) -> list[tuple[str, str]]:
    """Collect only the files the packaged demo genuinely needs at runtime."""
    collected: list[tuple[str, str]] = []
    for relative_path in relative_paths:
        collected += collect_project_file(relative_path)
    return collected


def collect_package_support(package_names: tuple[str, ...]) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[str]]:
    """Collect runtime resources for packages that Gradio relies on at startup."""
    datas: list[tuple[str, str]] = []
    binaries: list[tuple[str, str]] = []
    hiddenimports: list[str] = []

    for package_name in package_names:
        package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
        datas += package_datas
        binaries += package_binaries
        hiddenimports += package_hiddenimports

    return list(dict.fromkeys(datas)), list(dict.fromkeys(binaries)), list(dict.fromkeys(hiddenimports))


package_datas, package_binaries, package_hiddenimports = collect_package_support(GRADIO_RUNTIME_PACKAGES)

datas = package_datas
datas += collect_runtime_demo_files(RUNTIME_DEMO_FILES)

hiddenimports = package_hiddenimports


a = Analysis(
    [str(PROJECT_ROOT / "gui.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=package_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VAT_Spreadsheet_Demo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VAT_Spreadsheet_Demo",
)
