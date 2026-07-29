"""
Create a script that crawls the pair tree and then creates the model
of data
"""

# This needs Logging

import argparse
import datetime
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

from multiprocessing import Process, Semaphore, Manager

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
    NS,
    PREFIXES,
)
from .parse_dc import parse_dc
from .parse_bag import parse_bag_info

# from .parse_manifest import parse_manifest
from typing import Optional, List, Tuple, Dict

ns = NS(PREFIXES)


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
            ext = file_parts[-1]
            if ext in ("pdf", "tif"):
                print(f"Error with File {' - '.join(file_parts)}")
                return
            mime_type = find_mime_type(ext)
            type_node = match_file_type("supplimental")
    return (mime_type, type_node)


def update_id_manifest(
    store: Store, ark_node: NamedNode, head_manifest: Dict[str, str]
):
    """
    run an update query for the manifest
    """
    update_q = """PREFIX continuum: <http://continuum.lib.uchicago.edu/ontology/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX premis:  <http://www.loc.gov/premis/rdf/v3/>

    INSERT {
        <%s> continuum:hasHeadObject ?file .
    }
    WHERE {
        ?file premis:fixity/rdf:value ?hash
        VALUES ?hash {
    """ % (
        ark_node.value,
    )
    # hash_value_clause = '"' + '"\n "'.join(head_manifest.keys()) + '"'
    hash_value_clause = "\n".join([Literal(h) for h in head_manifest.keys()])
    query = update_q + hash_value_clause + "\n        }\n    }"
    # print(query)
    store.update(query)


def create_head_object(inventory: Dict, store: Store, ark_node: NamedNode):
    """
    Iterate backwards through the versions, and add files to the head object that
    are not in the head already. This might be better as a query that could be reused.
    """
    file_set = set()
    for version in sorted(inventory["versions"].keys(), reverse=True):
        print(version)

    return


def format_local(type_node: NamedNode) -> str:
    """
    create a path from a type_node
    """
    name = type_node.value
    slash_idx = name.rfind("/")
    hash_idx = name.rfind("#")
    idx = (slash_idx if slash_idx > hash_idx else hash_idx) + 1
    return name[idx:].lower()


def construct_original_name(
    file_name: str, internal_id: Optional[str] = None, page: Optional[str] = None
):
    if not internal_id:
        return file_name
    _, ext = file_name.split(".", maxsplit=1)
    return f"{internal_id}.{ext}" if not page else f"{internal_id}_{page}.{ext}"


