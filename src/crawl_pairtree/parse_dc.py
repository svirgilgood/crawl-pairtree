from rdflib import Graph, term

from pyoxigraph import Store, NamedNode, Literal, Quad
from pathlib import Path

from typing import List


def parse_dc(file: Path, id_node: NamedNode, quad_list: List[Quad]):
    """
    takes the full path to the file
    """
    graph = Graph()
    graph.parse(file, format="xml")

    for _, pred, obj in graph.triples((None, None, None)):
        predicate = NamedNode(str(pred))
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

        quad_list.append(Quad(id_node, predicate, obj_node))
