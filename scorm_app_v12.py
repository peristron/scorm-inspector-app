#     scorm_app_v12.py
# WORKING - LKG as of 11152025
# Directory setup:
#   cd c:\users\oakhtar\documents\pyprojs_local  (replace name/path if needed)
#
# Dependencies:
#   pip install streamlit pandas requests
#
# Run:
#   streamlit run scorm_app_v12.py

# -*- coding: utf-8 -*-
"""
scorm_app_v12.py

A Streamlit web application to parse and validate SCORM .zip packages.

Version 12 updates:
- CRITICAL FIX: Re-implemented dynamic namespace detection for the main 'imscp'
  schema. The previous version (v11) used a hardcoded namespace, causing it
  to fail silently on any package that used a slightly different but valid
  namespace URL (a very common scenario).
- Refactored parsing functions to accept a dynamically-built namespace
  dictionary, ensuring all XML queries are robust and accurate.
"""

import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
import json
import pandas as pd
import requests
from io import BytesIO

# ==============================================================================
# CORE VALIDATION, PARSING & METADATA EXTRACTION
# ==============================================================================

def find_text_or_default(node, path, namespaces, default='N/A'):
    """Safely find text in a node, returning a default if not found."""
    if node is None: return default
    found_node = node.find(path, namespaces)
    return found_node.text.strip() if found_node is not None and found_node.text else default

def extract_metadata(root, ns):
    """Extracts high-level metadata and technical properties from the manifest."""
    metadata = {}
    
    meta_node = root.find('.//imscp:metadata', ns)
    metadata['Description'] = find_text_or_default(meta_node, './/lom:description/lom:string', ns)
    metadata['Keywords'] = find_text_or_default(meta_node, './/lom:keyword/lom:string', ns)

    first_item = root.find('.//imscp:item', ns)
    if first_item is not None:
        mastery_score = find_text_or_default(first_item, './/adlcp:masteryscore', ns)
        metadata['Passing Score'] = mastery_score
        
        first_item_ref = first_item.get('identifierref')
        if first_item_ref:
            resource_node = root.find(f".//imscp:resource[@identifier='{first_item_ref}']", ns)
            if resource_node is not None:
                metadata['Launch File'] = resource_node.get('href', 'N/A')
                metadata['SCORM Type (Primary)'] = resource_node.get(f"{{{ns.get('adlcp', '')}}}scormtype", 'asset').upper()

    resources = root.findall('.//imscp:resource', ns)
    metadata['SCO Count'] = sum(1 for r in resources if r.get(f"{{{ns.get('adlcp', '')}}}scormtype", 'asset') == 'sco')
    metadata['Asset Count'] = sum(1 for r in resources if r.get(f"{{{ns.get('adlcp', '')}}}scormtype", 'asset') == 'asset')

    sequencing_node = root.find('.//imsss:sequencing', ns)
    if sequencing_node:
        seq_rules = {}
        control_mode = sequencing_node.find('imsss:controlMode', ns)
        if control_mode is not None:
            seq_rules['Flow'] = 'Forced/Linear' if control_mode.get('flow') == 'true' else 'User Choice'
            seq_rules['Forward Only'] = control_mode.get('forwardOnly', 'false')
        metadata['Sequencing Rules'] = seq_rules

    return metadata

def validate_scorm_package(scorm_zip, root, ns):
    """Runs checks on the parsed SCORM package."""
    findings = []
    zip_files = set(scorm_zip.namelist())
    
    sequencing_node = root.find('.//imsss:sequencing', ns)
    version = "SCORM 2004" if sequencing_node is not None else "SCORM 1.2"
    findings.append({'level': 'INFO', 'message': f'Detected Version: {version}.'})

    resource_nodes = root.findall('.//imscp:resource', ns)
    item_nodes = root.findall('.//imscp:item', ns)
    resource_ids = {res.get('identifier') for res in resource_nodes}
    
    for item in item_nodes:
        ref = item.get('identifierref')
        if ref and ref not in resource_ids:
            findings.append({'level': 'ERROR', 'message': f"Broken Link: Item '{item.get('identifier')}' references non-existent resource '{ref}'."})

    for resource in resource_nodes:
        href = resource.get('href')
        if href and href.replace('\\', '/') not in zip_files:
            findings.append({'level': 'ERROR', 'message': f"Missing File: Resource '{resource.get('identifier')}' points to '{href}' which is missing from the zip."})

    return findings

