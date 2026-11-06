# -*- coding: utf-8 -*-
"""
EXPO MINAS - Grupo 1 - Grafo COMBINADO de Jujuy
================================================
Une en un solo grafo:
  (1) el DETALLE COMPLETO (todas las calles) de Gran Jujuy, y
  (2) las RUTAS PRINCIPALES de toda la provincia,
ambos de OpenStreetMap (formato JSON de Overpass).

Así en la app se puede clickear en CUALQUIER calle de la ciudad y, a la vez,
rutear entre pueblos de la provincia (Humahuaca, La Quiaca, etc.).

Los dos archivos comparten los IDs de nodo de OSM, por lo que las calles de la
ciudad se conectan naturalmente con las rutas provinciales en los cruces reales.

Uso:
    python construir_datos_combinado.py granjujuy.json provincia.json
"""
import json, math, os, sys
from collections import defaultdict, deque

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA_JS = os.path.join(AQUI, "..", "app", "datos_jujuy.js")
SALIDA_JSON = os.path.join(AQUI, "..", "app", "datos_jujuy.json")


def haversine(a, b):
    R = 6371000.0
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def parsear(path, coords, vias):
    data = json.load(open(path, encoding="utf-8"))
    for el in data["elements"]:
        if el["type"] == "node":
            coords[el["id"]] = (el["lat"], el["lon"])
        elif el["type"] == "way" and len(el.get("nodes", [])) >= 2:
            vias.append(el["nodes"])


def construir_grafo(coords, vias):
    occ = defaultdict(int)
    endpoints = set()
    for nodos in vias:
        endpoints.add(nodos[0]); endpoints.add(nodos[-1])
        for n in nodos:
            occ[n] += 1
    for n, c in occ.items():
        if c >= 2:
            endpoints.add(n)

    aristas = {}
    for nodos in vias:
        anterior = nodos[0]; acum = 0.0
        for i in range(1, len(nodos)):
            a, b = nodos[i - 1], nodos[i]
            if a in coords and b in coords:
                acum += haversine(coords[a], coords[b])
            if nodos[i] in endpoints:
                u, v = anterior, nodos[i]
                if u != v and u in coords and v in coords:
                    key = (min(u, v), max(u, v))
                    if key not in aristas or acum < aristas[key]:
                        aristas[key] = acum
                anterior = nodos[i]; acum = 0.0

    ady = defaultdict(set)
    for (u, v) in aristas:
        ady[u].add(v); ady[v].add(u)

    visto, mejor = set(), []
    for inicio in ady:
        if inicio in visto:
            continue
        comp, cola = [], deque([inicio]); visto.add(inicio)
        while cola:
            x = cola.popleft(); comp.append(x)
            for y in ady[x]:
                if y not in visto:
                    visto.add(y); cola.append(y)
        if len(comp) > len(mejor):
            mejor = comp
    comp_set = set(mejor)

    idx = {osmid: i for i, osmid in enumerate(sorted(comp_set))}
    nodos_out = [None] * len(idx)
    for osmid, i in idx.items():
        la, lo = coords[osmid]
        nodos_out[i] = [round(la, 6), round(lo, 6)]
    aristas_out = [[idx[u], idx[v], round(m, 1)]
                   for (u, v), m in aristas.items() if u in comp_set and v in comp_set]
    return nodos_out, aristas_out


def main():
    archivos = sys.argv[1:]
    if not archivos:
        print("Uso: python construir_datos_combinado.py archivo1.json [archivo2.json ...]")
        return
    coords, vias = {}, []
    for p in archivos:
        parsear(p, coords, vias)
        print(f"  leído {os.path.basename(p)}")
    print(f"  Nodos OSM crudos: {len(coords)} | Vías: {len(vias)}")

    nodos, aristas = construir_grafo(coords, vias)
    km = sum(a[2] for a in aristas) / 1000.0
    print("\nGRAFO COMBINADO (componente conexa principal)")
    print(f"  |V| nodos : {len(nodos)}")
    print(f"  |E| aristas: {len(aristas)}")
    print(f"  Longitud  : {km:.0f} km")
    print(f"  Grado medio: {2*len(aristas)/len(nodos):.3f}")

    datos = {"nodos": nodos, "aristas": aristas,
             "meta": {"ciudad": "Jujuy", "V": len(nodos), "E": len(aristas), "km": round(km)}}
    json.dump(datos, open(SALIDA_JSON, "w", encoding="utf-8"), separators=(",", ":"))
    with open(SALIDA_JS, "w", encoding="utf-8") as f:
        f.write("// Grafo de Jujuy: detalle de Gran Jujuy + rutas de la provincia (OpenStreetMap)\n")
        f.write("window.DATOS_JUJUY = ")
        json.dump(datos, f, separators=(",", ":"))
        f.write(";\n")
    print(f"\n  Exportado: {os.path.normpath(SALIDA_JS)}")
    print(f"  Tamaño JS: {os.path.getsize(SALIDA_JS)/1e6:.2f} MB")


if __name__ == "__main__":
    main()
