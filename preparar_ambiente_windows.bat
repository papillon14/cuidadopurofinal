@echo off
REM preparar_ambiente_windows.bat -> prepara o Cuidado Puro no Windows
REM Uso: de dois cliques neste arquivo, ou rode no terminal dentro da pasta cuidado_puro
cd /d "%~dp0"

echo == 1/4 Criando o ambiente virtual (venv) ==
if not exist venv (
    python -m venv venv
    if errorlevel 1 (
        echo ERRO: nao consegui criar o venv. Confira se o Python esta instalado e marcado "Add to PATH".
        pause
        exit /b 1
    )
)

echo == 2/4 Ativando o venv ==
call venv\Scripts\activate

echo == 3/4 Instalando as bibliotecas ==
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERRO ao instalar. Confira se o computador tem internet.
    pause
    exit /b 1
)

echo == 4/4 Carregando o banco com os dados de exemplo ==
python carregar_exemplos.py

python verificar_ambiente.py
echo Agora rode:  venv\Scripts\activate   e depois   uvicorn main:app --reload
echo E abra no navegador:  http://127.0.0.1:8000
pause
