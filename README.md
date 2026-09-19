---
title: ULang
emoji: 🗣️
colorFrom: indigo
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
---

# ULang

Capa de integración multilingüe: una **lengua humana** (vía lexicón) se
compila a una **IR neutra** y de ahí a código (Python) o a otra lengua.

- `GET /estado` — estado del trabajador
- `GET /catalogo` — lenguas conocidas (metadatos + procedencia)
- `GET /lexicons` — lexicones y su estado
- `GET /propuestas` — propuestas del pipeline de metadatos (datos/propuestas/)
- `POST /compilar` — `{fuente, lexicon}` → IR, Python y salida
- `POST /traducir` — `{fuente, origen, destino}` → superficie + salida

Flujo de trabajo:
1. `trabajador.py` — refresca el catálogo desde Wikidata (CC0).
2. `proponer.py` — enriquece con **ISO 639-3 (SIL), Glottolog (CLDF) y CLDR** y
   genera las propuestas (`datos/propuestas/*.json`) marcadas `propuesto`.
3. `agente_nocturno.py` — rellena palabras sugeridas (IA, nunca `validado`).
4. `revisar.py` — puerta humana: `propuesto` → `validado` (exige referencias).

Regla: los metadatos vienen de fuentes citables (Wikidata, ISO 639-3 SIL,
Glottolog, CLDR); las palabras clave se **proponen** desde literatura y solo
un humano las marca `validado`. El sistema nunca inventa términos.
