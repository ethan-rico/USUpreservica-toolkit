# update_metadata/metadata_updater.py

import xml.etree.ElementTree as ET
from pyPreservica import EntityAPI
from typing import Dict
from .metadata_diff import NAMESPACES
from collections import defaultdict
import re
from xml.etree.ElementTree import Element, SubElement, tostring, register_namespace
from .metadata_diff import fetch_current_metadata

QDC_NAMESPACE = "http://www.openarchives.org/OAI/2.0/oai_dc/"
DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"

def build_qdc_xml(metadata: Dict[str, str]) -> str:
    # Set the default namespace to match the metadata schema
    register_namespace('', DC_NAMESPACE)

    # Create root with the default namespace
    root = Element(f"{{{DC_NAMESPACE}}}dc")

    # Group repeated keys (e.g., dc:creator.1, dc:creator.2 → dc:creator)
    grouped = defaultdict(list)
    for key, value in metadata.items():
        if not key.startswith("dc:") or not value.strip():
            continue
        base_key = re.sub(r"\.\d+$", "", key)
        grouped[base_key].append(value.strip())

    # Add elements using default namespace
    for base_key, values in grouped.items():
        _, tag = base_key.split(":")
        for val in values:
            elem = SubElement(root, f"{{{DC_NAMESPACE}}}{tag}")
            elem.text = val

    return tostring(root, encoding="unicode")



def update_asset_metadata(client: EntityAPI, reference: str, updated_metadata: Dict[str, str]) -> str:
    try:
        entity = client.asset(reference)
    except Exception:
        entity = client.folder(reference)

    schema_url = "http://purl.org/dc/elements/1.1/"
    metadata_blocks = entity.metadata or {}

    # Fetch current QDC XML
    qdc_xml, _ = fetch_current_metadata(client, reference)

    if not qdc_xml:
        return "Skipped — no existing QDC metadata to modify"

    # Parse XML
    root = ET.fromstring(qdc_xml)

    # Map namespace prefixes
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}

    # Group repeated fields like dc:identifier, dc:identifier.1, etc.
    grouped = defaultdict(list)
    for key, value in updated_metadata.items():
        if key.startswith("dc:") and value.strip():
            base_key = re.sub(r"\.\d+$", "", key)
            grouped[base_key].append(value.strip())

    # Remove existing elements and replace with all values for each group
    for base_key, values in grouped.items():
        tag = base_key.split(":")[1]

        # Remove all existing elements of this tag
        for elem in root.findall(f"dc:{tag}", namespaces=ns):
            root.remove(elem)

        # Add all new elements for this tag
        for val in values:
            new_elem = ET.SubElement(root, f"{{{ns['dc']}}}{tag}")
            new_elem.text = val

    # Generate updated XML
    updated_xml = ET.tostring(root, encoding="unicode")

    if schema_url in metadata_blocks.values():
        block_id = next((block for block, schema in metadata_blocks.items() if schema == schema_url), None)
        if block_id:
            client.update_metadata(entity, schema_url, updated_xml)
            return "Updated existing QDC metadata"
    else:
        client.add_metadata(entity, schema_url, updated_xml)
        return "Added new QDC metadata"

    return "Skipped — metadata block could not be determined"

