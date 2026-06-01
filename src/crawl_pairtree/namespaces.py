from pyoxigraph import NamedNode

from typing import Optional, Dict


class Namespace(str):
    def __new__(cls, value: str):
        return str.__new__(cls, value)

    def term(self, local: str) -> NamedNode:
        return NamedNode(self + local)

    def __getattr__(self, local: str) -> NamedNode:
        if local.startswith("__"):
            raise AttributeError
        return self.term(local)


ark_ns = Namespace("http://ark.lib.uchicago.edu/ark:61001/")

continuum_ns = Namespace("http://continuum.lib.uchicago.edu/ontology/")
continuum_item = Namespace("http://continuum.lib.uchicago.edu/item/")
premis_ns = Namespace("http://www.loc.gov/premis/rdf/v3/")
ebucore = Namespace("http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#")

DC = Namespace("http://purl.org/dc/elements/1.1/")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
DCTERMS = Namespace("http://purl.org/dc/terms/")

PREFIXES = {
    "ark": "http://ark.lib.uchicago.edu/",
    "bf": "http://id.loc.gov/ontologies/bibframe/",
    "continuum": "http://continuum.lib.uchicago.edu/item/",
    "premis": "http://www.loc.gov/premis/rdf/v3/",
    "ebucore": "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "edm": "http://www.europeana.eu/schemas/edm/",
}


class NS:
    def __init__(self, prefixes: Dict[str, str]):
        self.dict = prefixes

    def get(self, namespace):
        return Namespace(self.dict[namespace])

    def __getattr__(self, namespace):
        return self.get(namespace)
