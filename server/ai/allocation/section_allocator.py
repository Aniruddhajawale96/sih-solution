from typing import Dict, List, Any


def _get_near_water_sections(payload: Dict[str, Any]) -> List[str]:
    """
    Helper to extract section names that are near water from the
    high-level payload structure.

    Expects payload to have a `soil_sections` array like:
    [
        {"section_name": "A", "near_water": true, ...},
        ...
    ]
    """
    soil_sections = payload.get("soil_sections", [])
    return [
        s["section_name"]
        for s in soil_sections
        if s.get("near_water")
    ]


def allocate_crops_to_sections(crops: List[Dict[str, Any]], payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Allocate each crop to a single primary section.

    Rules (simple, interpretable):
    - High water need crops prefer sections marked `near_water = true`.
    - Other crops prefer sections that are not near water, if available.
    - If no suitable section is found, fall back to the first section.

    Returns a mapping:
    {
        "crop_name": "SectionName",
        ...
    }
    """
    sections: List[str] = payload.get("sections", [])
    if not sections:
        return {}

    near_water_sections = _get_near_water_sections(payload)
    near_water_set = set(near_water_sections)

    allocation: Dict[str, str] = {}

    # indices to help us round‑robin sections instead of always choosing the first
    high_idx = 0
    other_idx = 0

    # Precompute non‑near‑water list (may be empty)
    non_near_sections: List[str] = [s for s in sections if s not in near_water_set]

    for crop in crops:
        name = crop["crop"]
        water_need = crop.get("water_need", "medium")

        chosen_section = None

        if water_need == "high" and near_water_sections:
            # Prefer near‑water sections, distributed across them
            chosen_section = near_water_sections[high_idx % len(near_water_sections)]
            high_idx += 1
        else:
            if non_near_sections:
                # Prefer non‑near‑water sections and distribute across them
                chosen_section = non_near_sections[other_idx % len(non_near_sections)]
                other_idx += 1
            else:
                # If every section is near water, distribute across all sections
                chosen_section = sections[other_idx % len(sections)]
                other_idx += 1

        allocation[name] = chosen_section

    return allocation
