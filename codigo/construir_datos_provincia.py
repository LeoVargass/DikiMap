# -*- coding: utf-8 -*-
"""
EXPO MINAS - Grupo 1 - Grafo de TODA la provincia de Jujuy
==========================================================
Lee la red vial principal de la provincia de Jujuy (descargada de OpenStreetMap
vía Overpass: motorway/trunk/primary/secondary/tertiary/unclassified), arma el
grafo de intersecciones y exporta 'app/datos_jujuy.js' para la app.

Uso:
    python construir_datos_provincia.py archivo_overpass.json
    python construir_datos_provincia.py            # descarga de Overpass

El JSON de Overpass trae elementos {type:node,id,lat,lon} y {type:way,id,nodes:[...]}.
"""
import json, math, os, sys, time, urllib.request
from collections import defaultdict, deque

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA_JS = os.path.join(AQUI, "..", "app", "datos_jujuy.js")
SALIDA_JSON = os.path.join(AQUI, "..", "app", "datos_jujuy.json")

OVERPASS = 'https://overpass-api.de/api/interpreter'
QUERY = '''[out:json][timeout:240];
area["name"="Jujuy"]["admin_level"="4"]->.a;
(way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified)$"](area.a););
(._;>;);
out skel qt;'''


def haversine(a, b):
    R = 6371000.0
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def obtener():
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        print("Leyendo:", sys.argv[1])
        return json.load(open(sys.argv[1], encoding="utf-8"))
    print("Descargando provincia de Jujuy desde Overpass...")
    req = urllib.request.Request(OVERPASS, data=("data=" + QUERY).encode(),
                                 headers={"User-Agent": "expo-minas-edu/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=260).read())


def parsear(data):
    coords, vias = {}, []
    for el in data["elements"]:
        if el["type"] == "node":
            coords[el["id"]] = (el["lat"], el["lon"])
        elif el["type"] == "way" and len(el.get("nodes", [])) >= 2:
            vias.append(el["nodes"])
    return coords, vias


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
    data = obtener()
    coords, vias = parsear(data)
    print(f"  Nodos OSM crudos: {len(coords)} | Vías: {len(vias)}")
    nodos, aristas = construir_grafo(coords, vias)
    km = sum(a[2] for a in aristas) / 1000.0
    print("\nGRAFO PROVINCIA DE JUJUY (componente conexa principal)")
    print(f"  |V| nodos (esquinas/cruces): {len(nodos)}")
    print(f"  |E| aristas (tramos)       : {len(aristas)}")
    print(f"  Longitud total             : {km:.0f} km")
    print(f"  Grado medio 2|E|/|V|       : {2*len(aristas)/len(nodos):.3f}")

    datos = {"nodos": nodos, "aristas": aristas,
             "meta": {"ciudad": "Provincia de Jujuy",
                      "V": len(nodos), "E": len(aristas), "km": round(km)}}
    json.dump(datos, open(SALIDA_JSON, "w", encoding="utf-8"), separators=(",", ":"))
    with open(SALIDA_JS, "w", encoding="utf-8") as f:
        f.write("// Red vial principal de la PROVINCIA DE JUJUY (OpenStreetMap / Overpass)\n")
        f.write("// nodos:[lat,lon]  aristas:[i,j,metros]\n")
        f.write("window.DATOS_JUJUY = ")
        json.dump(datos, f, separators=(",", ":"))
        f.write(";\n")
    print(f"\n  Exportado: {os.path.normpath(SALIDA_JS)}")
    print(f"  Tamaño JS: {os.path.getsize(SALIDA_JS)/1e6:.2f} MB")


if __name__ == "__main__":
    main()
