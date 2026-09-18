#!/usr/bin/env python3
"""
Agente nocturno: IA en lotes acotados para PROPONER palabras clave.

Reglas duras:
  - NUNCA marca 'validado'. Todo sale como 'propuesto_sin_validar'.
  - Si no hay literatura/fuente citada, devuelve la palabra como null.
  - Solo escribe en datos/propuestas/ (nada de tocar lexicons/validados).

Guardas economicas:
  --max-lenguas      cuantas lenguas por corrida           (default 3)
  --timeout          segundos max por lengua                (default 900)
  --presupuesto-min  minutos totales max por corrida        (default 30)
  --dry-run          no invoca la IA, solo muestra el plan

El comando de IA es configurable:
  OPENCODE_CMD="opencode run"           (por defecto)
  OPENCODE_MODEL="opencode/big-pickle"  (opcional, se agrega con --model)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import shutil
import subprocess
import time

BASE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(BASE, "datos")
PROPUESTAS = os.path.join(DATOS, "propuestas")
CATALOGO = os.path.join(DATOS, "catalogo.json")
LOG = os.path.join(DATOS, "agente.log")
VALIDOS = os.path.join(BASE, "lexicons")

PROMPT = """Eres un linguista-computacional asistente para ULang.
Tarea: PROPONER palabras clave de programacion en la lengua "{nombre}" (ISO 639-3: {iso3}).

Necesito estas categorias (JSON): FUNC, RETURN, IF, ELSE, WHILE, TRUE, FALSE, AND, OR, NOT, PRINT, END.

Reglas ESTRICTAS:
1. Usa SOLO literatura publicada, gramaticas, diccionarios o hablantes citables.
2. Si no tienes una fuente verificable para una palabra, pon null. NO inventes.
3. Cada palabra propuesta debe traer su referencia (autor, obra, anio, enlace).
4. Marca estado = "propuesto_sin_validar". NUNCA "validado".
5. Responde UNICAMENTE con un objeto JSON con esta forma:
{{"iso3": "{iso3}", "estado": "propuesto_sin_validar",
  "palabras": {{"FUNC": null, "PRINT": null, ...}},
  "referencias": [{{"categoria": "FUNC", "cita": "...", "enlace": "..."}}]}}
"""


def ahora() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def log(msg: str) -> None:
    linea = f"{ahora()}  {msg}"
    print(linea, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def cargar_catalogo() -> dict:
    if not os.path.isfile(CATALOGO):
        return {}
    with open(CATALOGO, encoding="utf-8") as f:
        return json.load(f)


def pendientes(catalogo: dict, maximo: int) -> list[dict]:
    out = []
    for iso, l in sorted(catalogo.items()):
        if l.get("estado") == "validado":
            continue
        if os.path.isfile(os.path.join(PROPUESTAS, iso + ".json")):
            continue
        if os.path.isfile(os.path.join(VALIDOS, iso + ".json")):
            continue
        out.append(l)
        if len(out) >= maximo:
            break
    return out


def extraer_json(texto: str) -> dict | None:
    m = re.search(r"\{.*\}", texto, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def invocar(prompt: str, timeout: int, modelo: str | None) -> str:
    cmd = shlex.split(os.environ.get("OPENCODE_CMD", "opencode run"))
    if modelo:
        cmd += ["--model", modelo]
    cmd.append(prompt)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"IA salio con codigo {r.returncode}: {r.stderr[:300]}")
    return r.stdout


def main() -> None:
    ap = argparse.ArgumentParser(description="Agente nocturno (IA en lotes acotados)")
    ap.add_argument("--max-lenguas", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--presupuesto-min", type=int, default=30)
    ap.add_argument("--modelo", default=os.environ.get("OPENCODE_MODEL"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    os.makedirs(PROPUESTAS, exist_ok=True)
    if args.dry_run:
        log("DRY-RUN: no se invocara IA ni se gastaran tokens")

    catalogo = cargar_catalogo()
    if not catalogo:
        log("catalogo vacio: corre primero  python3 trabajador.py --una-vez")
        return

    tareas = pendientes(catalogo, args.max_lenguas)
    log(f"lote: {len(tareas)} lenguas (max={args.max_lenguas}, presupuesto={args.presupuesto_min} min)")
    if not shutil.which(shlex.split(os.environ.get("OPENCODE_CMD", "opencode run"))[0]) and not args.dry_run:
        log("AVISO: 'opencode' no esta en el PATH; usa --dry-run o instala opencode")
        return

    inicio = time.monotonic()
    hechas = 0
    for l in tareas:
        if (time.monotonic() - inicio) / 60 >= args.presupuesto_min:
            log("presupuesto agotado: se detiene el lote (no se gasta mas)")
            break
        prompt = PROMPT.format(nombre=l["nombre"], iso3=l["iso3"])
        if args.dry_run:
            log(f"[DRY-RUN] procesaria {l['iso3']} ({l['nombre']})")
            continue
        log(f"procesando {l['iso3']} ({l['nombre']}) ...")
        try:
            salida = invocar(prompt, args.timeout, args.modelo)
        except Exception as e:
            log(f"ERROR en {l['iso3']}: {type(e).__name__}: {e}")
            continue
        prop = extraer_json(salida)
        if not prop or not isinstance(prop.get("palabras"), dict):
            log(f"{l['iso3']}: respuesta sin JSON valido, se descarta")
            continue
        prop["estado"] = "propuesto_sin_validar"
        prop["iso3"] = l["iso3"]
        prop["idioma"] = l["nombre"]
        prop.setdefault("fuente_metadatos", l.get("fuente"))
        prop["generado_por"] = "agente_nocturno"
        prop["fecha"] = ahora()
        prop["validado_por_humano"] = False
        with open(os.path.join(PROPUESTAS, l["iso3"] + ".json"), "w", encoding="utf-8") as f:
            json.dump(prop, f, ensure_ascii=False, indent=2)
        puestas = sum(1 for v in prop["palabras"].values() if v)
        log(f"{l['iso3']}: propuestas={puestas}/{len(prop['palabras'])} -> datos/propuestas/{l['iso3']}.json")
        hechas += 1

    log(f"lote terminado: {hechas} lenguas con propuesta (revision humana pendiente)")


if __name__ == "__main__":
    main()
