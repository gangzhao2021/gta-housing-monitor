"""Explicit source market identities; no guessed municipality or district merges."""
MONTHLY_REGIONS = {
    'toronto': 'Toronto', 'north_york': 'North York', 'scarborough': 'Scarborough',
    'markham': 'Markham', 'vaughan': 'Vaughan', 'mississauga': 'Mississauga', 'oakville': 'Oakville',
}
CMHC_REGIONS = {
    'north_york': 'North York (Zones 13-17)',
    'scarborough': 'Scarborough (Zones 10-12)',
    'mississauga': 'Mississauga City (Zones 18-20)',
    'oakville': 'Zone 23 - Oakville', 'markham': 'Zone 27 - Markham',
    'richmond_vaughan_king': 'Zone 25 - Richmond Hill/Vaughan/King',
    'aurora_newmarket_whit': 'Zone 26 - Aurora, Newmkt, Whit-St.',
}

def asking_id(region, room):
    return f'toronto_asking_rent_{room}' if region == 'toronto' else f'regional_asking_{region}_{room}'

def cmhc_id(region, measure, room):
    suffix = 'rate' if measure == 'vacancy' and room == 'total' else room
    return f'regional_cmhc_{region}_pbr_{measure}_{suffix}'
