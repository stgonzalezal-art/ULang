#!/usr/bin/env python3
"""
Trabajador 24/7 (deterministico, sin IA): mantiene el catalogo de lenguas
al dia desde fuentes externas y prepara las plantillas que luego un humano
(y opcionalmente el agente) deben llenar.

NO inventa terminos. Solo:
  - descarga METADATOS (codigo ISO 639-3, nombre, hablantes, QID de Wikidata),
  - conserva la procedencia y el estado,
  - crea plantillas vacias marcadas 'propuesto_sin_validar',
  - registra todo en datos/trabajador.log.

Uso:
    python3 trabajador.py --intervalo 3600        # bucle infinito
    python3 trabajador.py --una-vez               # una pasada (pruebas/cron)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time

import fuentes

BASE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(BASE, "datos")
PROPUESTOS = os.path.join(BASE, "lexicons", "propuestos")
CATALOGO = os.path.join(DATOS, "catalogo.json")
ESTADO = os.path.join(DATOS, "estado_trabajador.json")
LOG = os.path.join(DATOS, "trabajador.log")


def ahora() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def log(msg: str) -> None:
    linea = f"{ahora()}  {msg}"
    print(linea, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def cargar_json(ruta, defecto):
    if os.path.isfile(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    return defecto


def fusionar(catalogo: dict, nuevos: list[dict]) -> tuple[dict, int, int]:
    """Conserva el estado ya validado; nunca lo degrada."""
    nuevos_n = 0
    for l in nuevos:
        prev = catalogo.get(l["iso3"])
        if prev:
            l["estado"] = prev.get("estado", l["estado"])
            if prev.get("palabras_validadas"):
                l["palabras_validadas"] = prev["palabras_validadas"]
        else:
            nuevos_n += 1
        catalogo[l["iso3"]] = l
    return catalogo, nuevos_n, len(nuevos)


def preparar_plantilla(l: dict) -> bool:
    ruta = os.path.join(PROPUESTOS, l["iso3"] + ".json")
    if os.path.isfile(ruta):
        return False
    plantilla = {
        "idioma": l["nombre"],
        "iso3": l["iso3"],
        "estado": "propuesto_sin_validar",
        "nota": (
            "PLANTILLA VACIA. Las palabras clave deben provenir de literatura "
            "publicada o de hablantes; nunca inventarse. Al validar, cambiar "
            "'estado' a 'validado' y anadir las referencias."
        ),
        "fuente_metadatos": l["fuente"],
        "referencias": [],
        "palabras": {},
    }
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(plantilla, f, ensure_ascii=False, indent=2)
    return True


def pasada() -> dict:
    log("inicia pasada: consultando fuentes (Wikidata)...")
    try:
        nuevos = fuentes.lenguas_de_pais("Q739")
    except Exception as e:
        log(f"ERROR consultando fuentes: {type(e).__name__}: {e}")
        return {"ok": False, "error": str(e)}

    catalogo = cargar_json(CATALOGO, {})
    catalogo, agregadas, total_fuente = fusionar(catalogo, nuevos)
    os.makedirs(PROPUESTOS, exist_ok=True)

    plantillas = sum(preparar_plantilla(l) for l in catalogo.values())

    with open(CATALOGO, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)

    validadas = sum(1 for l in catalogo.values() if l.get("estado") == "validado")
    pendientes = len(catalogo) - validadas
    estado = {
        "ultima_ejecucion": ahora(),
        "fuente": "Wikidata (CC0)",
        "pais": "Colombia (Q739)",
        "lenguas_catalogo": len(catalogo),
        "nuevas_esta_pasada": agregadas,
        "total_fuente": total_fuente,
        "plantillas_creadas": plantillas,
        "validadas": validadas,
        "pendientes_validacion": pendientes,
        "ok": True,
    }
    with open(ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
    log(
        f"pasada OK: catalogo={len(catalogo)} nuevas={agregadas} "
        f"plantillas={plantillas} validadas={validadas} pendientes={pendientes}"
    )
    return estado


def main() -> None:
    ap = argparse.ArgumentParser(description="Trabajador 24/7 de catalogo de lenguas")
    ap.add_argument("--intervalo", type=int, default=3600, help="segundos entre pasadas")
    ap.add_argument("--una-vez", action="store_true", help="una sola pasada y salir")
    args = ap.parse_args()

    os.makedirs(DATOS, exist_ok=True)
    os.makedirs(PROPUESTOS, exist_ok=True)
    log(f"trabajador arrancado (intervalo={args.intervalo}s, una_vez={args.una_vez})")

    while True:
        pasada()
        if args.una_vez:
            break
        time.sleep(max(60, args.intervalo))


if __name__ == "__main__":
    main()
