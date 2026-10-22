"""Check the paper's displayed numbers against an independent rebuild. Standard library only."""
from pathlib import Path
import csv, hashlib, json, math, subprocess, sys
from calculate_paired import load, paired, ceiling, R
from copy import deepcopy

checks = []
def check(label, condition):
    if not condition:
        raise AssertionError(label)
    checks.append(label)

def rounded(label, actual, displayed, digits=1, scale=1):
    check(label, f'{actual * scale:.{digits}f}' == str(displayed).replace(',', '').replace('%', ''))

def close(label, a, b):
    check(label, math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-9))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if (R / 'MANIFEST.sha256').exists():
    for line in (R / 'MANIFEST.sha256').read_text().splitlines():
        h, name = line.split('  ', 1)
        check('package integrity ' + name, digest(R / name) == h)

# Start from the supplied values and rebuild in a separate interpreter.
before = {str(p.relative_to(R)): digest(p) for p in (R / 'results').iterdir()
          if p.suffix in ('.csv', '.json') and p.name != 'publication-verification.json'}
for script in ['calculate_paired.py', 'verify_paired.py']:
    run = subprocess.run([sys.executable, str(R / script)], cwd=R,
                         text=True, capture_output=True, check=True)
    if script == 'verify_paired.py':
        check('38 paired checks and 30 recovery-model checks',
              'PASS 38 paired checks; legacy PASS 30 checks' in run.stdout)
check('all supplied paired result files reproduce byte for byte',
      all(digest(R / n) == h for n, h in before.items()))

c = load()
d = c['designs'][0]
fixture = json.loads((R / 'publication-tables.json').read_text())
case_map = {
    'Selective target': (d, {}),
    'Moderate integration': (c['designs'][2], {}),
    'Recovery/selectivity penalty': (c['coupled_stresses'][0]['design'], {}),
    'Combined process penalties': (c['coupled_stresses'][2]['design'], {'extra_power': 100}),
    'Hot dilute': (c['designs'][3], {})
}
for row in fixture['paper'][1][1:]:
    label, electricity, conventional, basalt, reduction = row
    design, kw = case_map[label]
    x = paired(c, design, float(electricity) / 1000, **kw)
    prefix = 'Table 2 ' + label + ' ' + electricity + ' g/kWh '
    rounded(prefix + 'conventional', x['baseline_kg'], conventional)
    rounded(prefix + 'basalt', x['new_kg'], basalt)
    rounded(prefix + 'reduction', x['reduction_fraction'], reduction, scale=100)

core = json.loads((R / 'legacy' / 'inputs.json').read_text())
keys = ['feed_CaO_fraction', 'overall_Ca_recovery', 'reagent_equivalent_multiplier',
        'bmed_kWh_per_kgNaOH', 'leach_deltaT_K', 'sensible_heat_recovery_fraction',
        'cake_dry_solids_fraction', 'grinding_kWh_per_trock',
        'other_burden_kgCO2e_per_trock', 'makeup_loss_fraction']
for row, key in zip(fixture['supplement'][0][1:], keys):
    for design, displayed in zip(c['designs'], row[1:]):
        effective = {**core['defaults'], **core['designs'][0], **c['designs'][0], **design}
        close('Table S1 ' + design['id'] + ' ' + key, effective[key], float(displayed))

stress_specs = [(d, {}), (c['coupled_stresses'][0]['design'], {}),
                (c['coupled_stresses'][1]['design'], {'extra_power': 100}),
                (c['coupled_stresses'][2]['design'], {'extra_power': 100}),
                (d, {'extra_heat': 1, 'extra_power': 100, 'delta_other': 30}),
                (c['coupled_stresses'][4]['design'], {}),
                ({'reagent_equivalent_multiplier': 1.5}, {}),
                ({'reagent_equivalent_multiplier': 1.6}, {}),
                ({'sensible_heat_recovery_fraction': .7}, {}),
                ({'cake_dry_solids_fraction': .65}, {}), (d, {'heat': 100})]
for row, (design, kw) in zip(fixture['supplement'][1][1:], stress_specs):
    for ci, displayed in zip([.03, .05], row[1:]):
        rounded('Table S2 ' + row[0] + ' ' + str(ci),
                paired(c, design, ci, **kw)['reduction_fraction'], displayed, scale=100)

