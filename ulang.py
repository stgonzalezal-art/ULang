#!/usr/bin/env python3
"""
ULang - prototipo de capa de integracion multilingue.

Principio: NO reemplaza lenguajes; integra.
  superficie (lengua humana, via lexicon)
      -> IR neutra (AST)
          -> target (Python) y/o traduccion a otra superficie

Cambiar de lengua = cambiar de lexicon. La IR es la misma.
"""
import sys
import os
import re
import json
import argparse

BASE = os.path.dirname(os.path.abspath(__file__))
LEXICONS = os.path.join(BASE, "lexicons")

CANONICOS = (
    "FUNC", "RETURN", "IF", "ELSE", "WHILE",
    "TRUE", "FALSE", "AND", "OR", "NOT", "PRINT", "END",
)


class ErrorULang(Exception):
    pass


def cargar_lexicon(ruta):
    with open(ruta, encoding="utf-8") as f:
        data = json.load(f)
    superficie = {p: c.upper() for p, c in data.get("palabras", {}).items()}
    return data, superficie


def buscar_lexicon(codigo):
    if os.path.isfile(codigo):
        return codigo
    ruta = os.path.join(LEXICONS, codigo + ".json")
    if not os.path.isfile(ruta):
        raise ErrorULang(f"No existe el lexicon '{codigo}'")
    return ruta


TOKEN_RE = re.compile(
    r"""
      (?P<WS>\s+)
    | (?P<COMENTARIO>\#[^\n]*)
    | (?P<STRING>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')
    | (?P<NUMBER>\d+(?:\.\d+)?)
    | (?P<IDENT>[^\W\d]\w*)
    | (?P<OP>==|!=|<=|>=|[-+*/%<>=(),:])
    """,
    re.UNICODE | re.X,
)


def tokenizar(src, superficie, etiqueta):
    tokens = []
    pos = 0
    linea = 1
    n = len(src)
    while pos < n:
        m = TOKEN_RE.match(src, pos)
        if not m:
            raise ErrorULang(
                f"Caracter invalido {src[pos]!r} en {etiqueta}:{linea}"
            )
        tipo = m.lastgroup
        valor = m.group()
        if "\n" in valor:
            linea += valor.count("\n")
        pos = m.end()
        if tipo in ("WS", "COMENTARIO"):
            continue
        if tipo == "IDENT" and valor in superficie:
            tokens.append((superficie[valor], valor))
        else:
            tokens.append((tipo, valor))
    tokens.append(("EOF", None))
    return tokens


class Parser:
    def __init__(self, tokens, etiqueta):
        self.t = tokens
        self.i = 0
        self.etiqueta = etiqueta

    def actual(self):
        return self.t[self.i]

    def ver(self, tipo, valor=None):
        tk = self.t[self.i]
        if valor is None:
            return tk[0] == tipo
        return tk == (tipo, valor)

    def comer(self, tipo=None, valor=None):
        tk = self.t[self.i]
        if tipo is not None and tk[0] != tipo:
            raise ErrorULang(
                f"[{self.etiqueta}] se esperaba {tipo!r} y se hallo {tk[0]!r} ({tk[1]!r})"
            )
        if valor is not None and tk[1] != valor:
            raise ErrorULang(
                f"[{self.etiqueta}] se esperaba {valor!r} y se hallo {tk[1]!r}"
            )
        self.i += 1
        return tk

    def parsear(self):
        cuerpo = self.bloque(parar_en=("EOF",))
        self.comer("EOF")
        return {"tipo": "modulo", "cuerpo": cuerpo}

    def bloque(self, parar_en):
        cuerpo = []
        while self.actual()[0] not in parar_en:
            cuerpo.append(self.sentencia())
        return cuerpo

    def sentencia(self):
        tipo = self.actual()[0]
        if tipo == "FUNC":
            return self.funcion()
        if tipo == "IF":
            return self.si()
        if tipo == "WHILE":
            return self.mientras()
        if tipo == "RETURN":
            self.comer("RETURN")
            return {"tipo": "retorno", "valor": self.expr()}
        if tipo == "IDENT" and self.t[self.i + 1] == ("OP", "="):
            nombre = self.comer("IDENT")[1]
            self.comer("OP", "=")
            return {"tipo": "asignar", "nombre": nombre, "valor": self.expr()}
        return {"tipo": "exprstmt", "valor": self.expr()}

    def funcion(self):
        self.comer("FUNC")
        nombre = self.comer("IDENT")[1]
        self.comer("OP", "(")
        params = []
        if not self.ver("OP", ")"):
            params.append(self.comer("IDENT")[1])
            while self.ver("OP", ","):
                self.comer("OP", ",")
                params.append(self.comer("IDENT")[1])
        self.comer("OP", ")")
        self.comer("OP", ":")
        cuerpo = self.bloque(parar_en=("END", "EOF"))
        self.comer("END")
        return {"tipo": "funcion", "nombre": nombre, "params": params, "cuerpo": cuerpo}

    def si(self):
        self.comer("IF")
        cond = self.expr()
        self.comer("OP", ":")
        entonces = self.bloque(parar_en=("ELSE", "END", "EOF"))
        sino = []
        if self.ver("ELSE"):
            self.comer("ELSE")
            self.comer("OP", ":")
            sino = self.bloque(parar_en=("END", "EOF"))
        self.comer("END")
        return {"tipo": "si", "cond": cond, "entonces": entonces, "sino": sino}

    def mientras(self):
        self.comer("WHILE")
        cond = self.expr()
        self.comer("OP", ":")
        cuerpo = self.bloque(parar_en=("END", "EOF"))
        self.comer("END")
        return {"tipo": "mientras", "cond": cond, "cuerpo": cuerpo}

    def expr(self):
        return self.o()

    def o(self):
        izq = self.y()
        while self.ver("OR"):
            self.comer("OR")
            izq = {"tipo": "op", "op": "o", "izq": izq, "der": self.y()}
        return izq

    def y(self):
        izq = self.no()
        while self.ver("AND"):
            self.comer("AND")
            izq = {"tipo": "op", "op": "y", "izq": izq, "der": self.no()}
        return izq

    def no(self):
        if self.ver("NOT"):
            self.comer("NOT")
            return {"tipo": "op", "op": "no", "izq": self.no(), "der": None}
        return self.comparacion()

    def comparacion(self):
        izq = self.suma()
        while self.actual()[0] == "OP" and self.actual()[1] in ("==", "!=", "<", ">", "<=", ">="):
            op = self.comer("OP")[1]
            izq = {"tipo": "op", "op": op, "izq": izq, "der": self.suma()}
        return izq

    def suma(self):
        izq = self.mult()
        while self.actual()[0] == "OP" and self.actual()[1] in ("+", "-"):
            op = self.comer("OP")[1]
            izq = {"tipo": "op", "op": op, "izq": izq, "der": self.mult()}
        return izq

    def mult(self):
        izq = self.unario()
        while self.actual()[0] == "OP" and self.actual()[1] in ("*", "/", "%"):
            op = self.comer("OP")[1]
            izq = {"tipo": "op", "op": op, "izq": izq, "der": self.unario()}
        return izq

    def unario(self):
        if self.actual() == ("OP", "-"):
            self.comer("OP", "-")
            return {"tipo": "op", "op": "-u", "izq": self.unario(), "der": None}
        return self.primario()

    def primario(self):
        tk = self.actual()
        if tk[0] == "NUMBER":
            self.comer("NUMBER")
            return {"tipo": "num", "valor": float(tk[1]) if "." in tk[1] else int(tk[1])}
        if tk[0] == "STRING":
            self.comer("STRING")
            return {"tipo": "texto", "valor": tk[1][1:-1]}
        if tk[0] == "TRUE":
            self.comer("TRUE")
            return {"tipo": "bool", "valor": True}
        if tk[0] == "FALSE":
            self.comer("FALSE")
            return {"tipo": "bool", "valor": False}
        if tk[0] == "PRINT":
            self.comer("PRINT")
            return self.llamada("print")
        if tk[0] == "IDENT":
            nombre = self.comer("IDENT")[1]
            if self.ver("OP", "("):
                return self.llamada(nombre)
            return {"tipo": "var", "nombre": nombre}
        if self.ver("OP", "("):
            self.comer("OP", "(")
            e = self.expr()
            self.comer("OP", ")")
            return e
        raise ErrorULang(f"[{self.etiqueta}] expresion inesperada {tk!r}")

    def llamada(self, nombre):
        self.comer("OP", "(")
        args = []
        if not self.ver("OP", ")"):
            args.append(self.expr())
            while self.ver("OP", ","):
                self.comer("OP", ",")
                args.append(self.expr())
        self.comer("OP", ")")
        return {"tipo": "llamada", "nombre": nombre, "args": args}


# ---------------- codegen Python ----------------
BIN = {"o": "or", "y": "and", "==": "==", "!=": "!=", "<": "<",
       ">": ">", "<=": "<=", ">=": ">=", "+": "+", "-": "-",
       "*": "*", "/": "/", "%": "%"}


def gen_expr(n):
    t = n["tipo"]
    if t == "num":
        return repr(n["valor"])
    if t == "texto":
        return repr(n["valor"])
    if t == "bool":
        return "True" if n["valor"] else "False"
    if t == "var":
        return n["nombre"]
    if t == "llamada":
        return n["nombre"] + "(" + ", ".join(gen_expr(a) for a in n["args"]) + ")"
    if t == "op":
        if n["op"] == "no":
            return "(not " + gen_expr(n["izq"]) + ")"
        if n["op"] == "-u":
            return "(-" + gen_expr(n["izq"]) + ")"
        return "(" + gen_expr(n["izq"]) + " " + BIN[n["op"]] + " " + gen_expr(n["der"]) + ")"
    raise ErrorULang(f"Nodo IR desconocido: {t}")


def gen_bloque(cuerpo, nivel):
    lineas = []
    pad = "    " * nivel
    for s in cuerpo:
        lineas.extend(gen_stmt(s, nivel))
    if not lineas:
        lineas.append(pad + "pass")
    return lineas


def gen_stmt(s, nivel):
    t = s["tipo"]
    pad = "    " * nivel
    if t == "funcion":
        cab = f"{pad}def {s['nombre']}({', '.join(s['params'])}):"
        return [cab] + gen_bloque(s["cuerpo"], nivel + 1)
    if t == "retorno":
        return [pad + "return " + gen_expr(s["valor"])]
    if t == "asignar":
        return [pad + s["nombre"] + " = " + gen_expr(s["valor"])]
    if t == "exprstmt":
        return [pad + gen_expr(s["valor"])]
    if t == "si":
        out = [pad + "if " + gen_expr(s["cond"]) + ":"]
        out += gen_bloque(s["entonces"], nivel + 1)
        if s["sino"]:
            out.append(pad + "else:")
            out += gen_bloque(s["sino"], nivel + 1)
        return out
    if t == "mientras":
        out = [pad + "while " + gen_expr(s["cond"]) + ":"]
        out += gen_bloque(s["cuerpo"], nivel + 1)
        return out
    raise ErrorULang(f"Sentencia IR desconocida: {t}")


def generar_python(ir):
    return "\n".join(gen_bloque(ir["cuerpo"], 0)) + "\n"


# ---------------- codegen inverso: IR -> otra superficie (lengua humana) ----------------
def _w(inv, canon, etiqueta):
    if canon not in inv:
        raise ErrorULang(
            f"[{etiqueta}] falta termino para {canon} en el lexicon destino"
        )
    return inv[canon]


def gen_expr_sup(n, inv, et):
    t = n["tipo"]
    if t == "num":
        return repr(n["valor"])
    if t == "texto":
        return '"' + n["valor"].replace('"', '\\"') + '"'
    if t == "bool":
        return _w(inv, "TRUE" if n["valor"] else "FALSE", et)
    if t == "var":
        return n["nombre"]
    if t == "llamada":
        nombre = _w(inv, "PRINT", et) if n["nombre"] == "print" else n["nombre"]
        return nombre + "(" + ", ".join(gen_expr_sup(a, inv, et) for a in n["args"]) + ")"
    if t == "op":
        if n["op"] == "no":
            return _w(inv, "NOT", et) + " " + gen_expr_sup(n["izq"], inv, et)
        if n["op"] == "-u":
            return "-" + gen_expr_sup(n["izq"], inv, et)
        op = {"o": _w(inv, "OR", et), "y": _w(inv, "AND", et)}.get(n["op"], n["op"])
        return (
            gen_expr_sup(n["izq"], inv, et) + " " + op + " "
            + gen_expr_sup(n["der"], inv, et)
        )
    raise ErrorULang(f"Nodo IR desconocido (superficie): {t}")


