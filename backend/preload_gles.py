"""
Preloads a stub libGLESv2.so.2 so mediapipe can run on CPU-only servers
(e.g. Render free tier) that lack OpenGL ES libraries.

Import this module BEFORE any mediapipe.tasks imports.

How it works: mediapipe's libmediapipe.so declares libGLESv2.so.2 as a NEEDED
dependency AND references GL/EGL symbols (e.g. glBindBuffer) that must resolve
at load time. On CPU-only hosts that library is absent. We compile a shared
library that defines every GLES2/GLES3/EGL entry point as a no-op returning 0,
give it SONAME libGLESv2.so.2, and preload it with RTLD_GLOBAL so the symbols
land in the global scope. With the CPU delegate these functions are never
actually called, so the no-op bodies never run.
"""
import ctypes
import os
import subprocess
import tempfile

_STUB_PATH = os.path.join(tempfile.gettempdir(), "libGLESv2.so.2")

# Comprehensive set of GLES2/GLES3 + EGL entry points mediapipe may reference.
_GL_SYMBOLS = [
    # EGL
    "eglGetDisplay", "eglInitialize", "eglTerminate", "eglGetConfigs",
    "eglChooseConfig", "eglGetConfigAttrib", "eglCreateWindowSurface",
    "eglCreatePbufferSurface", "eglCreatePixmapSurface", "eglDestroySurface",
    "eglQuerySurface", "eglBindAPI", "eglQueryAPI", "eglWaitClient",
    "eglReleaseThread", "eglCreatePbufferFromClientBuffer", "eglSurfaceAttrib",
    "eglBindTexImage", "eglReleaseTexImage", "eglSwapInterval",
    "eglCreateContext", "eglDestroyContext", "eglMakeCurrent",
    "eglGetCurrentContext", "eglGetCurrentSurface", "eglGetCurrentDisplay",
    "eglQueryContext", "eglWaitGL", "eglWaitNative", "eglSwapBuffers",
    "eglCopyBuffers", "eglGetError", "eglQueryString", "eglGetProcAddress",
    "eglGetPlatformDisplay", "eglCreatePlatformWindowSurface",
    "eglCreatePlatformPixmapSurface", "eglCreateImage", "eglDestroyImage",
    "eglCreateImageKHR", "eglDestroyImageKHR", "eglClientWaitSyncKHR",
    "eglCreateSyncKHR", "eglDestroySyncKHR", "eglGetSyncAttribKHR",
    "eglCreateSync", "eglDestroySync", "eglClientWaitSync", "eglWaitSync",
    "eglGetSyncAttrib",
    # GLES2
    "glActiveTexture", "glAttachShader", "glBindAttribLocation", "glBindBuffer",
    "glBindFramebuffer", "glBindRenderbuffer", "glBindTexture", "glBlendColor",
    "glBlendEquation", "glBlendEquationSeparate", "glBlendFunc",
    "glBlendFuncSeparate", "glBufferData", "glBufferSubData",
    "glCheckFramebufferStatus", "glClear", "glClearColor", "glClearDepthf",
    "glClearStencil", "glColorMask", "glCompileShader", "glCompressedTexImage2D",
    "glCompressedTexSubImage2D", "glCopyTexImage2D", "glCopyTexSubImage2D",
    "glCreateProgram", "glCreateShader", "glCullFace", "glDeleteBuffers",
    "glDeleteFramebuffers", "glDeleteProgram", "glDeleteRenderbuffers",
    "glDeleteShader", "glDeleteTextures", "glDepthFunc", "glDepthMask",
    "glDepthRangef", "glDetachShader", "glDisable", "glDisableVertexAttribArray",
    "glDrawArrays", "glDrawElements", "glEnable", "glEnableVertexAttribArray",
    "glFinish", "glFlush", "glFramebufferRenderbuffer", "glFramebufferTexture2D",
    "glFrontFace", "glGenBuffers", "glGenerateMipmap", "glGenFramebuffers",
    "glGenRenderbuffers", "glGenTextures", "glGetActiveAttrib",
    "glGetActiveUniform", "glGetAttachedShaders", "glGetAttribLocation",
    "glGetBooleanv", "glGetBufferParameteriv", "glGetError", "glGetFloatv",
    "glGetFramebufferAttachmentParameteriv", "glGetIntegerv", "glGetProgramiv",
    "glGetProgramInfoLog", "glGetRenderbufferParameteriv", "glGetShaderiv",
    "glGetShaderInfoLog", "glGetShaderPrecisionFormat", "glGetShaderSource",
    "glGetString", "glGetTexParameterfv", "glGetTexParameteriv",
    "glGetUniformfv", "glGetUniformiv", "glGetUniformLocation",
    "glGetVertexAttribfv", "glGetVertexAttribiv", "glGetVertexAttribPointerv",
    "glHint", "glIsBuffer", "glIsEnabled", "glIsFramebuffer", "glIsProgram",
    "glIsRenderbuffer", "glIsShader", "glIsTexture", "glLineWidth",
    "glLinkProgram", "glPixelStorei", "glPolygonOffset", "glReadPixels",
    "glReleaseShaderCompiler", "glRenderbufferStorage", "glSampleCoverage",
    "glScissor", "glShaderBinary", "glShaderSource", "glStencilFunc",
    "glStencilFuncSeparate", "glStencilMask", "glStencilMaskSeparate",
    "glStencilOp", "glStencilOpSeparate", "glTexImage2D", "glTexParameterf",
    "glTexParameterfv", "glTexParameteri", "glTexParameteriv", "glTexSubImage2D",
    "glUniform1f", "glUniform1fv", "glUniform1i", "glUniform1iv", "glUniform2f",
    "glUniform2fv", "glUniform2i", "glUniform2iv", "glUniform3f", "glUniform3fv",
    "glUniform3i", "glUniform3iv", "glUniform4f", "glUniform4fv", "glUniform4i",
    "glUniform4iv", "glUniformMatrix2fv", "glUniformMatrix3fv",
    "glUniformMatrix4fv", "glUseProgram", "glValidateProgram", "glVertexAttrib1f",
    "glVertexAttrib1fv", "glVertexAttrib2f", "glVertexAttrib2fv",
    "glVertexAttrib3f", "glVertexAttrib3fv", "glVertexAttrib4f",
    "glVertexAttrib4fv", "glVertexAttribPointer", "glViewport",
    # GLES3
    "glReadBuffer", "glDrawRangeElements", "glTexImage3D", "glTexSubImage3D",
    "glCopyTexSubImage3D", "glCompressedTexImage3D", "glCompressedTexSubImage3D",
    "glGenQueries", "glDeleteQueries", "glIsQuery", "glBeginQuery", "glEndQuery",
    "glGetQueryiv", "glGetQueryObjectuiv", "glUnmapBuffer", "glGetBufferPointerv",
    "glDrawBuffers", "glUniformMatrix2x3fv", "glUniformMatrix3x2fv",
    "glUniformMatrix2x4fv", "glUniformMatrix4x2fv", "glUniformMatrix3x4fv",
    "glUniformMatrix4x3fv", "glBlitFramebuffer", "glRenderbufferStorageMultisample",
    "glFramebufferTextureLayer", "glMapBufferRange", "glFlushMappedBufferRange",
    "glBindVertexArray", "glDeleteVertexArrays", "glGenVertexArrays",
    "glIsVertexArray", "glGetIntegeri_v", "glBeginTransformFeedback",
    "glEndTransformFeedback", "glBindBufferRange", "glBindBufferBase",
    "glTransformFeedbackVaryings", "glGetTransformFeedbackVarying",
    "glVertexAttribIPointer", "glGetVertexAttribIiv", "glGetVertexAttribIuiv",
    "glVertexAttribI4i", "glVertexAttribI4ui", "glVertexAttribI4iv",
    "glVertexAttribI4uiv", "glGetUniformuiv", "glGetFragDataLocation",
    "glUniform1ui", "glUniform2ui", "glUniform3ui", "glUniform4ui",
    "glUniform1uiv", "glUniform2uiv", "glUniform3uiv", "glUniform4uiv",
    "glClearBufferiv", "glClearBufferuiv", "glClearBufferfv", "glClearBufferfi",
    "glGetStringi", "glCopyBufferSubData", "glGetUniformIndices",
    "glGetActiveUniformsiv", "glGetUniformBlockIndex", "glGetActiveUniformBlockiv",
    "glGetActiveUniformBlockName", "glUniformBlockBinding", "glDrawArraysInstanced",
    "glDrawElementsInstanced", "glFenceSync", "glIsSync", "glDeleteSync",
    "glClientWaitSync", "glWaitSync", "glGetInteger64v", "glGetSynciv",
    "glGetInteger64i_v", "glGetBufferParameteri64v", "glGenSamplers",
    "glDeleteSamplers", "glIsSampler", "glBindSampler", "glSamplerParameteri",
    "glSamplerParameteriv", "glSamplerParameterf", "glSamplerParameterfv",
    "glGetSamplerParameteriv", "glGetSamplerParameterfv", "glVertexAttribDivisor",
    "glBindTransformFeedback", "glDeleteTransformFeedbacks",
    "glGenTransformFeedbacks", "glIsTransformFeedback", "glPauseTransformFeedback",
    "glResumeTransformFeedback", "glGetProgramBinary", "glProgramBinary",
    "glProgramParameteri", "glInvalidateFramebuffer", "glInvalidateSubFramebuffer",
    "glTexStorage2D", "glTexStorage3D", "glGetInternalformativ",
]


def _compile_stub(path: str) -> bool:
    """Compile a shared library defining all GL/EGL symbols as no-ops."""
    src = path + ".c"
    try:
        with open(src, "w") as f:
            # Each entry point returns 0 (covers void / int / uint / pointer
            # returns on the x86_64 SysV ABI — the value is ignored for void).
            for name in _GL_SYMBOLS:
                f.write(f"long {name}(){{return 0;}}\n")
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
        # RTLD_GLOBAL so the no-op GL symbols enter the global scope and
        # satisfy libmediapipe.so's undefined references at load time.
        ctypes.CDLL(_STUB_PATH, mode=ctypes.RTLD_GLOBAL)
        os.environ["LD_LIBRARY_PATH"] = (
            tempfile.gettempdir() + ":" + os.environ.get("LD_LIBRARY_PATH", "")
        )
        print("[preload_gles] Loaded libGLESv2 GL stub for CPU-only mediapipe")
    except OSError as e:
        print(f"[preload_gles] Could not load stub: {e}")


ensure_libgles()
