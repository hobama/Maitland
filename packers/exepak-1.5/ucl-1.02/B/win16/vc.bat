@echo // Copyright (C) 1996-2003 Markus F.X.J. Oberhumer
@echo //
@echo //   Windows 16-bit
@echo //   Microsoft Visual C/C++ (using QuickWin)
@echo //
@call b\prepare.bat
@if "%BECHO%"=="n" echo off


set CC=cl -nologo -AL -Mq -G2
set CF=-O -Gf -Gy -W3 %CFI%
set LF=%BLIB% /link /seg:256

%CC% %CF% -c src\*.c
@if errorlevel 1 goto error
lib /nologo %BLIB% @b\dos16\bc.rsp;
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
