#!/usr/bin/env python3
"""
Arranque para un servicio gratuito (Hugging Face Spaces, Docker).

Levanta dos cosas en el MISMO contenedor:
  1. un hilo demonio que corre el trabajador (catalogo, sin IA) cada
     INTERVALO_TRABAJADOR segundos;
  2. el servidor HTTP de ULang en el puerto $PORT (HF espera 7860).

Economico: el trabajo de catalogo es liviano y no usa IA.
"""
from __future__ import annotations

import os
import threading
import time

import servidor
import trabajador


def bucle() -> None:
    intervalo = int(os.environ.get("INTERVALO_TRABAJADOR", "21600"))  # 6 h
    time.sleep(20)  # deja arrancar el servidor primero
    while True:
        try:
            trabajador.pasada()
        except Exception as e:  # nunca tumba el servidor
            try:
                trabajador.log(f"fallo en bucle del trabajador: {type(e).__name__}: {e}")
            except Exception:
                pass
        time.sleep(max(300, intervalo))


if __name__ == "__main__":
    os.makedirs(trabajador.DATOS, exist_ok=True)
    os.makedirs(trabajador.PROPUESTOS, exist_ok=True)
    threading.Thread(target=bucle, daemon=True).start()
    servidor.app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "7860")))
