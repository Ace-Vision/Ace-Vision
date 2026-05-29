"""
Preloads a stub libGLESv2.so.2 so mediapipe can run on CPU-only servers
(e.g. Render free tier) that lack OpenGL ES libraries.

Import this module BEFORE any mediapipe.tasks imports.
"""
import ctypes
import os
import struct


def _create_stub(path: str) -> bool:
    """Write a minimal valid ELF64 shared object with SONAME=libGLESv2.so.2."""
    try:
        STRTAB = b'\x00libGLESv2.so.2\x00'
        DYN_OFF = 64 + 56 + 56          # ELF header + 2 phdrs
        STRTAB_OFF = DYN_OFF + 64       # 4 dynamic entries * 16 bytes
        FILE_SIZE = STRTAB_OFF + len(STRTAB)

        e_ident = b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 8
        elf_hdr = e_ident + struct.pack(
            '<HHIQQQIHHHHHH',
            3, 62, 1, 0, 64, 0, 0, 64, 56, 2, 64, 0, 0)

        ph_load = struct.pack('<IIQQQQQQ',
            1, 5, 0, 0, 0, FILE_SIZE, FILE_SIZE, 0x1000)
        ph_dyn = struct.pack('<IIQQQQQQ',
            2, 6, DYN_OFF, DYN_OFF, DYN_OFF, 64, 64, 8)

        # DT_SONAME=14, DT_STRTAB=5, DT_STRSZ=10, DT_NULL=0
        dyn = struct.pack('<8q',
            14, 1,
            5, STRTAB_OFF,
            10, len(STRTAB),
            0, 0)

        with open(path, 'wb') as f:
            f.write(elf_hdr + ph_load + ph_dyn + dyn + STRTAB)
        os.chmod(path, 0o755)
        return True
    except Exception as e:
        print(f"[preload_gles] Failed to create stub: {e}")
        return False


def ensure_libgles():
    """Preload libGLESv2.so.2 stub if not already available."""
    try:
        ctypes.CDLL('libGLESv2.so.2', mode=ctypes.RTLD_GLOBAL)
        return  # Already available on this system
    except OSError:
        pass

    stub_path = '/tmp/libGLESv2.so.2'
    if not os.path.exists(stub_path):
        if not _create_stub(stub_path):
            return

    try:
        ctypes.CDLL(stub_path, mode=ctypes.RTLD_GLOBAL)
        print('[preload_gles] Loaded libGLESv2 stub for CPU-only mediapipe')
    except OSError as e:
        print(f'[preload_gles] Could not load stub: {e}')


ensure_libgles()
