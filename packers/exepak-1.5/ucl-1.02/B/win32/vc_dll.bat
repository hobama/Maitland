@echo // Copyright (C) 1996-2003 Markus F.X.J. Oberhumer
@echo //
@echo //   Windows 32-bit
@echo //   Microsoft Visual C/C++ (DLL)
@echo //
@call b\prepare.bat
@if "%BECHO%"=="n" echo off


set CC=cl -nologo -MD
set CF=-O2 -GF -W4 %CFI% %CFASM%
set LF=%BLIB% setargv.obj

%CC% %CF% -D__UCL_EXPORT1#__declspec(dllexport) -c @b\src.rsp
@if errorlevel 1 goto error
%CC% -LD -Fe%BDLL% @b\win32\vc.rsp /link /map /def:b\win32\vc_dll.def
@if errorlevel 1 goto error

%CC% %CF% examples\simple.c %LF%
@if errorlevel 1 goto error
%CC% %CF% examples\uclpack.c %LF%
@if errorlevel 1 goto error


@call b\done.bat
@goto end
:error
@echo ERROR during build!
:end
@call b\unset.bat
