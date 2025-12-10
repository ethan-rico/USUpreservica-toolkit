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
DCTERMS_NAMESPACE = "http://purl.org/dc/terms/"

def build_qdc_xml(metadata: Dict[str, str]) -> str:
    # Set the default namespace to match the metadata schema
    # Register both DC and DCTERMS so output includes appropriate namespaces
    try:
        register_namespace('dc', DC_NAMESPACE)
        register_namespace('dcterms', DCTERMS_NAMESPACE)
        register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    except Exception:
        pass

    # Create root element for qdc (no prefix; we'll use explicit namespaced children)
    root = Element(f"{{{DC_NAMESPACE}}}dc")
    # Include xsi:schemaLocation attribute pointing to the QDC schema so Preservica accepts the block
    try:
        root.set('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', 'https://www.dublincore.org/schemas/xmls/qdc/dc.xsd')
    except Exception:
        pass

    # Group repeated keys (handles both dc: and dcterms: prefixes)
    grouped = defaultdict(list)
    for key, value in metadata.items():
        if not value or not str(value).strip():
            continue
        # Accept both dc: and dcterms: prefixes
        if key.startswith("dc:") or key.startswith("dcterms:"):
            base_key = re.sub(r"\.\d+$", "", key)
            grouped[base_key].append(str(value).strip())

    # Add elements using appropriate namespaces
    for base_key, values in grouped.items():
        prefix, tag = base_key.split(":", 1)
        ns_uri = DC_NAMESPACE if prefix == 'dc' else DCTERMS_NAMESPACE
        for val in values:
            elem = SubElement(root, f"{{{ns_uri}}}{tag}")
            elem.text = val

    return tostring(root, encoding="unicode")



def update_asset_metadata(client: EntityAPI, reference: str, updated_metadata: Dict[str, str]) -> str:
    try:
        entity = client.asset(reference)
    except Exception:
        entity = client.folder(reference)

    metadata_blocks = entity.metadata or {}

    # Prepare grouped DC values and custom-schema values
    dc_grouped = defaultdict(list)  # base dc:key -> [values]
    custom_schemas = defaultdict(lambda: defaultdict(list))  # schema_url -> {element: [values]}

    for key, value in updated_metadata.items():
        # Skip known non-metadata columns commonly present in CSV exports
        if key in ("reference", "title", "type", "qdc_xml"):
            continue

        if not (value and value.strip()):
            continue
        val = value.strip()
        # DC fields (dc:tag or dc:tag.N) and DCTERMS fields
        if key.startswith("dc:") or key.startswith("dcterms:"):
            base_key = re.sub(r"\.\d+$", "", key)
            dc_grouped[base_key].append(val)
        # Custom schema header format: schemaURL::elementName
        elif "::" in key:
            schema_url, elem = key.split("::", 1)
            schema_url = schema_url.strip()
            elem = elem.strip()
            if schema_url and elem:
                custom_schemas[schema_url][elem].append(val)
        else:
            # Non-dc single unknown headers: treat as a DC-less custom field under a generic metadata block
            # Put them under a generic local schema URL so they get added as a separate metadata block
            custom_schemas["urn:local:custom"][key].append(val)

    results = []

    # Handle QDC (dc:) metadata
    if dc_grouped:
        schema_url = DC_NAMESPACE

        # Try to fetch existing QDC XML
        qdc_xml, _ = fetch_current_metadata(client, reference)

        if qdc_xml:
            # Parse existing XML and replace groups
            root = ET.fromstring(qdc_xml)
            ns = {"dc": DC_NAMESPACE, "dcterms": DCTERMS_NAMESPACE}

            for base_key, values in dc_grouped.items():
                prefix, tag = base_key.split(":", 1)
                ns_uri = ns.get(prefix, DC_NAMESPACE)

                # Remove existing elements of this tag (using the correct namespace)
                for elem in list(root.findall(f".//{{{ns_uri}}}{tag}")):
                    parent = root
                    parent.remove(elem)

                # Add new elements
                for v in values:
                    new_elem = ET.SubElement(root, f"{{{ns_uri}}}{tag}")
                    new_elem.text = v

            updated_xml = ET.tostring(root, encoding="unicode")
        else:
            # Build fresh QDC XML
            # build_qdc_xml filters keys starting with dc: and dcterms: and will create a proper DC-rooted XML
            # build a flat mapping like dc:tag, dc:tag.1 ...
            flat = {}
            for base_key, values in dc_grouped.items():
                for idx, v in enumerate(values):
                    keyname = base_key if idx == 0 else f"{base_key}.{idx}"
                    flat[keyname] = v
            updated_xml = build_qdc_xml(flat)

        # Add or update QDC block
        if DC_NAMESPACE in (metadata_blocks or {}).values():
            client.update_metadata(entity, DC_NAMESPACE, updated_xml)
            results.append("Updated existing QDC metadata")
        else:
            client.add_metadata(entity, DC_NAMESPACE, updated_xml)
            results.append("Added new QDC metadata")

    # Handle custom schema blocks
    for schema_url, elements in custom_schemas.items():
        # Build XML for this custom schema. Preservica requires a default namespace
        # that matches the schemaUri; create namespaced elements when possible.
        try:
            # register default namespace so tostring() emits it
            register_namespace('', schema_url)
        except Exception:
            pass

        # Create root element with the schema_url as the default namespace
        try:
            root = Element(f"{{{schema_url}}}metadata")
        except Exception:
            # fallback to non-namespaced element if schema_url not usable as namespace
            root = Element("metadata")

        for elem_name, vals in elements.items():
            for v in vals:
                try:
                    child = SubElement(root, f"{{{schema_url}}}{elem_name}")
                except Exception:
                    child = SubElement(root, elem_name)
                child.text = v

        updated_xml = tostring(root, encoding="unicode")

        if schema_url in (metadata_blocks or {}).values():
            client.update_metadata(entity, schema_url, updated_xml)
            results.append(f"Updated metadata for {schema_url}")
        else:
            client.add_metadata(entity, schema_url, updated_xml)
            results.append(f"Added metadata for {schema_url}")

    if results:
        return "; ".join(results)

    return "No changes applied"

