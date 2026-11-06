# -*- coding: utf-8 -*-
"""
EXPO MINAS - Grupo 1 - Eje: Teoria de Grafos
=============================================
RED REAL de calles de San Salvador de Jujuy desde OpenStreetMap.

Baja la traza urbana real con la libreria OSMnx (que consulta la API de
Overpass de OpenStreetMap) y arma el grafo:
    - cada ESQUINA  -> nodo   (vertice V)
    - cada TRAMO de calle -> arista (E), con peso = longitud real en metros
Luego calcula camino minimo con Dijkstra y con A* (heuristica Haversine),
compara cuantos nodos explora cada uno y guarda las figuras.

REQUISITOS:
    pip install osmnx networkx matplotlib scikit-learn
    (necesita conexion a internet para descargar el mapa)

Uso:
    python red_real_osm.py

Nota: el grafo que usa la app se arma con construir_datos_combinado.py
(solo libreria estandar). Este script es una variante con OSMnx.
"""

import heapq
import math
import os

import networkx as nx
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Centro aproximado de San Salvador de Jujuy
LUGAR = "San Salvador de Jujuy, Argentina"
PUNTO_CENTRO = (-24.1858, -65.2995)   # (lat, lon) centro de la ciudad aprox.
RADIO_M = 2000                         # radio de descarga en metros


def descargar_red():
    """Descarga la red vial 'drive' y devuelve un grafo no dirigido ponderado."""
    import osmnx as ox
    print(f"Descargando red vial de: {LUGAR} ...")
    # red manejable centrada en el microcentro:
    G = ox.graph_from_point(PUNTO_CENTRO, dist=RADIO_M, network_type="drive")
    G = ox.convert.to_undirected(G)
    print(f"  Nodos (esquinas): {G.number_of_nodes()}")
    print(f"  Aristas (tramos): {G.number_of_edges()}")
    largo_total = sum(d.get("length", 0) for _, _, d in G.edges(data=True))
    print(f"  Longitud total de calles: {largo_total/1000:.1f} km")
    return G


def haversine(G, a, b):
    """Distancia en linea recta (m) entre dos nodos -> heuristica admisible."""
    R = 6371000.0
    la1, lo1 = math.radians(G.nodes[a]["y"]), math.radians(G.nodes[a]["x"])
    la2, lo2 = math.radians(G.nodes[b]["y"]), math.radians(G.nodes[b]["x"])
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def _peso(G, u, v):
    data = G.get_edge_data(u, v)
    return min(d.get("length", 1.0) for d in data.values())


def dijkstra(G, origen, destino):
    dist = {origen: 0.0}
    prev = {}
    pq = [(0.0, origen)]
    visto, explorados = set(), 0
    while pq:
        d, u = heapq.heappop(pq)
        if u in visto:
            continue
        visto.add(u)
        explorados += 1
        if u == destino:
            break
        for v in G.neighbors(u):
            nd = d + _peso(G, u, v)
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    return _camino(prev, origen, destino), dist.get(destino, math.inf), explorados


def a_estrella(G, origen, destino):
    g = {origen: 0.0}
    prev = {}
    pq = [(haversine(G, origen, destino), origen)]
    visto, explorados = set(), 0
    while pq:
        f, u = heapq.heappop(pq)
        if u in visto:
            continue
        visto.add(u)
        explorados += 1
        if u == destino:
            break
        for v in G.neighbors(u):
            ng = g[u] + _peso(G, u, v)
            if ng < g.get(v, math.inf):
                g[v] = ng
                prev[v] = u
                heapq.heappush(pq, (ng + haversine(G, v, destino), v))
    return _camino(prev, origen, destino), g.get(destino, math.inf), explorados


def _camino(prev, origen, destino):
    cam, u = [], destino
    while u != origen:
        cam.append(u)
        if u not in prev:
            return []
        u = prev[u]
    cam.append(origen)
    cam.reverse()
    return cam


def main():
    try:
        import osmnx  # noqa: F401
    except ImportError:
        print("Falta OSMnx.  Instalalo con:  pip install osmnx")
        print("Alternativa sin OSMnx: construir_datos_combinado.py")
        return

    import osmnx as ox
    G = descargar_red()

    # Grados
    grados = [d for _, d in G.degree()]
    print(f"\n  Grado medio = 2|E|/|V| = {2*G.number_of_edges()/G.number_of_nodes():.3f}")
    print(f"  Grado maximo = {max(grados)} | Grado minimo = {min(grados)}")
    print(f"  Lema del apreton de manos: suma de grados = {sum(grados)} = 2|E| = {2*G.number_of_edges()}")

    # Dos esquinas lejanas: la mas al sur-oeste y la mas al nor-este
    nodos = list(G.nodes(data=True))
    origen = min(nodos, key=lambda n: n[1]["y"] + n[1]["x"])[0]
    destino = max(nodos, key=lambda n: n[1]["y"] + n[1]["x"])[0]

    print("\n" + "=" * 60)
    print("CAMINO MINIMO sobre la RED REAL")
    print("=" * 60)
    cam_d, costo_d, exp_d = dijkstra(G, origen, destino)
    cam_a, costo_a, exp_a = a_estrella(G, origen, destino)

    print(f"\nDIJKSTRA : {costo_d:.0f} m | nodos explorados = {exp_d}")
    print(f"A*       : {costo_a:.0f} m | nodos explorados = {exp_a}")
    print(f"Mismo costo optimo: {'SI' if abs(costo_d-costo_a) < 1 else 'NO'}")
    if exp_d:
        print(f"A* exploro {exp_d - exp_a} nodos menos "
              f"({100*(exp_d-exp_a)/exp_d:.0f}% menos trabajo que Dijkstra).")

    # Figuras
    carpeta = os.path.join(os.path.dirname(__file__), "..", "figuras")
    fig, ax = ox.plot_graph(G, node_size=3, edge_linewidth=0.5, show=False,
                            close=False, bgcolor="white",
                            node_color="#1f77b4", edge_color="#bbb")
    fig.savefig(os.path.join(carpeta, "red_real_osm.png"), dpi=150,
                bbox_inches="tight")
    print("\n  Figura guardada: figuras/red_real_osm.png")

    fig, ax = ox.plot_graph_route(G, cam_d, route_color="#d62728",
                                  route_linewidth=4, node_size=0, show=False,
                                  close=False, bgcolor="white",
                                  edge_color="#ddd")
    fig.savefig(os.path.join(carpeta, "red_real_camino.png"), dpi=150,
                bbox_inches="tight")
    print("  Figura guardada: figuras/red_real_camino.png")
    print("\nListo.")


if __name__ == "__main__":
    main()