# Independently evaluate the supplement S2-S4 equations, without calling the model.
q = 456 / 1000 / (44.01 / 56.077)
rock = q / (.12 * .9)
acid_eq = 2 * q * 1e6 / 56.077 * 1.3
base_eq = acid_eq / .9
base_kg = base_eq * 39.997 / 1000
acid_m3, base_m3 = acid_eq / 900, base_eq / 1000
power = base_kg * 1.8 * 1.1 + rock * 30 + 50
gross = ((acid_m3 + .5 * base_m3) * 4.18 + rock * .84) * 35 / 1000
water = q * 74.093 / 56.077 * (1 / .8 - 1)
heat = (gross * .15 + water * 2.4 / .8) * 1.1
burden = power * .03 + heat * 70 + base_kg * .02 * 3 + rock * 8 + rock * 2 + 10
B = 480 + 3.5 * .914 * 70 + 100 * .03 + 50
x = paired(c, d, .03)
for key, independent in [('q_CaOeq_t', q), ('rock_t', rock),
        ('reagent_pairs_mol', acid_eq), ('generated_base_mol', base_eq),
        ('base_equivalent_kg', base_kg), ('acid_m3', acid_m3), ('base_m3', base_m3),
        ('electricity_kWh', power), ('extra_heat_GJ', heat), ('P_kg', burden), ('baseline_kg', B)]:
    close('independent worked-case equation ' + key, x[key], independent)

reported = [('rock_t', '5.37990', 5), ('reagent_pairs_mol', '26939.3', 1),
            ('generated_base_mol', '29932.6', 1), ('base_equivalent_kg', '1197.2', 1),
            ('acid_m3', '29.9326', 4), ('base_m3', '29.9326', 4),
            ('electricity_kWh', '2581.9', 1), ('extra_heat_GJ', '1.74329', 5),
            ('P_kg', '335.118287', 6), ('new_kg', '636.048287', 6),
            ('net_saving_kg', '120.9', 1), ('margin10_kg', '45.2', 1)]
for key, displayed, digits in reported:
    rounded('worked case displayed ' + key, x[key], displayed, digits)
rounded('10 percent electricity ceiling', ceiling(c, d, .1), '47.4', scale=1000)
rounded('20 percent electricity ceiling', ceiling(c, d, .2), '18.3', scale=1000)
rounded('40 g headroom', paired(c, d, .04)['margin10_kg'], '19.3')
rounded('20 g shortfall for exact 20 percent', -paired(c, d, .02)['margin20_kg'], '4.5')

ordinary, clean = paired(c, d, .4), paired(c, d, .03)
rounded('conventional clean-power benefit', ordinary['baseline_kg'] - clean['baseline_kg'], '37.0')
rounded('basalt clean-power benefit', ordinary['new_kg'] - clean['new_kg'], '992.3')
from calculate import evaluate
old = deepcopy(core)
old['defaults']['kiln_saving_GJ_per_full_tcement'] = 0
fixed = evaluate(old, old['designs'][0], 1, .03)['new_kg']
rounded('separate fixed-inventory route', fixed, '764.5')
rounded('fixed 750 comparator increase', fixed / 750 - 1, '1.9', scale=100)
close('plagioclase Na-only lower bound at An0.65', 1 + (.35 / .65) / 2, 1.2692307692307692)

expected_counts = {'paired-scenarios.csv': 112, 'paired-thresholds.csv': 12,
    'coupled-stresses.csv': 10, 'supplementary-stresses.csv': 10,
    'paired-baseline-sensitivity.csv': 810, 'operating-envelope.csv': 75,
    'energy-attribution.csv': 4}
for name, n in expected_counts.items():
    with (R / 'results' / name).open() as f:
        rows = list(csv.DictReader(f))
    check('row count ' + name, len(rows) == n)
    for row in rows:
        for key in ['coproduct_credit_kg', 'carbon_removal_credit_kg', 'kiln_saving_kg']:
            if key in row:
                check('zero boundary ' + name + ' ' + key, float(row[key]) == 0)
    if name == 'paired-scenarios.csv':
        close('all 112 main rows close the carbon ledger',
              max(abs(float(z['baseline_kg']) - float(z['new_kg']) - float(z['net_saving_kg'])) for z in rows), 0)

# claim-map.json links exact values to the tables used by the paper.
for claim in json.loads((R / 'claim-map.json').read_text()):
    with (R / claim['source_file']).open() as f:
        rows = list(csv.DictReader(f))
    selected = [z for z in rows if all(
        math.isclose(float(z[k]), float(v), rel_tol=1e-12) if k != 'design' else z[k] == v
        for k, v in claim['where'].items())]
    check('claim map unique row ' + claim['display'], len(selected) == 1)
    for key, value in claim['values'].items():
        if key == 'design':
            check('claim map design', selected[0][key] == value)
        else:
            close('claim map ' + claim['display'] + ' ' + key, float(selected[0][key]), float(value))

report = {'status': 'PASS', 'checks': len(checks),
    'scope': 'Package integrity, all numeric table rows, worked equations, displayed results, target boundaries, data counts and deterministic replay; not experimental validation.',
    'main_30g': {'conventional_kg': B, 'basalt_kg': B - 456 + burden,
                 'reduction_percent': 100 * (456 - burden) / B},
    'named_checks': checks}
(R / 'results' / 'publication-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS', len(checks), 'publication checks; 38 paired checks; 30 recovery-model checks')
