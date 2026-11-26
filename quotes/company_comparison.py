"""Offer comparison reads the same editable company summaries as the portal."""

def comparison_data(options, summaries, content, language):
    configuration = content.get('offer_comparison', {}).get(language)
    if not configuration:
        return None
    by_id = {s.supplier_id: s for s in summaries if s.supplier_id}
    normalize = lambda name: ''.join(name.casefold().split())
    by_name = {normalize(s.name): s for s in summaries}
    companies, seen = [], set()
    for option in options:
        if option.supplier_id in seen:
            continue
        seen.add(option.supplier_id)
        summary = by_id.get(option.supplier_id) or by_name.get(normalize(option.supplier.supplier_name))
        facts = summary.facts if summary else {}
        translated = facts if language == 'Hebrew' else facts.get('translations', {}).get(language, {})
        companies.append({'name': option.supplier_name_snapshot or option.supplier.supplier_name,
                          'values': [translated.get(key) or configuration['unknown']
                                     for key in configuration['keys']]})
    if not companies:
        return None
    for company in companies:
        company['rows'] = [{'label': label, 'value': value}
                           for label, value in zip(configuration['columns'][1:], company['values'])]
    rows = [{'label': label, 'values': [company['values'][index] for company in companies]}
            for index, label in enumerate(configuration['columns'][1:])]
    return {**configuration, 'companies': companies, 'rows': rows}


def offer_company_comparison(options, language):
    from partners.models import PortalConfiguration, SupplierSummary
    config = PortalConfiguration.objects.first()
    if not config:
        return None
    return comparison_data(options, list(SupplierSummary.objects.filter(is_active=True)), config.content, language)
