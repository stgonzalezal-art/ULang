#!/usr/bin/env bash
# Crea el Space en Hugging Face y sube el proyecto.
# Requiere haberse autenticado antes (una vez):
#     /home/styven/.hf-ulang/bin/hf auth login
#
# Uso:  bash deploy/subir_hf.sh TU_USUARIO [NOMBRE_SPACE]
set -euo pipefail

HF="/home/styven/.hf-ulang/bin/hf"
PROYECTO="$(cd "$(dirname "$0")/.." && pwd)"
USUARIO="${1:?Falta tu usuario de Hugging Face. Ej: bash deploy/subir_hf.sh styven}"
SPACE="${2:-ULang}"
REPO="$USUARIO/$SPACE"

if ! "$HF" auth whoami >/dev/null 2>&1; then
  echo "ERROR: no has iniciado sesion. Corre primero:"
  echo "    $HF auth login"
  exit 1
fi

echo "==> Creando Space $REPO (Docker, publico)"
"$HF" repos create "$REPO" --type space --sdk docker --public --exist-ok

echo "==> Subiendo contenido de $PROYECTO"
"$HF" upload "$REPO" "$PROYECTO" --type space \
  --exclude ".git/*" \
  --exclude "__pycache__/*" \
  --exclude "*.pyc" \
  --exclude "datos/*.log" \
  --exclude ".hf-ulang/*"

echo
echo "Listo. Space: https://huggingface.co/spaces/$REPO"
echo "App:   https://${USUARIO//_/-}-${SPACE,,}.hf.space"
echo "Prueba: curl https://${USUARIO//_/-}-${SPACE,,}.hf.space/estado"
