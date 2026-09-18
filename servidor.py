#!/usr/bin/env python3
"""
Servidor HTTP de ULang (Flask). Pensado para correr en un servidor gratuito.

Endpoints:
  GET  /                     -> salud + indice
  GET  /estado               -> estado del trabajador
  GET  /catalogo             -> lenguas conocidas (metadatos + procedencia)
  GET  /lexicons             -> lexicones disponibles y su estado
  POST /compilar             -> {fuente, lexicon}  -> IR, Python y salida
  POST /traducir             -> {fuente, origen, destino} -> superficie + salida
"""
from __future__ import annotations

import io
import contextlib
import json
import os

from flask import Flask, jsonify, request

import ulang
import trabajador

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))


def _ejecutar(py: str) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(py, "<ulang>", "exec"), {})
    return buf.getvalue()


def _error(msg, code=400):
    return jsonify({"ok": False, "error": msg}), code


@app.get("/")
def raiz():
    return jsonify({
        "ok": True,
        "servicio": "ULang",
        "descripcion": "capa de integracion multilingue (lengua -> IR -> codigo)",
        "endpoints": ["/estado", "/catalogo", "/lexicons",
                      "POST /compilar", "POST /traducir"],
    })


@app.get("/estado")
def estado():
    return jsonify(trabajador.cargar_json(trabajador.ESTADO, {"ok": False, "nota": "sin pasadas aun"}))


@app.get("/catalogo")
def catalogo():
    return jsonify(trabajador.cargar_json(trabajador.CATALOGO, {}))


@app.get("/lexicons")
def lexicons():
    out = {}
    for carpeta in (ulang.LEXICONS, os.path.join(ulang.LEXICONS, "propuestos")):
        if not os.path.isdir(carpeta):
            continue
        for nombre in sorted(os.listdir(carpeta)):
            if nombre.endswith(".json"):
                with open(os.path.join(carpeta, nombre), encoding="utf-8") as f:
                    d = json.load(f)
                out[nombre[:-5]] = {
                    "idioma": d.get("idioma"),
                    "estado": d.get("estado"),
                    "palabras": len(d.get("palabras", {})),
                    "iso3": d.get("iso3"),
                }
    return jsonify(out)


@app.post("/compilar")
def compilar():
    datos = request.get_json(silent=True) or {}
    fuente, lexicon = datos.get("fuente"), datos.get("lexicon", "es")
    if not fuente:
        return _error("falta 'fuente'")
    try:
        data, superficie = ulang.cargar_lexicon(ulang.buscar_lexicon(lexicon))
        ir = ulang.Parser(ulang.tokenizar(fuente, superficie, "api"), "api").parsear()
        py = ulang.generar_python(ir)
        return jsonify({"ok": True, "lengua": data.get("idioma"),
                        "estado": data.get("estado"), "ir": ir,
                        "python": py, "salida": _ejecutar(py)})
    except ulang.ErrorULang as e:
        return _error(str(e), 422)
    except Exception as e:
        return _error(f"{type(e).__name__}: {e}", 500)


@app.post("/traducir")
def traducir():
    datos = request.get_json(silent=True) or {}
    fuente = datos.get("fuente")
    origen, destino = datos.get("origen", "es"), datos.get("destino")
    if not fuente or not destino:
        return _error("faltan 'fuente' y/o 'destino'")
    try:
        _, sup_origen = ulang.cargar_lexicon(ulang.buscar_lexicon(origen))
        ir = ulang.Parser(ulang.tokenizar(fuente, sup_origen, "api"), "api").parsear()
        data2, sup2 = ulang.cargar_lexicon(ulang.buscar_lexicon(destino))
        inv = {c: p for p, c in data2.get("palabras", {}).items()}
        texto = ulang.generar_superficie(ir, inv, data2.get("idioma", "?"))
        ir2 = ulang.Parser(ulang.tokenizar(texto, sup2, "traducido"), "traducido").parsear()
        return jsonify({"ok": True, "destino": data2.get("idioma"),
                        "traduccion": texto,
                        "misma_ir": ir == ir2,
                        "salida": _ejecutar(ulang.generar_python(ir2))})
    except ulang.ErrorULang as e:
        return _error(str(e), 422)
    except Exception as e:
        return _error(f"{type(e).__name__}: {e}", 500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
