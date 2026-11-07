#!/bin/bash
# preparar_ambiente.sh -> prepara o Cuidado Puro de uma vez (Linux Mint)
# Uso, dentro da pasta cuidado_puro:   bash preparar_ambiente.sh

cd "$(dirname "$0")" || exit 1

echo "== 1/4 Criando o ambiente virtual (venv) =="
if [ ! -d venv ]; then
    if ! python3 -m venv venv; then
        echo ""
        echo "ERRO: nao consegui criar o venv (falta o pacote python3-venv)."
        echo "Use o PLANO B da apostila:"
        echo "   pip3 install --user -r requirements.txt"
        echo "   python3 carregar_exemplos.py"
        echo "   python3 -m uvicorn main:app --reload"
        rm -rf venv
        exit 1
    fi
fi

echo "== 2/4 Ativando o venv =="
source venv/bin/activate

echo "== 3/4 Instalando as bibliotecas =="
pip install --upgrade pip
if ! pip install -r requirements.txt; then
    echo ""
    echo "ERRO ao instalar. Confira se o computador tem internet."
    exit 1
fi

echo "== 4/4 Carregando o banco com os dados de exemplo =="
python3 carregar_exemplos.py

echo ""
python3 verificar_ambiente.py
echo "Agora rode:  source venv/bin/activate   e depois   uvicorn main:app --reload"
echo "E abra no navegador:  http://127.0.0.1:8000"
