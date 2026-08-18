from rdflib import Graph, term

from pyoxigraph import Store, NamedNode, Literal, Quad
from pathlib import Path
from .namespaces import NS, PREFIXES

# from typing import List

ns = NS(PREFIXES)


def parse_dc(file: Path, id_node: NamedNode, store: Store):
    """
    takes the full path to the file
    """
    graph = Graph()
    graph.parse(file, format="xml")

    for _, pred, obj in graph.triples((None, None, None)):
        predicate = NamedNode(str(pred))
        # Removing the rdf type from the dc.xml crawl
        # because it will take this element: <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        # and turn it into an rdf type for the file.
        if predicate == ns.rdf.type:
            continue
        match obj:
            case term.URIRef():
                obj_node = NamedNode(str(obj))
            case term.Literal():
                obj_node = Literal(str(obj))
            case term.BNode():
                continue
            case _:
                # This maybe should be recursive
                obj_node = Literal(str(obj))
        if predicate == ns.dc.identifier:
            store.add(Quad(id_node, ns.continuum.originalIdentifier, obj_node))

        store.add(Quad(id_node, predicate, obj_node))