def parse_scorm(scorm_file_object, source_name="file"):
    """Parses, validates, and extracts metadata from a SCORM package."""
    try:
        with zipfile.ZipFile(scorm_file_object, 'r') as scorm_zip:
            if 'imsmanifest.xml' not in scorm_zip.namelist():
                st.error("CRITICAL: 'imsmanifest.xml' not found.")
                return None
            
            xml_content = scorm_zip.open('imsmanifest.xml').read()
            raw_xml_string = xml_content.decode('utf-8', 'ignore')
            root = ET.fromstring(xml_content)
            
            # --- DYNAMIC NAMESPACE DETECTION (CRITICAL FIX) ---
            # Create a dictionary with the stable, known namespaces
            ns = {
                'adlcp': 'http://www.adlnet.org/xsd/adlcp_v1p3',
                'imsss': 'http://www.imsglobal.org/xsd/imsss_v1p0',
                'lom': 'http://ltsc.ieee.org/xsd/LOM'
            }
            # Dynamically detect the main 'imscp' namespace from the root tag and add it
            if '}' in root.tag:
                ns['imscp'] = root.tag.split('}')[0][1:]
            else:
                # Fallback for manifests without explicit namespace in root tag
                ns['imscp'] = '' 

            # --- Run all analyses with the correct namespaces ---
            validation_results = validate_scorm_package(scorm_zip, root, ns)
            metadata = extract_metadata(root, ns)
            
            # --- Parse structure ---
            resources = {res.get('identifier'): res.get('href') for res in root.findall('.//imscp:resource', ns)}
            org_element = root.find('.//imscp:organization', ns)
            if org_element is None:
                st.error("Error: Could not find the <organization> element. The manifest might be malformed.")
                # Still return partial results for diagnostics
                return {'source': source_name, 'course_title': 'Unknown', 'structure': [], 'metadata': metadata, 'validation': validation_results, 'raw_manifest': raw_xml_string}
            
            course_title = find_text_or_default(org_element, 'imscp:title', ns, 'Untitled Course')

            def parse_items(parent_element):
                items_list = []
                for item_element in parent_element.findall('imscp:item', ns):
                    items_list.append({
                        'identifier': item_element.get('identifier'),
                        'title': find_text_or_default(item_element, 'imscp:title', ns, 'No Title'),
                        'resource_href': resources.get(item_element.get('identifierref')),
                        'sub_items': parse_items(item_element)
                    })
                return items_list

            return {
                'source': source_name,
                'course_title': course_title,
                'structure': parse_items(org_element),
                'metadata': metadata,
                'validation': validation_results,
                'raw_manifest': raw_xml_string
            }

    except Exception as e:
        st.error(f"A critical error occurred during analysis. See details below.")
        st.exception(e)
        return None

def flatten_structure(items, parent_title=""):
    flat_list = []
    for item in items:
        current_title = f"{parent_title}{item['title']}"
        if item['resource_href']: flat_list.append({'Path': current_title, 'File': item['resource_href'], 'Identifier': item['identifier']})
        if item['sub_items']: flat_list.extend(flatten_structure(item['sub_items'], parent_title=f"{current_title} -> "))
    return flat_list

# ==============================================================================
# STREAMLIT WEB INTERFACE
# ==============================================================================
st.set_page_config(page_title="SCORM Inspector(12)", layout="wide")
st.title(":mag: SCORM Package Inspector(v12)")

# --- STATE MANAGEMENT ---
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None
    st.session_state.file_processed_id = None

def reset_state():
    st.session_state.analysis_data = None
    st.session_state.file_processed_id = None

