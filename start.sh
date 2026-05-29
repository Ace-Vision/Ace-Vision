#!/bin/bash
# Create stub libGLESv2.so.2 for mediapipe on CPU-only servers
echo 'void eglGetDisplay() {} void glFlush() {}' > /tmp/gles_stub.c
gcc -shared -fPIC -Wl,-soname,libGLESv2.so.2 -o /tmp/libGLESv2.so.2 /tmp/gles_stub.c 2>/dev/null || true
export LD_LIBRARY_PATH=/tmp:$LD_LIBRARY_PATH
exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT
