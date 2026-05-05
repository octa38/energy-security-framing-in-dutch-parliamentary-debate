"""
enrich_speakers.py
==================

Adds speaker-level metadata to the processed ParlaMint CSV.
The ParlaMint .txt files are convenient for text processing, but they usually do
not contain rich metadata such as party, gender, role, or full speaker name.

This script reads the ParlaMint TEI/XML files and tries to extract:
- speaker_id
- speaker_name
- speaker_gender
- speaker_role
- speaker_party

Then it joins those fields onto: processed/energy_security_utterances.csv
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from lxml import etree


NS = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "xml": "http://www.w3.org/XML/1998/namespace",
}


def clean_ref(value: Optional[str]) -> str:
    """Remove leading # from TEI references."""
    if not value:
        return ""
    return value.strip().lstrip("#")


def first_text(element, xpath: str) -> str:
    """Return first non-empty text from an XPath query."""
    if element is None:
        return ""

    results = element.xpath(xpath, namespaces=NS)
    for result in results:
        if isinstance(result, str):
            text = result.strip()
        else:
            text = " ".join(result.itertext()).strip()

        if text:
            return re.sub(r"\s+", " ", text)

    return ""


def get_xml_id(element) -> str:
    """Get xml:id from an XML element."""
    if element is None:
        return ""
    return element.get("{http://www.w3.org/XML/1998/namespace}id", "")


def parse_orgs(tree: etree._ElementTree) -> Dict[str, str]:
    """
    Extract organisation IDs and names.
    """
    org_lookup: Dict[str, str] = {}

    for org in tree.xpath("//tei:org", namespaces=NS):
        org_id = get_xml_id(org)
        if not org_id:
            continue

        org_name = first_text(org, ".//tei:orgName")
        if not org_name:
            org_name = first_text(org, ".//tei:name")

        if org_name:
            org_lookup[org_id] = org_name

    return org_lookup


def clean_party_ref(ref: str) -> str:
    """
    Convert common party/org refs into a readable fallback.

    """
    ref = clean_ref(ref)
    ref = ref.replace("party.", "").replace("org.", "")
    return ref.strip()


def parse_person_metadata(tree: etree._ElementTree, org_lookup: Dict[str, str]) -> Dict[str, dict]:
    """
    Extract speaker metadata from <person> elements.
    """
    people: Dict[str, dict] = {}

    for person in tree.xpath("//tei:person", namespaces=NS):
        person_id = get_xml_id(person)
        if not person_id:
            continue

        # Important: use TEI-aware XPath, not non-namespaced findall().
        name = first_text(person, ".//tei:persName")
        if not name:
            # Fallback: speaker id often contains a readable name.
            name = re.sub(r"(?<!^)(?=[A-Z])", " ", person_id).strip()

        gender = (
            person.get("sex")
            or person.get("gender")
            or first_text(person, ".//tei:sex/text()")
            or first_text(person, ".//tei:sex/@value")
        )

        role = (
            first_text(person, ".//tei:roleName")
            or person.get("role")
            or ""
        )

        # Party can appear in affiliation/@ref, affiliation text, or orgName.
        party = ""

        affiliation_refs = person.xpath(".//tei:affiliation/@ref", namespaces=NS)
        for ref in affiliation_refs:
            ref_id = clean_ref(ref)
            if ref_id in org_lookup:
                party = org_lookup[ref_id]
                break

        # Fallback: keep the raw party ref cleaned if org lookup is unavailable.
        if not party and affiliation_refs:
            party = clean_party_ref(affiliation_refs[0])

        if not party:
            party = first_text(person, ".//tei:affiliation//tei:orgName")

        if not party:
            party = first_text(person, ".//tei:affiliation")

        people[person_id] = {
            "speaker_id": person_id,
            "speaker_name": name,
            "speaker_gender": gender.strip() if isinstance(gender, str) else "",
            "speaker_role": role,
            "speaker_party": party,
        }

    return people


def parse_utterance_speaker_links(tree: etree._ElementTree) -> Dict[str, str]:
    """
    Build mapping:
        utterance_id -> speaker_id

    """
    links: Dict[str, str] = {}

    for utt in tree.xpath("//tei:u", namespaces=NS):
        utt_id = get_xml_id(utt)
        speaker_ref = clean_ref(utt.get("who"))

        if utt_id and speaker_ref:
            links[utt_id] = speaker_ref

    return links


