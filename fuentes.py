#!/usr/bin/env python3
"""
Fuentes externas (solo metadatos, nunca terminos).

Regla de oro: de aqui salen CODIGOS y NOMBRES (hechos verificables con
procedencia). Las PALABRAS CLAVE de programacion NO se descargan: se
proponen desde literatura y se validan con hablantes.

Fuente: Wikidata (SPARQL), licencia CC0. Se cita el QID de cada lengua.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

SPARQL = "https://query.wikidata.org/sparql"
UA = "ULang/0.1 (integracion linguistica; contacto: aseempresa01@gmail.com)"

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