def parse_inventory(inventory_file: Path, root: Path, store: Store):
    """
    Parse the inventory file to create the various items that will be stored in
    continuum
    """
    with open(root / inventory_file, "r") as jsonp:
        inventory = json.load(jsonp)

    content_manifest = inventory["manifest"]
    ark_full = inventory["id"]  # .replace("ark:61001/", "")
    # ark_id = ark_full.replace("ark:61001/", "")
    ark_id = ark_full.replace("ark:61001/", "").replace("ark:/61001/", "")
    ark_node = ns.ark.term(ark_full)
    # print("ark node", ark_node)
    digest_algo = inventory["digestAlgorithm"]
    head = inventory["head"]
    store.add(Quad(ark_node, continuum_ns.head, Literal(head)))
    store.add(Quad(ark_node, ns.rdf.type, ns.edm.ProvidedCHO))
    store.add(Quad(ark_node, continuum_ns.hasArkID, Literal(ark_id)))
    versions = sorted(inventory["versions"].keys(), reverse=True)
    file_name_set = set()
    """
    try:
        _, _, internal_id = list(
            store.quads_for_pattern(
                ark_node,
                ns.continuum.orginalIdentifier,
                None,
            )
        ).pop()
    except IndexError:
        print("Error in finding internal id: ", ark_node)
        internal_id = None
    """
    for version in versions:
        v_obj = inventory["versions"][version]
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
                page_number = None
                if len(slash_split) == 2:
                    """The file node is created"""
                    page_number = slash_split[0]
                    file_node = continuum_item.term(
                        f"{ark_id}/{format_local(type_node)}/{version}/{slash_split[1]}/{page_number}"
                    )
                    store.add(
                        Quad(file_node, continuum_ns.partNumber, Literal(page_number))
                    )
                else:
                    file_node = continuum_item.term(
                        f"{ark_id}/{format_local(type_node)}/{version}/{file_name}"
                    )

                if file_name not in file_name_set:
                    file_name_set.add(file_name)
                    store.add(Quad(ark_node, continuum_ns.hasHeadObject, file_node))

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

                # I think a distinction between content paths and logical paths need to
                # be made. Thsi is currently just the content path
                try:
                    content_path = root / content_manifest[hash][0]
                except IndexError:
                    print(content_manifest)
                    print(
                        f"ark node: {ark_node}\n file node: {file_node}\n hash: {hash}"
                    )
                store.add(
                    Quad(file_node, continuum_ns.hasPath, Literal(str(content_path)))
                    # Quad(file_node, continuum_ns.hasPath, Literal(str(file_path)))
                )
                logical_path = root / version / "content" / file_name
                store.add(
                    Quad(
                        file_node,
                        continuum_ns.hasLogicalPath,
                        Literal(str(logical_path)),
                    )
                    # Quad(file_node, continuum_ns.hasPath, Literal(str(file_path)))
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
    # update_id_manifest(store, ark_node, inventory["manifest"])


def return_relative_id(root: str):
    """
    returns the id relative to a specific id
    """
    inventory = Path(root).parents[1] / "inventory.json"
    with open(inventory, "r") as jp:
        inv = json.load(jp)
    return inv.get("id")


def process_files(f: str, root: str, store: Store):
    if f == "file.dc.xml":
        id = return_relative_id(root)
        if id:
            parse_dc(Path(root) / f, ns.ark.term(id), store)
        else:
            print(f"Id Not found for {root}/{f}")
    elif f == "file.info.txt":
        id = return_relative_id(root)
        if id:
            parse_bag_info(Path(root) / f, ns.ark.term(id), store)
        else:
            print(f"Id Not found for {root}/{f}")
    # elif f == "file.manifest.json":
    #    id = return_relative_id(root)
    #    if id:
    #        parse_manifest(Path(root) / f, ns.ark.term(id), store)
    #    else:
    #        print(f"Id Not found for {root}/{f}")

    elif f.startswith("0=ocfl_object_1"):
        parse_inventory("inventory.json", Path(root), store)
    else:
        pass
    # print(root, f)


def main():
    """
    How do parse the pair tree and add it to the data.
    """
    parser = argparse.ArgumentParser(
        "crawl-pairtree", description="crawl the ldr and create the data model to serve"
    )
    parser.add_argument(
        "--db",
        nargs="?",
        help="provide a path where the database should be stored, if no argument passed, the database will be in memory",
    )
    parser.add_argument(
        "basedirs",
        nargs="+",
        help="base directories to walk to find the files to parse",
    )

    args = parser.parse_args()

    store = Store() if not args.db else Store(args.db)

    ocfl_counter = 0
    for basedir in args.basedirs:

        for root, _dir, files in os.walk(basedir):
            # I should set this up to ~paralize~async this
            for f in files:
                if f in (
                    "file.dc.xml",
                    "file.info.txt",
                    "file.manifest.json",
                    "0=ocfl_object_1.0",
                    "0=ocfl_object_1.1",
                ):
                    process_files(f, root, store)
                    if f.startswith("0=ocfl_object_1"):
                        ocfl_counter += 1
                    if (ocfl_counter % 1000) == 0:
                        store.flush()
                        print(f"iteration: {ocfl_counter}")

    print(f"Total Number: {ocfl_counter}")

    # print(dir)
    store.flush()

    for cho, _pred, og_identifier, _ in store.quads_for_pattern(
        None, ns.continuum.originalIdentifier, None
    ):
        og_id = str(og_identifier).replace('"', "")
        for _sub, _pred, file_obj, _ in store.quads_for_pattern(
            cho, ns.cont.hasHeadObject, None
        ):
            for _sub, og_name, file_name, _ in store.quads_for_pattern(
                file_obj, ns.premis.originalName, None
            ):
                file_str = str(file_name)
                if file_str.find("/") != -1:
                    page, fname = file_str.split("/", maxsplit=1)
                    p = f"{page}"
                    formatted_page = str(int(p.replace('"', ""))).rjust(3, "0")
                    new_name = fname.replace("file", f"{og_id}_{formatted_page}")
                else:
                    new_name = file_str.replace("file", f"{og_id}")
                new_name = new_name.replace('"', "")
                print(new_name)

                store.remove(Quad(file_obj, og_name, file_name))
                store.add(Quad(file_obj, og_name, Literal(new_name)))

    store.update(
        """    PREFIX    ark: <http://ark.lib.uchicago.edu/>
    PREFIX bf:        <http://id.loc.gov/ontologies/bibframe/>
    PREFIX continuum: <http://continuum.lib.uchicago.edu/ontology/>
    PREFIX contid:    <http://continuum.lib.uchicago.edu/item/>
    PREFIX premis:    <http://www.loc.gov/premis/rdf/v3/>
    PREFIX ebucore:   <http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#>
    PREFIX dc:        <http://purl.org/dc/elements/1.1/>
    PREFIX dcterms:   <http://purl.org/dc/terms/>
    PREFIX xsd:       <http://www.w3.org/2001/XMLSchema#>
    PREFIX rdf:       <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs:      <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX edm:       <http://www.europeana.eu/schemas/edm/>
    PREFIX uchicago: <https://lib.uchicago.edu/>

    INSERT {
        ?fileNode
            premis:basis [
                premis:allows uchicago:DownloadAllowed ;
            ] ;
        .
    }
    WHERE {
        ?arkNode
            dc:rights ?rights ;
            ^dcterms:isPartOf ?fileNode ;
        .
        VALUES ?rights {
            <http://creativecommons.org/licenses/by-nc/4.0/>
            <https://rightsstatements.org/page/InC-NC/1.0/>
        }
    }
    """
    )
    output = io.BytesIO()
    serialize(store, output=output, format=RdfFormat.TURTLE, prefixes=PREFIXES)
    with open(
        f"continuum_{str(datetime.datetime.now()).replace(' ', 'T')}.ttl", "w"
    ) as fp:
        fp.write(output.getvalue().decode("utf-8"))