# --- INPUT METHOD ---
st.subheader("Step 1: Provide Your SCORM Package")
input_method = st.radio("Choose input method:", ("Upload a local file (Recommended)", "Enter a direct URL (Advanced)"), label_visibility="collapsed", on_change=reset_state)

if input_method.startswith("Upload"):
    with st.expander("Guide for Brightspace/D2L Users"):
        st.markdown("1. Go to **Course Admin** > **Manage Files**. 2. Find and **Download** the SCORM `.zip` file. 3. Upload it below.")
    uploaded_file = st.file_uploader("Upload your SCORM .zip file", type=['zip'], label_visibility="collapsed", on_change=reset_state)
    
    if uploaded_file and uploaded_file.file_id != st.session_state.get('file_processed_id'):
        with st.spinner("Analyzing SCORM package..."):
            st.session_state.analysis_data = parse_scorm(uploaded_file, uploaded_file.name)
        st.session_state.file_processed_id = uploaded_file.file_id
        st.rerun()

# --- DISPLAY RESULTS ---
st.markdown("---")
if st.session_state.get('analysis_data'):
    st.subheader("Step 2: Review Analysis")
    data = st.session_state.analysis_data
    metadata = data['metadata']
    validation = data['validation']

    st.header(f"`{data['course_title']}`")

    # Download buttons
    col1, col2, col3 = st.columns(3)
    with col1: st.download_button("Download Full Analysis (JSON)", json.dumps(data, indent=2), f"{data['course_title']}_full_analysis.json", "application/json")
    with col2: st.download_button("Download Content Map (CSV)", pd.DataFrame(flatten_structure(data['structure'])).to_csv(index=False), f"{data['course_title']}_content_map.csv", "text/csv")
    with col3: st.button("Clear & Start Over", on_click=reset_state, type="primary")

    # --- Main Display Tabs ---
    tab_summary, tab_validation, tab_map, tab_hier, tab_raw = st.tabs([
        ":clipboard: Summary & Metadata", ":shield: Validation Report", ":map: Content Map", 
        ":diamond_shape_with_a_dot_inside: Hierarchical View", ":scroll: Raw Manifest"
    ])

    with tab_summary:
        st.subheader("Course Profile")
        c1, c2, c3 = st.columns(3)
        c1.metric("Trackable Objects (SCOs)", metadata.get('SCO Count', 'N/A'))
        c2.metric("Static Content (Assets)", metadata.get('Asset Count', 'N/A'))
        c3.metric("Passing Score", metadata.get('Passing Score', 'N/A'))
        
        st.write(f"**Description:** {metadata.get('Description', 'N/A')}")
        st.write(f"**Launch File:** `{metadata.get('Launch File', 'N/A')}`")
        st.write(f"**Keywords:** {metadata.get('Keywords', 'N/A')}")

        if 'Sequencing Rules' in metadata:
            with st.expander("SCORM 2004 Sequencing Rules"):
                st.json(metadata['Sequencing Rules'])

    with tab_validation:
        st.subheader("Package Health Check")
        errors = [f['message'] for f in validation if f['level'] == 'ERROR']
        warnings = [f['message'] for f in validation if f['level'] == 'WARNING']
        infos = [f['message'] for f in validation if f['level'] == 'INFO']
        
        if not errors and not warnings:
            st.success("No critical errors or warnings found.")
        if errors:
            st.error(f"Found {len(errors)} error(s):")
            for e in errors: st.write(f"- {e}")
        if warnings:
            st.warning(f"Found {len(warnings)} warning(s):")
            for w in warnings: st.write(f"- {w}")
        st.info("Informational Notes:")
        for i in infos: st.write(f"- {i}")

    with tab_map:
        st.dataframe(pd.DataFrame(flatten_structure(data['structure'])), use_container_width=True, hide_index=True)

    with tab_hier:
        st.json(data['structure'])
        
    with tab_raw:
        st.code(data['raw_manifest'], language='xml')

else:
    st.info("Provide a SCORM file source above to begin analysis.")