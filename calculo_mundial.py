#!/usr/bin/env python3
"""
Calculo de esfuerzo/tiempo para lexicones de todo el mundo.

Modelo: el CODIGO se escribe UNA vez. El costo escala con el numero de
lenguas x el trabajo humano de proponer y VALIDAR el lexicon de palabras
clave. El cuello de botella no es la maquina, son las personas (hablantes
y linguistas) y su disponibilidad.

Universo (fuentes 2025-2026):
  - Ethnologue 29a ed. (2026): 7.170 lenguas vivas; 27a ed. 7.168.
  - ISO 639-3: ~7.900+ codigos (incluye extintas/no vivas).
  - Glottolog: ~8.600 languoides (variedades, incluye extintas).
  - Endangered (Ethnologue): ~3.078-3.226.
  - Lenguas de senas: ~160 (Ethnologue) a ~300 (estimaciones).
  - Historico/extintas atestiguadas: miles (varios miles documentadas).
"""

# ---- universo de lenguas (escenarios) ----
UNIVERSO = [
    ("Vivas (Ethnologue 2026)", 7170),
    ("ISO 639-3 (codigos)", 7900),
    ("Glottolog (languoides)", 8600),
    ("Vivas + senas (~300)", 7170 + 300),
    ("Vivas + extintas atestiguadas (~10.000)", 7170 + 10000),
]

# ---- esfuerzo humano por lengua (horas) ----
ESFUERZO = {
    "MVP (20-25 palabras clave)": 40,          # investigar+proponer+validar+QA
    "Intermedio (~80 palabras)": 160,
    "Completo (~250 conceptos + biblioteca)": 600,
}

HORAS_ANIO_PERSONA = 2000.0
EQUIPOS = [1, 10, 100, 500, 1000, 5000]


def anios(n_lenguas, horas_lengua, equipos):
    total_horas = n_lenguas * horas_lengua
    return total_horas / (equipos * HORAS_ANIO_PERSONA)


print("=" * 78)
print("CALCULO DE ESFUERZO - LEXICONES PARA TODO EL MUNDO")
print("=" * 78)
print(f"Base: {HORAS_ANIO_PERSONA:.0f} h por persona/anio.\n")

for etiqueta, n in UNIVERSO:
    print(f"### Universo: {etiqueta}  ->  {n:,} lenguas".replace(",", "."))
    for nivel, horas in ESFUERZO.items():
        secuencial = anios(n, horas, 1)
        fila = f"  {nivel:<40} 1 equipo: {secuencial:8.1f} anios"
        print(fila)
        for eq in EQUIPOS[1:]:
            a = anios(n, horas, eq)
            print(f"  {'':<40} {eq:>5} equipos: {a:8.2f} anios")
    print()

print("=" * 78)
print("RESUMEN PRACTICO (lenguas VIVAS = 7.170, MVP = 40 h/lengua)")
print("=" * 78)
for eq in EQUIPOS:
    a = anios(7170, 40, eq)
    if a >= 1:
        print(f"  {eq:>5} equipos en paralelo -> {a:7.2f} anios")
    else:
        print(f"  {eq:>5} equipos en paralelo -> {a*12:7.1f} meses")

print()
total_horas = 7170 * 40
print(f"Horas-persona totales (MVP, lenguas vivas): {total_horas:,} h".replace(",", "."))
print(f"= {total_horas/HORAS_ANIO_PERSONA:,.0f} personas-anio".replace(",", "."))
print()
print("Cuellos de botella reales (no de computo):")
print("  - ~45% de lenguas estan en peligro y muchas tienen <1.000 hablantes:")
print("    la validacion exige trabajo de campo con hablantes, no scraping.")
print("  - Lenguas orales sin literatura: no hay 'acuerdo' previo que interpretar.")
print("  - Financiacion, coordinacion y licencias de las fuentes.")

# ================= COLOMBIA =================
# ~65 lenguas indigenas + 2 criollas (palenquero, raizal) + romani + LSC.
COLOMBIA_VIVAS = 65 + 2 + 1 + 1          # 69
COLOMBIA_EXINTAS = 10                     # muisca, tairona, quimbaya, etc. (atestiguadas)
COLOMBIA_EQUIPOS = [1, 5, 10, 20]

print()
print("=" * 78)
print("COLOMBIA")
print("=" * 78)
print(f"Universo: ~65 indigenas + 2 criollas + romani + LSC = {COLOMBIA_VIVAS} lenguas vivas")
print(f"(+ ~{COLOMBIA_EXINTAS} extintas atestiguadas si se quieren reconstruir)\n")

for nivel, horas in ESFUERZO.items():
    n = COLOMBIA_VIVAS
    total_h = n * horas
    print(f"{nivel}  ({horas} h/lengua, {total_h:,.0f} h-persona)".replace(",", "."))
    for eq in COLOMBIA_EQUIPOS:
        a = anios(n, horas, eq)
        txt = f"{a:6.2f} anios ({a*12:5.1f} meses)" if a >= 0.25 else f"{a*52:5.1f} semanas"
        print(f"   {eq:>2} equipo(s): {txt}")
    print()

print("Notas propias de Colombia:")
print("  - ~50% de las lenguas indigenas estan en peligro; varias con <500 hablantes")
print("    (la validacion exige trabajo de campo con cada comunidad).")
print("  - Ley 1381 de 2010: concertacion previa con los pueblos -> no es opcional.")
print("  - Lenguas sin tradicion escrita (wayuunaiki ya tiene grafia; otras no).")
print("  - Muisca/tairona estan extintos: solo reconstruccion con fuentes (Lugo 1619, etc.).")
