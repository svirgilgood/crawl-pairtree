"""
Create a script that crawls the pair tree and then creates the model
of data
"""

import argparse
import os
import json
import io

from pathlib import Path

from pyoxigraph import (
    Store,
    NamedNode,
    Quad,
    Literal,
    BlankNode,
    serialize,
    RdfFormat,
)
import pyoxigraph as po


from .namespaces import (
    ebucore,
    ark_ns,
    continuum_ns,
    continuum_item,
    Namespace,
    DC,
    premis_ns,
    RDF,
    XSD,
    DCTERMS,
)
from typing import Optional, List, Tuple, Dict


def find_mime_type(ext: str) -> Optional[str]:
    """ """
    match ext:
        case "json":
            return "application/json"
        case "mrc":
            return "application/octet-stream"
        case "xml":
            return "application/xml"
        case "txt":
            return "text"
        case "ttl":
            return "text/turtle"
        case "tif":
            return "image/tiff"
        case "wav":
            return "audio/vnd.wav"
        case "pdf":
            return "application/pdf"
        case _:
            return None


def match_file_type(file_type: Optional[str]):
    """ """
    match file_type:
        case "pf":
            return continuum_ns.Preservation
        case "vaf":
            return continuum_ns.Viewer
        case "manifest":
            return continuum_ns.Manifest
        case _:
            return continuum_ns.Supplemental


def get_types(file_parts: List[str], base_name: str) -> Optional[Tuple[str, str]]:
    match len(file_parts):
        case 3:
            _, file_type, ext = file_parts
            mime_type = find_mime_type(ext)
            type_node = match_file_type(file_type)

        case 2:
            _, ext = file_parts
            mime_type = find_mime_type(ext)
            file_type = "pf" if base_name in ("file.tif", "file.pdf") else None
            type_node = match_file_type(file_type)
        case _:
            print(f"Error with File {file_name}")
            return
    return (mime_type, type_node)


def update_id_manifest(
    store: Store, ark_node: NamedNode, head_manifest: Dict[str, str]
):
    """
    run an update query for the manifest
    """
    update_q = """PREFIX continuum: <http://continuum.lib.uchicago.edu/ontology/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX primis:  <http://www.loc.gov/premis/rdf/v3/>

    INSERT {
        <%s> continuum:hasHeadObject ?file .
    }
    WHERE {
        ?file primis:fixity/rdf:value ?hash
        VALUES ?hash {
    """ % (
        ark_node.value,
    )
    hash_value_clause = '"' + '"\n "'.join(head_manifest.keys()) + '"'
    query = update_q + hash_value_clause + "\n        }\n    }"
    # print(query)
    store.update(query)


def format_local(type_node: NamedNode) -> str:
    """
    create a path from a type_node
    """
    name = type_node.value
    slash_idx = name.rfind("/")
    hash_idx = name.rfind("#")
    idx = (slash_idx if slash_idx > hash_idx else hash_idx) + 1
    return name[idx:].lower()


def parse_inventory(inventory_file: Path, root: Path, store: Store):
    """
    Parse the inventory file to create the various items that will be stored in
    continuum
    """
    with open(root / inventory_file, "r") as jsonp:
        inventory = json.load(jsonp)

    ark_full = inventory["id"].replace("ark:61001/", "")
    ark_id = ark_full.replace("ark:61001/", "")
    ark_node = ark_ns.term(ark_full)
    digest_algo = inventory["digestAlgorithm"]
    head = inventory["head"]
    store.add(Quad(ark_node, continuum_ns.head, Literal(head)))
    versions = inventory["versions"]
    for version, v_obj in versions.items():
        created = v_obj["created"]

        store.add(
            Quad(ark_node, DCTERMS.modified, Literal(created, datatype=XSD.datetime))
        )

        for hash, file_names in v_obj["state"].items():
            for file_name in file_names:
                base_fname = os.path.basename(file_name)
                file_parts = file_name.split(".")
                mime_type, type_node = get_types(file_parts, base_fname)

                if not mime_type and not type_node:
                    continue

                slash_split = file_name.split("/")
                if len(slash_split) == 2:
                    """The file node is created"""
                    file_node = continuum_item.term(
                        f"{ark_id}/{format_local(type_node)}/{version}/{slash_split[1]}/{slash_split[0]}"
                    )
                else:
                    file_node = continuum_item.term(
                        f"{ark_id}/{format_local(type_node)}/{version}/{file_name}"
                    )

                if mime_type:
                    store.add(Quad(file_node, ebucore.hasMimeType, Literal(mime_type)))

                store.add(Quad(file_node, continuum_ns.fileType, type_node))
                store.add(Quad(file_node, premis_ns.originalName, Literal(file_name)))
                store.add(Quad(file_node, continuum_ns.partOfVersion, Literal(version)))
                store.add(
                    Quad(
                        file_node,
                        DCTERMS.created,
                        Literal(created, datatype=XSD.datetime),
                    )
                )

                file_path = root / version / "content" / file_name
                store.add(
                    Quad(file_node, continuum_ns.hasPath, Literal(str(file_path)))
                )
                premis_node = BlankNode()
                store.add(Quad(file_node, premis_ns.fixity, premis_node))
                store.add(Quad(file_node, DCTERMS.isPartOf, ark_node))
                store.add(
                    Quad(
                        premis_node,
                        RDF.type,
                        NamedNode(
                            "https://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions/sha512"
                        ),
                    )
                )
                store.add(Quad(premis_node, RDF.value, Literal(hash)))
    # Called  here to add the various manifest files to the specific ark node
    update_id_manifest(store, ark_node, inventory["manifest"])


def main():
    """
    How do parse the pair tree and add it to the data.
    """
    parser = argparse.ArgumentParser(
        "crawl-pairtree", description="crawl the ldr and create the data model to serve"
    )
    parser.add_argument(
        "basedirs",
        nargs="+",
        help="base directories to walk to find the files to parse",
    )

    args = parser.parse_args()

    store = Store()

    for basedir in args.basedirs:
        for root, _dir, files in os.walk(basedir):
            for f in files:
                if not f.startswith("0=ocfl_object_1"):
                    continue

                # print(root, f)
                parse_inventory("inventory.json", Path(root), store)

            # print(dir)
    prefixes = {
        "ark": "http://ark.lib.uchicago.edu/ark:61001/",
        "conti": "http://continuum.lib.uchicago.edu/item/",
        "continuum": "http://continuum.lib.uchicago.edu/ontology/",
        "premis": "http://www.loc.gov/premis/rdf/v3/",
        "ebucore": "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#",
        "dc": "http://purl.org/dc/elements/1.1/",
        "dcterms": "http://purl.org/dc/terms/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    }
    output = io.BytesIO()
    serialize(store, output=output, format=RdfFormat.TURTLE, prefixes=prefixes)
    with open("continuum.ttl", "w") as fp:
        fp.write(output.getvalue().decode("utf-8"))
