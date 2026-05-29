"""
Preloads a stub libGLESv2.so.2 so mediapipe can run on CPU-only servers
(e.g. Render free tier) that lack OpenGL ES libraries.

Import this module BEFORE any mediapipe.tasks imports.

How it works: mediapipe's libmediapipe.so declares libGLESv2.so.2 as a NEEDED
dependency. On CPU-only hosts that library is absent, so dlopen fails. We compile
a valid *empty* shared library with the matching SONAME and preload it with
RTLD_GLOBAL. Because we use lazy binding and the CPU delegate never actually
calls any GL functions, the missing symbols are never resolved at runtime.
"""
import ctypes
import os
import subprocess
import tempfile

_STUB_PATH = os.path.join(tempfile.gettempdir(), "libGLESv2.so.2")


def _compile_stub(path: str) -> bool:
    """Compile a valid empty shared library with SONAME=libGLESv2.so.2."""
    src = path + ".c"
    try:
        with open(src, "w") as f:
            f.write("\n")  # empty translation unit
        result = subprocess.run(
            ["gcc", "-shared", "-fPIC", "-Wl,-soname,libGLESv2.so.2", "-o", path, src],
            capture_output=True,
        )
        if result.returncode != 0:
            print(f"[preload_gles] gcc failed: {result.stderr.decode(errors='ignore')}")
            return False
        return os.path.exists(path)
    except FileNotFoundError:
        print("[preload_gles] gcc not available; cannot build stub")
        return False
    except Exception as e:
        print(f"[preload_gles] stub compile error: {e}")
        return False
    finally:
        try:
            os.remove(src)
        except OSError:
            pass


def ensure_libgles():
    """Preload libGLESv2.so.2 (real or stub) so mediapipe can load."""
    try:
        ctypes.CDLL("libGLESv2.so.2", mode=ctypes.RTLD_GLOBAL)
        return  # Already available on this system
    except OSError:
        pass

    if not os.path.exists(_STUB_PATH):
        if not _compile_stub(_STUB_PATH):
            return

    try:
        # RTLD_LAZY so unresolved GL symbols don't fail until (never) called
        ctypes.CDLL(_STUB_PATH, mode=ctypes.RTLD_GLOBAL | ctypes.RTLD_LAZY)
        os.environ["LD_LIBRARY_PATH"] = (
            tempfile.gettempdir() + ":" + os.environ.get("LD_LIBRARY_PATH", "")
        )
        print("[preload_gles] Loaded libGLESv2 stub for CPU-only mediapipe")
    except OSError as e:
        print(f"[preload_gles] Could not load stub: {e}")


ensure_libgles()
