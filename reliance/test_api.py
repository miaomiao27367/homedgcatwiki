import requests, json

# Compare different monsters to understand curve mapping
ids_to_check = ['20010101', '29010102', '28021305', '20040101', '20010301', '21010101']
for mid in ids_to_check:
    r = requests.get(f'https://static.nanoka.cc/gi/7.1.50/zh/monster/{mid}.json', timeout=30)
    data = r.json()
    print(f'\n=== {mid}: {data.get("name")} (codex={data.get("codex")}) ===')
    for child_id, child in data.get('child', {}).items():
        props = child.get('prop', [])
        curves = [(p.get('type',''), p.get('grow_curve','')) for p in props[:3]]
        base = child.get('base', {})
        sub = child.get('sub_hurt', {})
        monster_name = child.get('monster_name', '')
        ll = child.get('local_legend', False)
        print(f'  {child_id} [{monster_name}] type={child.get("type")} local_legend={ll}')
        print(f'    curves={curves} base={base}')
        print(f'    sub_hurt={sub}')