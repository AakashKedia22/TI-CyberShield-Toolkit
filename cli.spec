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

# Collect TIFS certificate generation files
datas = []
tifs_path = os.path.join(repo_root, 'host', 'src', 'apps', 'tifs')
for root, dirs, files in os.walk(tifs_path):
    for file in files:
        src_file = os.path.join(root, file)
        rel_path = os.path.relpath(root, os.path.join(repo_root, 'host', 'src'))
        dst_dir = rel_path
        datas.append((src_file, dst_dir))

# Collect f29_devel_keys data files (.pem, .key)
devel_keys_path = os.path.join(repo_root, 'host', 'src', 'apps', 'spt', 'f29_devel_keys')
for root, dirs, files in os.walk(devel_keys_path):
    for file in files:
        if file.endswith(('.pem', '.key')):
            src_file = os.path.join(root, file)
            rel_path = os.path.relpath(root, os.path.join(repo_root, 'host', 'src'))
            datas.append((src_file, rel_path))

a = Analysis(
    [os.path.join(repo_root, 'host', 'src', 'apps', 'spt', '__main__.py')],
    pathex=[repo_root, os.path.join(repo_root, 'host', 'src')],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'importlib.resources',
        'cryptography',
        'serial',
        'xmodem',
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
        'apps.spt',
        'apps.spt.main',
        'apps.spt.f29_spt',
        'apps.spt.genkeys',
        'apps.spt.gencert',
        'apps.spt.sign',
        'apps.spt.encrypt',
        'apps.spt.download',
        'apps.spt.parseSoCId',
        'apps.spt.f29_devel_keys.load_development_keys',
        'apps.tifs',
        'apps.tifs.kp_cp_f29h85x',
        'apps.tifs.sign_encrypt_f29',
        'apps.tifs.sign_encrypt_f29.sign_encrypt',
        'apps.tifs.rot_cert_scripts.rot_switch_cert_gen',
        'apps.tifs.debug_cert_scripts.debug_image_gen',
        'apps.tifs.f29_device_recovery',
        'apps.tifs.f29_device_recovery.device_recovery_flow',
        'apps.tifs.f29_device_recovery.debug_recovery_cert_gen',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'PyQt5.QtCore',
        'apps.qtgui',
    ],
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
    name='TI_CST_CLI',
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
    # Windows-specific settings
    uac_admin=True if IS_WINDOWS else False,
)
