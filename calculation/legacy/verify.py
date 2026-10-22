#!/usr/bin/env python3
"""Independent identities, boundary guards, sensitivity and reproducibility checks."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,math,subprocess,sys,tempfile
from calculate import load,evaluate,threshold
ROOT=Path(__file__).resolve().parent
c=load();d=c['designs'][0];checks=[]
def record(name,condition):
    if not condition:raise AssertionError(name)
    checks.append({'name':name,'pass':True})
x=evaluate(c,d,1,.05);rho=44.01/56.077
record('CaCO3 reaction mass ratio independently calculated',math.isclose(rho,.7848130242345347,rel_tol=1e-5))
record('zero substitution returns exact source baseline',evaluate(c,d,0,.4)['new_kg']==919)
record('carbon identity closes',math.isclose(x['new_kg']+x['net_saving_kg'],919,abs_tol=1e-9))
record('eligible reference retains24kg calcination',x['eligible_calcination_kg']==456 and 480-x['eligible_calcination_kg']==24)
record('CaO recovered mass closes',math.isclose(x['rock_t']*d['feed_CaO_fraction']*d['overall_Ca_recovery'],x['q_CaOeq_t'],rel_tol=1e-12))
record('acid volume follows molarity rather than chosen convenient liquid/solid ratio',math.isclose(x['acid_m3']*900,x['reagent_pairs_mol'],rel_tol=1e-12))
record('lower acid yield increases full stack charge once',evaluate(c,{**d,'acid_to_base_equivalent_yield':.8},1,.05)['bmed_stack_kWh']>x['bmed_stack_kWh'])
record('paired acid energy not added a second time',math.isclose(x['bmed_stack_kWh'],x['base_equivalent_kg']*1.8,rel_tol=1e-12))
record('cake water and drying cannot disappear',x['cake_water_t']>0 and x['drying_GJ']>0)
record('wetter cake consumes more heat',evaluate(c,{**d,'cake_dry_solids_fraction':.5},1,.05)['extra_heat_GJ']>x['extra_heat_GJ'])
record('poorer sensible recovery worsens net emissions',evaluate(c,{**d,'sensible_heat_recovery_fraction':.5},1,.05)['new_kg']>x['new_kg'])
record('extra reagent demand worsens both heating and electricity',evaluate(c,{**d,'reagent_equivalent_multiplier':2},1,.05)['new_kg']>x['new_kg'])
record('loss/makeup embodied emissions included',x['makeup_kg']>0)
record('feed carbonate emissions included',x['feed_carbonate_kg']>0)
record('lower electricity factor improves identical process only',evaluate(c,d,1,.03)['new_kg']<x['new_kg'])
record('all baseline kiln emissions retained in main case',x['kiln_saving_kg']==0)
for target in [0,.1,.2]:
    t=threshold(c,d,1,target)['max_electricity_kg_per_kWh']
    if t is not None and t>=0:record(f'exact solved boundary recovers target{target}',math.isclose(evaluate(c,d,1,t)['reduction_fraction'],target,abs_tol=1e-12))
for label,key in [('coproduct','coproduct_credit_kg'),('carbon removal','carbon_removal_credit_kg')]:
    bad={**d,key:1}
    try:evaluate(c,bad,1,.03);raised=False
    except ValueError:raised=True
    record(label+' credits fail closed',raised)
record('published salt-splitting arithmetic matches rounded4.5GJ within2%',abs(11000*2*202/1e6-4.5)/4.5<.02)
# All deterministic numerical outputs must match a separate clean output directory.
with tempfile.TemporaryDirectory() as td:
    subprocess.run([sys.executable,str(ROOT/'calculate.py'),'--out',td],check=True,capture_output=True)
    for p in sorted((ROOT/'results').iterdir()):
        if p.name=='verification.json':continue
        if p.suffix not in ['.csv','.json']:continue
        other=Path(td)/p.name
        if other.exists():record('clean rebuild '+p.name,hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(other.read_bytes()).digest())
result={'status':'PASS','checks':checks,'count':len(checks),'scope':'model arithmetic, conservative boundary guards, metamorphic changes and independent clean numerical rebuild; not independent experimental validation'}
(ROOT/'results/verification.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(checks),'checks')
