#!/usr/bin/env python3
"""
Puerta de revision humana: propuesto -> validado.

Nada pasa a un lexicon real sin:
  - una referencia verificable por CADA palabra,
  - la confirmacion de una persona,
  - y palabras que no se repitan (mapeo inequivoco).

La propuesta viene de datos/propuestas/<iso3>.json (formato: canonico -> palabra).
El lexicon validado se escribe al reves (palabra -> canonico), como en es.json.

Uso:
    python3 revisar.py listar
    python3 revisar.py ver guc
    python3 revisar.py promover guc            # pide confirmacion
    python3 revisar.py promover guc --si       # sin preguntar
    python3 revisar.py promover guc --forzar   # sobrescribe uno ya validado
    python3 revisar.py rechazar guc
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(BASE, "datos")
PROPUESTAS = os.path.join(DATOS, "propuestas")
LEXICONS = os.path.join(BASE, "lexicons")
CATALOGO = os.path.join(DATOS, "catalogo.json")


def ahora() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def cargar(ruta, defecto=None):
    if not os.path.isfile(ruta):
        return defecto
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def guardar(ruta, obj) -> None:
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def ruta_propuesta(iso3):
    return os.path.join(PROPUESTAS, iso3 + ".json")


def ruta_lexicon(iso3):
    return os.path.join(LEXICONS, iso3 + ".json")


def listar() -> None:
    props = sorted(f[:-5] for f in os.listdir(PROPUESTAS)) if os.path.isdir(PROPUESTAS) else []
    validados = sorted(
        f[:-5] for f in os.listdir(LEXICONS)
        if f.endswith(".json") and os.path.isfile(os.path.join(LEXICONS, f))
    )
    print(f"Propuestas pendientes ({len(props)}):")
    for iso in props:
        p = cargar(ruta_propuesta(iso), {})
        n = sum(1 for v in p.get("palabras", {}).values() if v)
        print(f"  {iso:<5} {p.get('idioma','?'):<28} palabras={n}")
    print(f"\nLexicones validados ({len(validados)}): {', '.join(validados) or '(ninguno)'}")


def ver(iso3: str) -> int:
    p = cargar(ruta_propuesta(iso3))
    if not p:
        print(f"No hay propuesta para '{iso3}'")
        return 1
    print(f"Propuesta {iso3} - {p.get('idioma')} [{p.get('estado')}]")
    for k, v in p.get("palabras", {}).items():
        print(f"  {k:<7} -> {v if v else '(sin propuesta)'}")
    refs = p.get("referencias", [])
    print(f"Referencias: {len(refs)}")
    for r in refs:
        print(f"  [{r.get('categoria')}] {r.get('cita')} {r.get('enlace','')}")
    return 0


def promover(iso3: str, si: bool, forzar: bool) -> int:
    p = cargar(ruta_propuesta(iso3))
    if not p:
        print(f"No hay propuesta para '{iso3}'")
        return 1
    if p.get("estado") == "validado":
        print(f"'{iso3}' ya figura como validado")
        return 1
    if os.path.isfile(ruta_lexicon(iso3)) and not forzar:
        print(f"Ya existe lexicons/{iso3}.json. Usa --forzar para sobrescribir.")
        return 1

    palabras = {k: v for k, v in p.get("palabras", {}).items() if v}
    if not palabras:
        print("La propuesta no tiene ninguna palabra; nada que validar.")
        return 1

    refs = [r for r in p.get("referencias", []) if r.get("cita")]
    categorias = {r.get("categoria") for r in refs}
    faltan = sorted(k for k in palabras if k not in categorias)
    if faltan:
        print("RECHAZADO: estas palabras no tienen referencia verificable:")
        for k in faltan:
            print(f"  - {k} ({palabras[k]})")
        print("Anade la cita (autor, obra, anio, enlace) antes de validar.")
        return 1

    superficie = list(palabras.values())
    if len(set(superficie)) != len(superficie):
        dup = sorted({w for w in superficie if superficie.count(w) > 1})
        print(f"RECHAZADO: palabras ambiguas (misma superficie para dos categorias): {dup}")
        return 1
    invalidas = [w for w in superficie if not isinstance(w, str) or " " in w or "(" in w or "," in w]
    if invalidas:
        print(f"RECHAZADO: superficies invalidas (espacios o signos): {invalidas}")
        return 1

    print(f"Validar {iso3} ({p.get('idioma')}) con {len(palabras)} palabras:")
    for k, v in palabras.items():
        print(f"  {k:<7} -> {v}")
    if not si:
        if input("Confirmas? [s/N] ").strip().lower() not in ("s", "si", "y", "yes"):
            print("Cancelado.")
            return 1

    lexicon = {
        "idioma": p.get("idioma"),
        "iso3": iso3,
        "estado": "validado",
        "nota": "Lexicon validado por revision humana; cada palabra tiene referencia.",
        "fuente_metadatos": p.get("fuente_metadatos"),
        "referencias": refs,
        "palabras": {v: k for k, v in palabras.items()},  # palabra -> canonico
        "validado_por": "revision_humana",
        "fecha_validacion": ahora(),
    }
    guardar(ruta_lexicon(iso3), lexicon)

    cat = cargar(CATALOGO, {})
    if iso3 in cat:
        cat[iso3]["estado"] = "validado"
        cat[iso3]["palabras_validadas"] = len(palabras)
        guardar(CATALOGO, cat)

    os.remove(ruta_propuesta(iso3))
    print(f"OK: lexicons/{iso3}.json validado y propuesta archivada.")
    return 0


def rechazar(iso3: str) -> int:
    if not os.path.isfile(ruta_propuesta(iso3)):
        print(f"No hay propuesta para '{iso3}'")
        return 1
    os.remove(ruta_propuesta(iso3))
    print(f"Propuesta '{iso3}' descartada.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Revision humana de propuestas de lexicon")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("listar")
    pv = sub.add_parser("ver"); pv.add_argument("iso3")
    pp = sub.add_parser("promover")
    pp.add_argument("iso3")
    pp.add_argument("--si", action="store_true", help="no pedir confirmacion")
    pp.add_argument("--forzar", action="store_true", help="sobrescribir lexicon existente")
    pr = sub.add_parser("rechazar"); pr.add_argument("iso3")
    args = ap.parse_args()

    if args.cmd in (None, "listar"):
        listar(); return 0
    if args.cmd == "ver":
        return ver(args.iso3)
    if args.cmd == "promover":
        return promover(args.iso3, args.si, args.forzar)
    if args.cmd == "rechazar":
        return rechazar(args.iso3)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
