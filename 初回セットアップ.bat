@echo off
chcp 932 >nul
setlocal
cd /d "%~dp0"
title 初回セットアップ

echo ==================================================
echo  初回セットアップ
echo  セリフ一覧作成ツールに必要なライブラリを入れます
echo ==================================================
echo.

call :find_python
if not defined PY goto no_python

echo 使う Python：
%PY% --version
echo.
echo ライブラリをインストールしています。しばらくお待ちください……
echo （インターネットにつながっている必要があります）
echo.
%PY% -m pip install --upgrade --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto pip_failed

echo.
echo ==================================================
echo  セットアップが完了しました！
echo  次からは「セリフ一覧作成.bat」を使ってください。
echo ==================================================
goto end

:pip_failed
echo.
echo 【エラー】ライブラリのインストールに失敗しました。
echo  ・インターネットにつながっているか確かめてください。
echo  ・もう一度このファイルを実行してみてください。
echo  ・それでもだめなときは、上に表示された英語のメッセージを
echo    README の「困ったとき」と見比べてください。
goto end

:no_python
echo 【エラー】Python が見つかりません。
echo  README の「1. Python を入れる」の手順で Python をインストールしてください。
echo  インストールのとき「Add python.exe to PATH」にチェックを入れるのを
echo  忘れないでください。インストール後、このファイルをもう一度実行します。
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
