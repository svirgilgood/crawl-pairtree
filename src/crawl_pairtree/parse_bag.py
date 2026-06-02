from pyoxigraph import Quad, Literal, NamedNode, BlankNode, Store
from dataclasses import dataclass, field, fields
from ocfl import Inventory
import os
from pathlib import Path

from .namespaces import NS, PREFIXES, Namespace

from typing import List, Optional, Tuple

ns = NS(PREFIXES)
continuum_item = Namespace("http://continuum.lib.uchicago.edu/item/")


def format_local(node: NamedNode | str) -> str:
    """
    create a path from a type_node
    """
    if isinstance(node, NamedNode):
        name = node.toPython()
    else:
        name = node
    slash_idx = name.rfind("/")
    hash_idx = name.rfind("#")
    idx = (slash_idx if slash_idx > hash_idx else hash_idx) + 1
    return name[idx:].lower()


def match_file_type(file_type: str) -> NamedNode:
    """ """
    match file_type:
        case "pf":
            return ns.continuum.Preservation
        case "vaf":
            return ns.continuum.Viewer
        case "manifest":
            return ns.continuum.Manifest
        case _:
            return ns.continuum.Supplemental


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
            return "audio/vnd.wave"
        case "pdf":
            return "application/pdf"
        case _:
            return None


def get_types(file_parts: List[str], base_name: str) -> Tuple[str | None, NamedNode]:
    match len(file_parts):
        case 3:
            _, file_type, ext = file_parts
            mime_type = find_mime_type(ext)
            type_node = match_file_type(file_type)

        case 2:
            _, ext = file_parts
            mime_type = find_mime_type(ext)
            file_type = (
                "pf" if base_name in ("file.tif", "file.pdf") else "supplemental"
            )

            type_node = match_file_type(file_type)
        case _:
            ext = file_parts[-1]
            if ext in ("pdf", "tif"):
                print(f"Error with File {' - '.join(file_parts)}")
                return (None, NamedNode("http://exmaple.org/error"))
            mime_type = find_mime_type(ext)
            type_node = match_file_type("supplimental")
    return (mime_type, type_node)


def expand_pair_tree(ark_id: str):
    """split the ark id into the pair tree"""
    return "".join([x if (i + 1) % 2 != 0 else x + "/" for i, x in enumerate(ark_id)])


