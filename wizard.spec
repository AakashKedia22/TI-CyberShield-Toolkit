# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import os
import sys
import platform

# Platform detection
IS_WINDOWS = platform.system() == 'Windows'

# Set the repo root as the base directory for paths
repo_root = os.path.abspath(os.path.dirname('__file__'))
# When using PyInstaller directly, __file__ isn't defined
# So we use the current directory
if not os.path.isdir(os.path.join(repo_root, 'host')):
    repo_root = os.getcwd()

# Make sure we add repo_root to sys.path for imports
sys.path.insert(0, repo_root)

# Collect all non-Python data files from apps/ (assets, device configs, keys, certs, etc.)
datas = []
apps_src_path = os.path.join(repo_root, 'host', 'src', 'apps')
for root, dirs, files in os.walk(apps_src_path):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for file in files:
        if file.endswith(('.py', '.pyc')):
            continue
        src_file = os.path.join(root, file)
        rel_path = os.path.relpath(root, os.path.join(repo_root, 'host', 'src'))
        datas.append((src_file, rel_path))

# Collect TIFS certificate generation files
tifs_path = os.path.join(repo_root, 'host', 'src', 'apps', 'tifs')
for root, dirs, files in os.walk(tifs_path):
    for file in files:
        src_file = os.path.join(root, file)
        # The path needs to be relative to the apps directory
        rel_path = os.path.relpath(root, os.path.join(repo_root, 'host', 'src'))
        dst_dir = rel_path
        datas.append((src_file, dst_dir))

a = Analysis(
    [os.path.join(repo_root, 'run_wizard.py')],
    pathex=[repo_root, os.path.join(repo_root, 'host', 'src')],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'PyQt5.QtCore',
        'importlib.resources',
        'apps.qtgui.main_wizard',
        'apps.qtgui.views.wizard_view',
        'apps.qtgui.controllers.wizard_controller',
        'apps.qtgui.utils.platform_utils',
        'cryptography',
        'serial',
        'xmodem',
        'apps.tifs',
        'apps.tifs.otp_cert_gen',
        'apps.tifs.otp_cert_gen.keys_devel',
        'apps.tifs.otp_cert_gen.keys_devel.load_development_keys',
        'apps.tifs.sign_encrypt_f29',
        'apps.spt.f29_spt',
        'tqdm',
        'asn1crypto',
        'pkcs11',
        'pkcs11._pkcs11',
        'pkcs11.attributes',
        'pkcs11.constants',
        'pkcs11.exceptions',
        'pkcs11.mechanisms',
        'pkcs11.types',
        'pkcs11.util',
        'pkcs11.util.rsa',
        'pkcs11.util.ec',
        'pkcs11.util.x509',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=False,
    name='ti_wizard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    onefile=True,
    # Windows-specific settings
    uac_admin=True if IS_WINDOWS else False,
    distpath=os.path.join(repo_root, 'dist', 'wizard')
)