def gen_bloque_sup(cuerpo, nivel, inv, et):
    lineas = []
    for s in cuerpo:
        lineas.extend(gen_stmt_sup(s, nivel, inv, et))
    return lineas


def gen_stmt_sup(s, nivel, inv, et):
    t = s["tipo"]
    pad = "    " * nivel
    if t == "funcion":
        cab = f"{pad}{_w(inv, 'FUNC', et)} {s['nombre']}({', '.join(s['params'])}):"
        return [cab] + gen_bloque_sup(s["cuerpo"], nivel + 1, inv, et) + [pad + _w(inv, "END", et)]
    if t == "retorno":
        return [pad + _w(inv, "RETURN", et) + " " + gen_expr_sup(s["valor"], inv, et)]
    if t == "asignar":
        return [pad + s["nombre"] + " = " + gen_expr_sup(s["valor"], inv, et)]
    if t == "exprstmt":
        return [pad + gen_expr_sup(s["valor"], inv, et)]
    if t == "si":
        out = [pad + _w(inv, "IF", et) + " " + gen_expr_sup(s["cond"], inv, et) + ":"]
        out += gen_bloque_sup(s["entonces"], nivel + 1, inv, et)
        if s["sino"]:
            out.append(pad + _w(inv, "ELSE", et) + ":")
            out += gen_bloque_sup(s["sino"], nivel + 1, inv, et)
        out.append(pad + _w(inv, "END", et))
        return out
    if t == "mientras":
        out = [pad + _w(inv, "WHILE", et) + " " + gen_expr_sup(s["cond"], inv, et) + ":"]
        out += gen_bloque_sup(s["cuerpo"], nivel + 1, inv, et)
        out.append(pad + _w(inv, "END", et))
        return out
    raise ErrorULang(f"Sentencia IR desconocida (superficie): {t}")


def generar_superficie(ir, inv, et):
    return "\n".join(gen_bloque_sup(ir["cuerpo"], 0, inv, et)) + "\n"


def main():
    ap = argparse.ArgumentParser(description="ULang - integracion multilingue")
    ap.add_argument("archivo")
    ap.add_argument("-l", "--lexicon", default="es", help="codigo o ruta del lexicon")
    ap.add_argument("--ir", action="store_true", help="mostrar la IR (codigo intermedio)")
    ap.add_argument("--solo-generar", action="store_true", help="no ejecutar, solo mostrar Python")
    ap.add_argument("--traducir", metavar="LEX", help="traducir la IR a la superficie de otro lexicon y ejecutarla")
    args = ap.parse_args()

    data, superficie = cargar_lexicon(buscar_lexicon(args.lexicon))
    with open(args.archivo, encoding="utf-8") as f:
        src = f.read()

    etiqueta = os.path.basename(args.archivo)
    tokens = tokenizar(src, superficie, etiqueta)
    ir = Parser(tokens, etiqueta).parsear()

    if args.ir:
        print(json.dumps(ir, ensure_ascii=False, indent=2))
        return

    if args.traducir:
        data2, sup2 = cargar_lexicon(buscar_lexicon(args.traducir))
        inv2 = {c: p for p, c in data2.get("palabras", {}).items()}
        texto = generar_superficie(ir, inv2, data2.get("idioma", "?"))
        print(f"# traduccion a {data2.get('idioma')} ({data2.get('estado')})")
        print(texto, end="")
        ir2 = Parser(tokenizar(texto, sup2, "traducido"), "traducido").parsear()
        py2 = generar_python(ir2)
        print("# --- ejecucion de la traduccion (round-trip IR -> otra lengua -> IR -> Python) ---")
        exec(compile(py2, "<ulang-traducido>", "exec"), {})
        return

    py = generar_python(ir)
    if args.solo_generar:
        print(py)
        return

    print(f"# lengua: {data.get('idioma')} ({data.get('estado')})")
    print("# --- IR -> Python ---")
    print(py, end="")
    print("# --- salida ---")
    entorno = {}
    exec(compile(py, "<ulang>", "exec"), entorno)


if __name__ == "__main__":
    try:
        main()
    except ErrorULang as e:
        print(f"ErrorULang: {e}", file=sys.stderr)
        sys.exit(1)