@dataclass(init=True)
class BagMetadata:
    """
    BagMetadata is an object that holds the important tidbits so that they can
    be exported and parsed by other tools.
    """

    collection: str = field(default="")
    external_id: str = field(default="")
    internal_id: str = field(default="")
    resource_constraint: str = field(default="")
    resource_date: str = field(default="")
    bagging_date: str = field(default="")
    resource_title: str = field(default="")
    source_organization: str = field(default="")
    rights: str = field(default="")

    def add_inventory(self, inv: Inventory):
        """
        Add the OCFL to the BagMetadata
        """
        self.inventory = inv.data

    def set_ark_node(self, ark_node: NamedNode):
        self.ark_node = ark_node

    def to_metadata_triples(self, quad_list: List[Quad] = []) -> List[Quad]:
        """ """
        for f in fields(self):
            if getattr(self, f.name) == "":
                continue
            match f.name:
                case "internal_id":
                    quad_list.append(
                        Quad(
                            self.ark_node,
                            ns.continuum.originalIdentifier,
                            Literal(self.internal_id),
                        )
                    )
                case "resource_constraint":
                    try:
                        quad_list.append(
                            Quad(
                                self.ark_node,
                                ns.edm.rights,
                                NamedNode(self.resource_constraint),
                            )
                        )
                    except ValueError:
                        print(f"Resource Constraint: self.resource_constraint")
                        quad_list.append(
                            Quad(
                                self.ark_node,
                                ns.edm.rights,
                                Literal(self.resource_constraint),
                            )
                        )

                case "resource_date":
                    quad_list.append(
                        Quad(
                            self.ark_node, ns.dcterms.date, Literal(self.resource_date)
                        )
                    )
                case "resource_title":
                    quad_list.append(
                        Quad(
                            self.ark_node,
                            ns.dc.term("title"),
                            Literal(self.resource_title),
                        )
                    )
                case "source_organization":
                    quad_list.append(
                        Quad(
                            self.ark_node,
                            ns.edm.dataProvider,
                            Literal(self.source_organization),
                        )
                    )
                case _:
                    continue

    def add_collection(self, quad_list: List[Quad]):
        if not self.ark_node:
            return
        local_name = format_local(self.collection)
        collection_node = NamedNode(
            f"http://continuum.lib.uchicago.edu/project/{local_name}"
        )
        quad_list.append(Quad(self.ark_node, ns.dcterms.isPartOf, collection_node))
        quad_list.append(
            Quad(
                self.ark_node,
                ns.continuum.originalIdentifier,
                Literal(self.internal_id),
            )
        )
        collection_url = (
            NamedNode(self.collection)
            if self.collection.startswith("http")
            else collection_node
        )
        quad_list.append(Quad(collection_node, ns.rdfs.label, Literal(local_name)))
        quad_list.append(Quad(collection_node, ns.rdf.type, ns.continuum.Collection))
        quad_list.append(Quad(collection_node, ns.bf.electronicLocator, collection_url))

    def to_triples(
        self, quad_list: List[Quad] = [], root=Path(".")
    ) -> Optional[List[Quad]]:
        """
        Create triples from the bag metadata
        """
        if self.inventory:
            inventory = self.inventory
            digest_algo = inventory["digestAlgorithm"]
            head = inventory["head"]
            quad_list.append(Quad(ark_node, ns.continuum.head, Literal(head)))
            ark_full = inventory["id"]  # .replace("ark:61001/", "")
            versions = inventory["versions"]

        # quad_list: List[Quad] = []
        # ark_id = ark_full.replace("ark:61001/", "")
        ark_id = ark_full.replace("ark:61001/", "").replace("ark:/61001/", "")
        ark_node = ns.ark.term(ark_full)

        path = root / expand_pair_tree(ark_id)

        self.ark_node = ark_node
        self.add_collection(quad_list)
        print("ark node", ark_node)
        quad_list.append(Quad(ark_node, ns.rdf.type, ns.edm.ProvidedCHO))
        quad_list.append(Quad(ark_node, ns.continuum.hasArkID, Literal(ark_id)))
        if self.rights != "":
            quad_list.append(Quad(ark_node, ns.edm.rights, NamedNode(self.rights)))
        """
        We only need the current version of the inventory. If its the initial item,
        there will only be one version. If there are many versions, we only need
        the latest version.

        What do we need for the updates to the `continuum:hasHeadObject`?
        this might be better handeled in the import to the file.
        """
        # for version, v_obj in versions.items():
        file_name_set = set()
        for version in sorted(versions.keys(), reverse=True):
            #    if version != head:
            #        continue
            v_obj = versions[version]
            created = v_obj["created"]

            quad_list.append(
                Quad(
                    ark_node,
                    ns.dcterms.modified,
                    Literal(created, datatype=ns.xsd.datetime),
                )
            )

            for hash, file_names in v_obj["state"].items():
                for file_name in file_names:
                    base_fname = os.path.basename(file_name)
                    file_parts = file_name.split(".")
                    mime_type, type_node = get_types(file_parts, base_fname)

                    if not mime_type:
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
                    if file_name not in file_name_set:
                        file_name_set.add(file_name)
                        quad_list.append(
                            Quad(ark_node, ns.continuum.hasHeadObject, file_node)
                        )

                    if version != head:
                        continue

                    if mime_type:
                        quad_list.append(
                            Quad(file_node, ns.ebucore.hasMimeType, Literal(mime_type))
                        )

                    quad_list.append(Quad(file_node, ns.continuum.fileType, type_node))
                    quad_list.append(
                        Quad(file_node, ns.premis.originalName, Literal(file_name))
                    )
                    quad_list.append(
                        Quad(file_node, ns.continuum.partOfVersion, Literal(version))
                    )
                    quad_list.append(
                        Quad(
                            file_node,
                            ns.dcterms.created,
                            Literal(created, datatype=ns.xsd.datetime),
                        )
                    )

                    file_path = path / version / "content" / file_name
                    quad_list.append(
                        Quad(file_node, ns.continuum.hasPath, Literal(str(file_path)))
                    )
                    premis_node = BlankNode()
                    quad_list.append(Quad(file_node, ns.premis.fixity, premis_node))
                    quad_list.append(Quad(file_node, ns.dcterms.isPartOf, ark_node))
                    quad_list.append(
                        Quad(
                            premis_node,
                            ns.rdf.type,
                            NamedNode(
                                "https://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions/sha512"
                            ),
                        )
                    )
                    quad_list.append(Quad(premis_node, ns.rdf.value, Literal(hash)))

        # for hash in inventory["manifest"].keys():
        #    quad_list.append(
        #        Quad(ark_node, ns.continuum.hashForHeadFile, Literal(hash))
        #    )

        return quad_list


def fill_in_bag_terms(line: str, bag_metadata: BagMetadata) -> BagMetadata:
    """
    This parses the bag-info.txt line and fills out the bag metadata object.
    returns the updated bag_metadata
    """
    try:
        metadata_term, value = line.split(":", maxsplit=1)
        match metadata_term:
            case "Collection-Name":
                bag_metadata.collection = value.strip()
            case "External-Identifier":  # ark id
                bag_metadata.external_id = value.strip()
            case "Internal-Sender-Identifier":  # local id
                bag_metadata.internal_id = value.strip()
            case "Resource-Date":
                bag_metadata.resource_date = value.strip()
            case "Resource Title":
                bag_metadata.resource_title = value.strip()
            case "Source Organization":
                bag_metadata.source_organization = value.strip()
            case "Resource-Constraints":
                bag_metadata.rights = value.strip()
            case "Bagging-Date":
                bag_metadata.bagging_date = value.strip()
    except ValueError:
        print(f"Value Error: {line}")
    return bag_metadata


def parsing_bag(bag_info: Path) -> BagMetadata:
    """
    takes the path to the bag-info.txt and returns the BagMetadata
    object with all of the important information for the lines.
    """
    with open(bag_info, "r") as fp:
        bag_metadata = BagMetadata()
        for line in fp:
            bag_metadata = fill_in_bag_terms(line, bag_metadata)

    return bag_metadata


def parse_bag_info(bag_info: Path, id: NamedNode, store: Store):
    """ """
    quad_list: List[Quad] = []
    bag_metadata = parsing_bag(bag_info)
    bag_metadata.set_ark_node(id)
    bag_metadata.add_collection(quad_list)
    bag_metadata.to_metadata_triples(quad_list)
    for quad in quad_list:
        store.add(quad)