def collect_metadata(tei_dir: Path) -> pd.DataFrame:
    """
    Scan all XML files and collect utterance-level speaker metadata.
    """
    xml_files = sorted(tei_dir.rglob("*.xml"))

    if not xml_files:
        raise FileNotFoundError(f"No XML files found under {tei_dir}")

    rows = []

    for i, xml_file in enumerate(xml_files, start=1):
        try:
            tree = etree.parse(str(xml_file))
        except Exception as exc:
            print(f"Skipping unreadable XML file: {xml_file} ({exc})")
            continue

        org_lookup = parse_orgs(tree)
        people = parse_person_metadata(tree, org_lookup)
        utterance_links = parse_utterance_speaker_links(tree)

        for utterance_id, speaker_id in utterance_links.items():
            metadata = people.get(speaker_id, {
                "speaker_id": speaker_id,
                "speaker_name": re.sub(r"(?<!^)(?=[A-Z])", " ", speaker_id).strip(),
                "speaker_gender": "",
                "speaker_role": "",
                "speaker_party": "",
            })

            rows.append({
                "utterance_id": utterance_id,
                "speaker_id": metadata["speaker_id"],
                "speaker_name": metadata["speaker_name"],
                "speaker_gender": metadata["speaker_gender"],
                "speaker_role": metadata["speaker_role"],
                "speaker_party": metadata["speaker_party"],
                "metadata_source_file": xml_file.name,
            })

        if i % 100 == 0:
            print(f"Scanned {i}/{len(xml_files)} XML files...")

    if not rows:
        return pd.DataFrame(columns=[
            "utterance_id", "speaker_id", "speaker_name", "speaker_gender",
            "speaker_role", "speaker_party", "metadata_source_file"
        ])

    return pd.DataFrame(rows).drop_duplicates(subset=["utterance_id"])


def add_speaker_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add simple speaker-level aggregate columns back onto each utterance row.

    These are useful for dashboards and ranking speakers.
    """
    if "speaker_id" not in df.columns:
        return df

    aggregates = (
        df.groupby(["speaker_id"], dropna=False)
        .agg(
            speaker_total_utterances=("utterance_id", "count"),
            speaker_avg_security_density=("security_density", "mean")
                if "security_density" in df.columns else ("security_score", "mean"),
            speaker_avg_economic_density=("economic_density", "mean")
                if "economic_density" in df.columns else ("economic_score", "mean"),
            speaker_avg_climate_density=("climate_density", "mean")
                if "climate_density" in df.columns else ("climate_score", "mean"),
            speaker_avg_minerals_density=("minerals_density", "mean")
                if "minerals_density" in df.columns else ("minerals_score", "mean"),
            speaker_energy_security_overlap=("is_energy_security", "sum"),
            speaker_energy_minerals_overlap=("is_energy_minerals", "sum"),
        )
        .reset_index()
    )

    return df.merge(aggregates, on="speaker_id", how="left")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich processed ParlaMint CSV with speaker metadata.")
    parser.add_argument("--processed_csv", required=True, help="Path to processed CSV.")
    parser.add_argument("--tei_dir", required=True, help="Path to ParlaMint TEI/XML folder.")
    parser.add_argument("--out_csv", default="./processed/energy_security_utterances_enriched.csv")
    args = parser.parse_args()

    processed_csv = Path(args.processed_csv)
    tei_dir = Path(args.tei_dir)
    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    if not processed_csv.exists():
        raise FileNotFoundError(f"Processed CSV not found: {processed_csv}")

    if not tei_dir.exists():
        raise FileNotFoundError(f"TEI directory not found: {tei_dir}")

    print("Loading processed CSV...")
    df = pd.read_csv(processed_csv)

    print("Collecting speaker metadata from TEI/XML files...")
    speaker_df = collect_metadata(tei_dir)

    print(f"Found speaker links for {len(speaker_df):,} utterances.")

    enriched = df.merge(speaker_df, on="utterance_id", how="left")

    matched = enriched["speaker_id"].notna().sum()
    total = len(enriched)

    print(f"Matched speaker metadata for {matched:,}/{total:,} processed utterances.")

    enriched = add_speaker_aggregates(enriched)

    enriched.to_csv(out_csv, index=False, encoding="utf-8")

    print(f"\nDone. Wrote enriched file to: {out_csv}")

    if total > 0:
        print(f"Metadata match rate: {matched / total * 100:.1f}%")

    if "speaker_name" in enriched.columns:
        top_speakers = (
            enriched.groupby(["speaker_id", "speaker_name", "speaker_party"], dropna=False)
            .size()
            .reset_index(name="utterances")
            .sort_values("utterances", ascending=False)
            .head(10)
        )

        print("\nTop speakers in processed subset:")
        print(top_speakers.to_string(index=False))

    if "speaker_party" in enriched.columns:
        print("\nTop party/affiliation values:")
        print(enriched["speaker_party"].fillna("Unknown").replace("", "Unknown").value_counts().head(15).to_string())


if __name__ == "__main__":
    main()
