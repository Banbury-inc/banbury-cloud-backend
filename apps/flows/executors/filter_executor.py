"""
Filter Data executor: filters a list of records from upstream inputs by conditions.
"""


def _matches(record: dict, conditions: list) -> bool:
    for cond in conditions:
        field = cond.get('field', '')
        operator = cond.get('operator', '=')
        value = cond.get('value', '')

        record_val = record.get(field)
        record_str = str(record_val) if record_val is not None else ''

        if operator == '=':
            if record_str != str(value):
                return False
        elif operator == '!=':
            if record_str == str(value):
                return False
        elif operator == '>':
            try:
                if float(record_str) <= float(value):
                    return False
            except (ValueError, TypeError):
                return False
        elif operator == '<':
            try:
                if float(record_str) >= float(value):
                    return False
            except (ValueError, TypeError):
                return False
        elif operator == '>=':
            try:
                if float(record_str) < float(value):
                    return False
            except (ValueError, TypeError):
                return False
        elif operator == '<=':
            try:
                if float(record_str) > float(value):
                    return False
            except (ValueError, TypeError):
                return False
        elif operator == 'contains':
            if str(value).lower() not in record_str.lower():
                return False

    return True


def execute(node_data: dict, inputs: dict) -> dict:
    conditions = node_data.get('conditions', [])

    # Collect rows/items from upstream
    records = []
    for upstream_output in inputs.values():
        if isinstance(upstream_output, dict):
            data = upstream_output.get('data', {})
            if isinstance(data, dict):
                rows = data.get('rows') or data.get('items') or data.get('results') or []
                if isinstance(rows, list):
                    records.extend(rows)

    if not conditions:
        return {'status': 'success', 'data': {'rows': records, 'count': len(records)}}

    filtered = [r for r in records if isinstance(r, dict) and _matches(r, conditions)]
    return {'status': 'success', 'data': {'rows': filtered, 'count': len(filtered)}}
