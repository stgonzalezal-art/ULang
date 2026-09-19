#!/usr/bin/env python3
"""
Proponer (pipeline de metadatos multi-fuente -> propuestas).

Error comun a evitar: este pipeline NO inventa palabras clave. Lo que hace es:
  1) enriquecer datos/catalogo.json con metadatos de varias fuentes
     (Wikidata, ISO 639-3 SIL, Glottolog CLDF, CLDR), conservando el estado,
  2) generar/refrescar las propuestas de lexicon en datos/propuestas/
     marcadas 'propuesto' para que un humano (o el agente) las rellene con
     literatura y despues las valide con revisar.py.

Formato propuesta (datos/propuestas/<iso3>.json):
    {idioma, iso3, estado: "propuesto", palabras: {CATEGORIA: null|"..."},
     referencias: [...], fuente_metadatos: {...fuentes fusionadas...}}

Uso:
    python3 proponer.py                       # enriquece y refresca propuestas
    python3 proponer.py --solo-enriquecer     # solo metadatos, no propuestas
    python3 proponer.py --revisar            # reporte de pendientes/validados
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os

import fuentes
import trabajador

BASE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(BASE, "datos")
PROPUESTAS = os.path.join(DATOS, "propuestas")
CATALOGO = trabajador.CATALOGO
LOG = os.path.join(DATOS, "proponer.log")

# Categorias canonicas de ULang (valores de es.json y del prompt del agente).
CATEGORIAS = ["FUNC", "RETURN", "PRINT", "IF", "ELSE", "WHILE",
              "TRUE", "FALSE", "AND", "OR", "NOT", "END"]

ORIGEN = {
    "wikidata": "Wikidata (CC0)",
    "sil": "ISO 639-3 SIL (CC-BY)",
    "glottolog": "Glottolog CLDF (CC-BY 4.0)",
    "cldr": "CLDR Unicode (Unicode-DFS-2016)",
}


def ahora() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def log(msg: str) -> None:
    linea = f"{ahora()}  {msg}"
    print(linea, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def enriquecer(catalogo: dict) -> dict:
    """Agrega sil/glottolog/cldr a cada entrada manteniendo estado y fuente.

    SIEMPRE reconstruye fuente_metadatos con datos frescos (idempotente);
    conserva solo la fuente Wikidata original y el estado validado."""
    sil = fuentes.sil_ref_names()
    gl = fuentes.glottolog_map()
    cldr = fuentes.cldr_es_names()

    for iso, e in catalogo.items():
        e = dict(e)
        if not e.get("fuente") and isinstance(e.get("fuente_metadatos"), dict):
            f = e["fuente_metadatos"]
            if isinstance(f.get("wikidata"), dict) and f["wikidata"].get("tipo") == "wikidata":
                e["fuente"] = f["wikidata"]
        meta: dict = {}
        if isinstance(e.get("fuente"), dict) and e["fuente"].get("tipo") == "wikidata":
            meta["wikidata"] = e["fuente"]
        s = sil.get(iso)
        g = gl.get(iso)
        c = cldr.get(iso)  # solo codigo exacto; nunca derivados (guc != gu)
        if s:
            meta["sil"] = {
                "ref_name": s["ref_name"], "tipo": s["tipo"], "ambito": s["ambito"],
                "fuente": {"tipo": "sil", "licencia": ORIGEN["sil"], "url": "https://iso639-3.sil.org/code/" + iso},
            }
        if g:
            meta["glottolog"] = {
                "glottocode": g["glottocode"], "nombre": g["nombre"],
                "macroarea": g["macroarea"], "familia": g["familia"],
                "lat": g["lat"], "lon": g["lon"],
                "fuente": {"tipo": "glottolog", "licencia": ORIGEN["glottolog"],
                           "url": "https://glottolog.org/resource/languoid/id/" + g["glottocode"] if g["glottocode"] else "https://glottolog.org"},
            }
        if c:
            meta["cldr"] = {"nombre_es": c,
                            "fuente": {"tipo": "cldr", "licencia": ORIGEN["cldr"],
                                       "url": "https://github.com/unicode-org/cldr"}}
        if meta:
            e["fuente_metadatos"] = meta
        catalogo[iso] = e
    return catalogo


def refrescar_propuesta(l: dict) -> tuple[bool, str]:
    """Genera (o refresca) la propuesta 'propuesto' sin tocar palabras existentes."""
    iso = l["iso3"]
    ruta = os.path.join(PROPUESTAS, iso + ".json")
    plantilla = {
        "idioma": l["nombre"],
        "iso3": iso,
        "estado": "propuesto",
        "nota": (
            "Generada por el pipeline de metadatos. Las palabras clave deben "
            "rellenarse desde literatura publicada o hablantes (nunca inventarse) "
            "y validarse con revisar.py."
        ),
        "fuente_metadatos": l.get("fuente_metadatos") or {"wikidata": l.get("fuente")},
        "referencias": [],
        "palabras": {c: None for c in CATEGORIAS},
    }
    if os.path.isfile(ruta):
        prev = cargar_json(ruta, {})
        if prev.get("estado") == "validado":
            return False, "ya_validado"
        # Conservar trabajo previo (palabras y referencias) que el humano/agente puso.
        plantilla["palabras"] = {c: prev.get("palabras", {}).get(c) for c in CATEGORIAS}
        plantilla["referencias"] = prev.get("referencias") or []
        plantilla["nota"] = plantilla["nota"] if not any(v for v in plantilla["palabras"].values()) else prev.get("nota") or plantilla["nota"]
        modo = "refrescada"
    else:
        modo = "creada"
        if l.get("estado") == "validado" or l.get("palabras_validadas"):
            return False, "ya_validado"
    guardar_json(ruta, plantilla)
    return True, modo


def cargar_json(ruta, defecto=None):
    if os.path.isfile(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    return defecto


def guardar_json(ruta, obj) -> None:
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def reporte() -> None:
    cat = cargar_json(CATALOGO, {})
    validadas = sum(1 for l in cat.values() if l.get("estado") == "validado")
    pendientes = len(cat) - validadas
    props = os.listdir(PROPUESTAS) if os.path.isdir(PROPUESTAS) else []
    con_palabras = 0
    for nombre in props:
        p = cargar_json(os.path.join(PROPUESTAS, nombre))
        if p and any(p.get("palabras", {}).values()):
            con_palabras += 1
    print(f"Catalogo: {len(cat)} lenguas | validadas: {validadas} | pendientes: {pendientes}")
    print(f"Propuestas en datos/propuestas/: {len(props)} | con palabras: {con_palabras}")
    print("Ejecuta  python3 proponer.py  para generar/refrescar las propuestas.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Pipeline de propuestas de lexicon (multifuente, sin IA)")
    ap.add_argument("--solo-enriquecer", action="store_true", help="solo metadatos, no tocar propuestas")
    ap.add_argument("--revisar", action="store_true", help="solo reporte, no tocar nada")
    ap.add_argument("--max", type=int, default=0, help="maximo de propuestas a crear/refrescar (0=todas)")
    args = ap.parse_args()

    os.makedirs(PROPUESTAS, exist_ok=True)
    if args.revisar:
        reporte()
        return

    catalogo = cargar_json(CATALOGO, {})
    if not catalogo:
        print("Catalogo vacio. Corre primero:  python3 trabajador.py --una-vez")
        return
    log(f"enriqueciendo {len(catalogo)} lenguas (sil/glottolog/cldr)...")
    catalogo = enriquecer(catalogo)
    guardar_json(CATALOGO, catalogo)
    log("catalogo enriquecido y guardado")

    if not args.solo_enriquecer:
        hechas = {"creada": 0, "refrescada": 0, "ya_validado": 0}
        for l in catalogo.values():
            try:
                ok, modo = refrescar_propuesta(l)
            except Exception as e:
                log(f"ERROR {l['iso3']}: {e}")
                continue
            hechas[modo] = hechas.get(modo, 0) + 1
            if args.max and hechas["creada"] + hechas["refrescada"] >= args.max:
                break
        log(f"propuestas: {json.dumps(hechas)}")
        reporte()


if __name__ == "__main__":
    main()