import json
from pyoxigraph import Quad, Literal, NamedNode, BlankNode, Store
from pathlib import Path

from .namespaces import NS, PREFIXES

ns = NS(PREFIXES)


def parse_manifest(manifest_file: Path, ark_node: NamedNode, store: Store):
    """ """
    with open(manifest_file, "r") as mfp:
        manifest = json.load(manifest_file)

    if rights := manifest.get("rights"):
        store.add(Quad(ark_node, ns.dc.rights, NamedNode(rights)))
    """
    rights = (
        NamedNode(manifest.get("rights"))
        if manifest.get("rights")
        else NamedNode("http://creativecommons.org/licenses/by-nc/4.0/")
    )
    if rights:
        store.add(ark_node, ns.dc.rights, NamedNode(rights))
    """
