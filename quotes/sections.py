def arrange_sections(options, presentation):
    """Keep relative order within each configured section; number globally in template."""
    order = presentation.get("section_order", ["cars", "crossovers", "premium", "vans"])
    labels = presentation.get("section_labels", {})
    result = sorted(options, key=lambda option: order.index(option.vehicle_group.offer_section)
                    if option.vehicle_group.offer_section in order else len(order))
    multiple = len({option.vehicle_group.offer_section for option in result}) > 1
    previous = None
    for option in result:
        section = option.vehicle_group.offer_section
        option.section_heading = labels.get(section, "") if multiple and section != previous else ""
        previous = section
    return result
