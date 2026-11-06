# -*- coding: utf-8 -*-
"""
EXPO MINAS - Grupo 1 - Construccion del grafo de calles de San Salvador de Jujuy
================================================================================
Baja los datos reales de OpenStreetMap (API oficial), arma el grafo donde
    - cada ESQUINA / interseccion -> nodo
    - cada TRAMO de calle entre dos esquinas -> arista (peso = metros reales)
y exporta 'app/datos_jujuy.js' que usa la aplicacion web del mapa.

Solo usa la libreria estandar de Python (no requiere osmnx ni internet rapido).

Uso:
    python construir_datos_osm.py                 # baja de internet
    python construir_datos_osm.py archivo.osm     # usa un .osm ya descargado
"""

import json
import math
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict, deque

# Recuadro (bbox) del centro de San Salvador de Jujuy: left,bottom,right,top
BBOX = "-65.3135,-24.1990,-65.2855,-24.1730"
API = "https://api.openstreetmap.org/api/0.6/map?bbox=" + BBOX

# Tipos de via que son "calles" transitables (se excluyen veredas, escaleras...)
VIAS_VALIDAS = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "unclassified", "residential", "living_street", "service",
    "motorway_link", "trunk_link", "primary_link", "secondary_link",
    "tertiary_link", "road",
}

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA_JS = os.path.join(AQUI, "..", "app", "datos_jujuy.js")
SALIDA_JSON = os.path.join(AQUI, "..", "app", "datos_jujuy.json")


def haversine(a, b):
    """Distancia en metros entre dos (lat, lon)."""
    R = 6371000.0
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def obtener_osm():
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        print("Leyendo archivo local:", sys.argv[1])
        with open(sys.argv[1], "rb") as f:
            return f.read()
    print("Descargando de OpenStreetMap...")
    req = urllib.request.Request(API, headers={"User-Agent": "expo-minas-grafos-edu/1.0"})
    data = urllib.request.urlopen(req, timeout=120).read()
    print(f"  {len(data)/1e6:.1f} MB descargados")
    return data


def parsear(osm_bytes):
    """Devuelve (coords: id->(lat,lon), vias: lista de listas de ids)."""
    coords = {}
    vias = []
    root = ET.fromstring(osm_bytes)
    for el in root:
        if el.tag == "node":
            coords[int(el.get("id"))] = (float(el.get("lat")), float(el.get("lon")))
        elif el.tag == "way":
            tipo = None
            nodos = []
            for h in el:
                if h.tag == "tag" and h.get("k") == "highway":
                    tipo = h.get("v")
                elif h.tag == "nd":
                    nodos.append(int(h.get("ref")))
            if tipo in VIAS_VALIDAS and len(nodos) >= 2:
                vias.append(nodos)
    return coords, vias


def construir_grafo(coords, vias):
    """Simplifica a intersecciones: nodos = esquinas, aristas = tramos."""
    # 1) contar ocurrencias para detectar intersecciones
    occ = defaultdict(int)
    endpoints = set()
    for nodos in vias:
        endpoints.add(nodos[0])
        endpoints.add(nodos[-1])
        for n in nodos:
            occ[n] += 1
    for n, c in occ.items():
        if c >= 2:               # nodo compartido por >=2 tramos -> esquina
            endpoints.add(n)

    # 2) recorrer cada via partiendo en las esquinas -> aristas con longitud real
    aristas = {}  # (u,v) -> metros (minimo si hay paralelas)
    for nodos in vias:
        anterior = nodos[0]
        acum = 0.0
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
                anterior = nodos[i]
                acum = 0.0

    # 3) adyacencia
    ady = defaultdict(set)
    for (u, v) in aristas:
        ady[u].add(v)
        ady[v].add(u)

    # 4) componente conexa mas grande (quedarnos con la red principal)
    visto = set()
    mejor = []
    for inicio in ady:
        if inicio in visto:
            continue
        comp, cola = [], deque([inicio])
        visto.add(inicio)
        while cola:
            x = cola.popleft()
            comp.append(x)
            for y in ady[x]:
                if y not in visto:
                    visto.add(y)
                    cola.append(y)
        if len(comp) > len(mejor):
            mejor = comp
    comp_set = set(mejor)

    # 5) reindexar y exportar estructuras compactas
    idx = {osmid: i for i, osmid in enumerate(sorted(comp_set))}
    nodos_out = [None] * len(idx)
    for osmid, i in idx.items():
        lat, lon = coords[osmid]
        nodos_out[i] = [round(lat, 6), round(lon, 6)]
    aristas_out = []
    for (u, v), metros in aristas.items():
        if u in comp_set and v in comp_set:
            aristas_out.append([idx[u], idx[v], round(metros, 1)])
    return nodos_out, aristas_out


def main():
    osm = obtener_osm()
    coords, vias = parsear(osm)
    print(f"  Nodos OSM crudos: {len(coords)} | Vias (calles): {len(vias)}")

    nodos, aristas = construir_grafo(coords, vias)
    total_km = sum(a[2] for a in aristas) / 1000.0
    grado_medio = 2 * len(aristas) / len(nodos)

    print("\nGRAFO FINAL (componente conexa principal)")
    print(f"  |V| nodos (esquinas) : {len(nodos)}")
    print(f"  |E| aristas (tramos) : {len(aristas)}")
    print(f"  Longitud total       : {total_km:.1f} km")
    print(f"  Grado medio 2|E|/|V| : {grado_medio:.3f}")

    os.makedirs(os.path.join(AQUI, "..", "app"), exist_ok=True)
    datos = {"nodos": nodos, "aristas": aristas,
             "meta": {"ciudad": "San Salvador de Jujuy",
                      "V": len(nodos), "E": len(aristas),
                      "km": round(total_km, 1)}}
    with open(SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(datos, f, separators=(",", ":"))
    with open(SALIDA_JS, "w", encoding="utf-8") as f:
        f.write("// Grafo real de San Salvador de Jujuy (OpenStreetMap)\n")
        f.write("// nodos:[lat,lon]  aristas:[i,j,metros]\n")
        f.write("window.DATOS_JUJUY = ")
        json.dump(datos, f, separators=(",", ":"))
        f.write(";\n")
    print(f"\n  Exportado: {os.path.normpath(SALIDA_JS)}")
    print(f"  Exportado: {os.path.normpath(SALIDA_JSON)}")


if __name__ == "__main__":
    main()
