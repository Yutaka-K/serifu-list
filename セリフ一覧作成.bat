@echo off
chcp 932 >nul
setlocal
cd /d "%~dp0"
title セリフ一覧作成

rem  使い方：
rem   ・ダブルクリック … 「入力」フォルダの台本をすべて処理します
rem   ・台本ファイルをこのファイルの上にドラッグ＆ドロップ … その台本だけ処理します
rem   結果は「出力」フォルダにできます。

call :find_python
if not defined PY goto no_python

set PYTHONUTF8=1
%PY% "%~dp0program\run.py" %*
if errorlevel 1 goto failed
goto end

:failed
echo.
echo ※ うまくいかなかった台本があります。上のメッセージを確かめてください。
goto end

:no_python
echo 【エラー】Python が見つかりません。
echo  README の「1. Python を入れる」の手順で Python をインストールし、
echo  「初回セットアップ.bat」を実行してから、もう一度ためしてください。
goto end

:find_python
set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY exit /b 0
python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
exit /b 0

:end
echo.
echo 何かキーを押すと、このウィンドウを閉じます。
pause >nul
endlocal
