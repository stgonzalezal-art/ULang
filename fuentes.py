#!/usr/bin/env python3
"""
Fuentes externas (solo metadatos, nunca terminos).

Regla de oro: de aqui salen CODIGOS y NOMBRES (hechos verificables con
procedencia). Las PALABRAS CLAVE de programacion NO se descargan: se
proponen desde literatura y se validan con hablantes.

Fuentes:
  - Wikidata (SPARQL), licencia CC0. Se cita el QID de cada lengua.
  - ISO 639-3 (tabla oficial SIL), CC-BY. Nombres de referencia en ingles.
  - Glottolog (CLDF), CC-BY 4.0. Glottocode, macroarea, familia y coordenadas.
  - CLDR (Unicode), Unicode-DFS-2016. Nombre en espanol cuando existe.

TODO con cache local en datos/cache/ (reutilizable sin red).
"""
from __future__ import annotations

import csv
import io
import json
import os
import time
import urllib.parse
import urllib.request

SPARQL = "https://query.wikidata.org/sparql"
UA = "ULang/0.1 (integracion linguistica; contacto: aseempresa01@gmail.com)"

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "datos", "cache")

SIL_TAB = "https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab"
GLOTTO_CSV = "https://raw.githubusercontent.com/glottolog/glottolog-cldf/master/cldf/languages.csv"
CLDR_LANGUAGES = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json/cldr-localenames-full/main/es/languages.json"

# P220 = codigo ISO 639-3, P17 = pais, P1098 = numero de hablantes
CONSULTA = """
SELECT ?item ?itemLabel ?code ?speakers WHERE {
  ?item wdt:P220 ?code ; wdt:P17 wd:%(pais)s .
  OPTIONAL { ?item wdt:P1098 ?speakers . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "es,en". }
}
"""


def _get(url: str, datos: dict, timeout: int = 40) -> dict:
    cuerpo = urllib.parse.urlencode(datos).encode("utf-8")
    req = urllib.request.Request(
        url, data=cuerpo, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _descargar(url: str, nombre: str, ttl_dias: int = 30, timeout: int = 90) -> str:
    """Descarga a datos/cache/ y reutiliza si es reciente (ttl_dias)."""
    os.makedirs(CACHE, exist_ok=True)
    ruta = os.path.join(CACHE, nombre)
    if os.path.isfile(ruta) and time.time() - os.path.getmtime(ruta) < ttl_dias * 86400:
        return ruta
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    tmp = ruta + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, ruta)
    return ruta


def sil_ref_names() -> dict[str, dict]:
    """Nombre de referencia ISO 639-3 (SIL). {iso3: {ref_name, tipo, ambito}}."""
    ruta = _descargar(SIL_TAB, "iso-639-3.tab", ttl_dias=60)
    salida: dict[str, dict] = {}
    with open(ruta, encoding="utf-8") as f:
        for fila in csv.DictReader(f, delimiter="\t"):
            if fila.get("Id"):
                salida[fila["Id"]] = {
                    "ref_name": fila.get("Ref_Name", "").strip(),
                    "tipo": fila.get("Language_Type", "").strip(),
                    "ambito": fila.get("Scope", "").strip(),
                }
    return salida


def glottolog_languages() -> list[dict]:
    """Lista CLDF de Glottolog (lenguas y familias)."""
    ruta = _descargar(GLOTTO_CSV, "glottolog-languages.csv", ttl_dias=30)
    with open(ruta, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def glottolog_map() -> dict[str, dict]:
    """{iso3: {glottocode, nombre, macroarea, familia, lat, lon}} para lenguas."""
    filas = glottolog_languages()
    familias = {f["ID"]: f for f in filas if f.get("Level") == "family"}
    salida: dict[str, dict] = {}
    for f in filas:
        iso = (f.get("ISO639P3code") or "").strip()
        if not iso:
            continue
        fam = familias.get(f.get("Family_ID", ""), {})
        salida[iso] = {
            "glottocode": f.get("Glottocode", "").strip(),
            "nombre": f.get("Name", "").strip(),
            "macroarea": f.get("Macroarea", "").strip(),
            "familia": fam.get("Name", "").strip(),
            "lat": f.get("Latitude", "").strip(),
            "lon": f.get("Longitude", "").strip(),
        }
    return salida


def cldr_es_names() -> dict[str, str]:
    """Nombre en espanol desde CLDR. {iso2/iso3: nombre}."""
    ruta = _descargar(CLDR_LANGUAGES, "cldr-es-languages.json", ttl_dias=60)
    with open(ruta, encoding="utf-8") as f:
        d = json.load(f)
    return d["main"]["es"]["localeDisplayNames"]["languages"]


def lenguas_de_pais(qid_pais: str = "Q739") -> list[dict]:
    """Devuelve [{qid, iso3, nombre, hablantes}] para un pais (Q739=Colombia)."""
    data = _get(SPARQL, {"query": CONSULTA % {"pais": qid_pais}})
    por_iso: dict[str, dict] = {}
    for f in data["results"]["bindings"]:
        iso = f["code"]["value"]
        reg = por_iso.setdefault(
            iso,
            {
                "iso3": iso,
                "qid": f["item"]["value"].rsplit("/", 1)[-1],
                "nombre": f.get("itemLabel", {}).get("value", iso),
                "hablantes": None,
                "fuente": {
                    "tipo": "wikidata",
                    "qid": f["item"]["value"].rsplit("/", 1)[-1],
                    "url": f["item"]["value"],
                    "licencia": "CC0",
                },
                "estado": "propuesto_sin_validar",
            },
        )
        h = f.get("speakers", {}).get("value")
        if h:
            try:
                h = int(float(h))
                if reg["hablantes"] is None or h > reg["hablantes"]:
                    reg["hablantes"] = h
            except ValueError:
                pass
    return sorted(por_iso.values(), key=lambda x: x["nombre"])


if __name__ == "__main__":
    for l in lenguas_de_pais():
        print(f"{l['iso3']:>4}  {l['nombre'][:45]:<46} {l['hablantes'] or '?':>10}  {l['qid']}")
