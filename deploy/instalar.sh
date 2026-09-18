#!/usr/bin/env bash
# Instala ULang en un servidor Debian/Ubuntu (ej. Oracle Cloud Always Free).
# Uso:  sudo bash deploy/instalar.sh
set -euo pipefail

ORIGEN="$(cd "$(dirname "$0")/.." && pwd)"
DESTINO="/opt/ulang"
USUARIO="ulang"

echo "==> Usuario de servicio"
id -u "$USUARIO" >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin "$USUARIO"

echo "==> Copiando proyecto a $DESTINO"
mkdir -p "$DESTINO"
rsync -a --delete \
  --exclude '.git' --exclude '__pycache__' --exclude 'datos' \
  "$ORIGEN"/ "$DESTINO"/
mkdir -p "$DESTINO/datos" "$DESTINO/datos/propuestas" "$DESTINO/lexicons/propuestos"

echo "==> Entorno virtual"
apt-get update -y
apt-get install -y python3 python3-venv rsync
python3 -m venv "$DESTINO/venv"
"$DESTINO/venv/bin/pip" install --no-cache-dir -r "$DESTINO/requirements.txt"

if [ ! -f "$DESTINO/.env" ]; then
  cp "$DESTINO/.env.example" "$DESTINO/.env"
  echo "    -> edita $DESTINO/.env (clave del modelo)"
fi

chown -R "$USUARIO:$USUARIO" "$DESTINO"

echo "==> systemd"
cp "$DESTINO"/deploy/ulang-*.service "$DESTINO"/deploy/ulang-*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now ulang-servidor.service ulang-trabajador.service
systemctl enable --now ulang-agente.timer

echo
echo "Listo. Comandos utiles:"
echo "  systemctl status ulang-servidor"
echo "  systemctl status ulang-trabajador"
echo "  systemctl list-timers ulang-agente.timer"
echo "  journalctl -u ulang-trabajador -f"
echo "  curl http://localhost:8080/estado"
