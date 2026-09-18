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
- `POST /compilar` — `{fuente, lexicon}` → IR, Python y salida
- `POST /traducir` — `{fuente, origen, destino}` → superficie + salida

Regla: los metadatos vienen de fuentes citables (Wikidata, CC0); las
palabras clave se **proponen** desde literatura y solo un humano las marca
`validado`. El sistema nunca inventa términos.
