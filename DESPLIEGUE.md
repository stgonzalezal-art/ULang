# Despliegue económico 24/7 (Oracle Cloud Always Free)

Objetivo: servidor + trabajador corriendo día y noche sin costo de cómputo.
La IA (agente nocturno) va aparte, en lotes acotados, porque sí consume tokens.

## 0. Qué corre dónde
| Proceso | Corre | Costo |
|---|---|---|
| `servidor.py` (API HTTP) | 24/7 | gratis (VM) |
| `trabajador.py` (catálogo, sin IA) | 24/7 | gratis (VM) |
| `agente_nocturno.py` (IA) | 1 vez/día, lote acotado | tokens por uso |
| Revisión humana | manual | tu tiempo |

## 1. Crear la VM (Oracle Cloud Always Free)
1. Cuenta en Oracle Cloud (Always Free).
2. Instancia con forma **VM.Standard.A1.Flex** (ARM Ampere, Always Free), Ubuntu 22.04/24.04.
3. Sube tu llave SSH pública.
4. En la VCN, abre en la Security List: TCP **8080** (o 80/443 si usas proxy).
5. En la VM abre el firewall: `sudo ufw allow 8080/tcp`.

Alternativa: **GCP e2-micro Always Free** (us-west1/us-central1/us-east1).

## 2. Instalar ULang
```bash
sudo apt-get update -y && sudo apt-get install -y git rsync
# copia el proyecto al servidor (git clone o rsync desde tu maquina)
cd lengua_universal
sudo bash deploy/instalar.sh
```
Deja `servidor.py` y `trabajador.py` como servicios systemd y el agente
como timer diario a las 02:00.

## 3. Instalar opencode (para el agente)
Sigue las instrucciones oficiales de https://opencode.ai e inicia sesión/
configura la clave del modelo. Luego edita `/opt/ulang/.env`:
```
OPENCODE_CMD=opencode run
OPENCODE_MODEL=opencode/big-pickle
# y la clave del proveedor
```
Prueba sin gastar:
```bash
sudo -u ulang /opt/ulang/venv/bin/python /opt/ulang/agente_nocturno.py --dry-run
```

## 4. Operación
```bash
systemctl status ulang-servidor ulang-trabajador
systemctl list-timers ulang-agente.timer
journalctl -u ulang-trabajador -f
curl http://localhost:8080/estado
```

## 5. Control de gasto (importante)
- `--max-lenguas` y `--presupuesto-min` limitan cada corrida del agente.
- El agente **nunca** marca `validado`; solo escribe `datos/propuestas/`.
- Revisa a mano y promueve a `lexicons/<iso3>.json` con estado `validado`
  y las referencias. Sin esa puerta, no hay verdad.
- Pon límites de gasto en el panel del proveedor del modelo.

## 6. Legal
- Cita autor, obra, año y enlace de cada fuente usada (APA al final).
- Wikidata es CC0; respeta la licencia de cada diccionario/gramática.
- Para conocimiento de comunidades indígenas, la Ley 1381/2010 exige
  concertación: la cita bibliográfica no la reemplaza.
