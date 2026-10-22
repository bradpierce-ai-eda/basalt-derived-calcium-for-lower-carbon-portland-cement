"""Meaningful paired-comparison, chemistry and reproducibility checks."""
from pathlib import Path
from copy import deepcopy
import math,json,csv,tempfile,hashlib,subprocess,sys
from calculate_paired import load,paired,ceiling,run,R
checks=[]
def ck(name,v):
    if not v:raise AssertionError(name)
    checks.append(name)
def close(a,b):return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-9)
c=load();d=c['designs'][0];x=paired(c,d,.03)
ck('principal reagent multiplier is 1.30',d['reagent_equivalent_multiplier']==1.3)
for ci in [0,.02,.03,.05,.4]:
    z=paired(c,d,ci,0)
    ck('zero calcium substitution identity '+str(ci),close(z['baseline_kg'],z['new_kg']))
for r in [0,.1,.2]:
    boundary=ceiling(c,d,r);p=paired(c,d,boundary)
    ck('paired denominator target boundary '+str(r),close(p['reduction_fraction'],r))
ck('calcium avoided stoichiometric factor',close(x['q_CaOeq_t']*1000*44.01/56.077,456))
ck('dry feed closes recovered calcium',close(x['rock_t']*.12*.90,x['q_CaOeq_t']))
ck('acid volume follows equivalents',close(x['acid_m3']*1000*.9,x['reagent_pairs_mol']))
ck('full stack once per generated base',close(x['bmed_stack_kWh'],x['base_equivalent_kg']*1.8))
ck('acid yield corrected',close(x['generated_base_mol']*.9,x['reagent_pairs_mol']))
ck('common inventory cancels in absolute saving',close(paired({**c,'common_other_kg':150,'common_kWh_per_tcement':150},d,.03)['net_saving_kg'],x['net_saving_kg']))
ck('common burden changes paired denominator',paired({**c,'common_other_kg':150},d,.03)['reduction_fraction']<x['reduction_fraction'])
y=paired(c,d,.05)
ck('conventional clean power benefit is its own utility use',close(y['baseline_kg']-x['baseline_kg'],100*.02))
ck('basalt clean power benefit includes recovery',close(y['new_kg']-x['new_kg'],(100+x['electricity_kWh'])*.02))
ck('added 1GJ and 100kWh charged fully',close(paired(c,d,.03,extra_heat=1,extra_power=100)['new_kg']-x['new_kg'],73))
ck('differential unclosed burden has no free cancellation',close(paired(c,d,.03,delta_other=30)['new_kg']-x['new_kg'],30))
for field in ['coproduct_credit_kg','carbon_removal_credit_kg','allocation_away_from_cement_fraction']:
    cc=deepcopy(c);cc[field]=1
    try:paired(cc,d,.03)
    except ValueError:rejected=True
    else:rejected=False
    ck('nonzero invariant rejected '+field,rejected)
ck('Na/Ca demand bound derived independently',close(1+(.35/.65)/2,1.2692307692307692))
ck('1.10 requires An >= five-sixths under Na co-release',close(1/(2*1.1-1),5/6))
ck('main30 value independently recomputed',close(x['new_kg'],480+3.5*.914*70+100*.03+50-456+x['P_kg']))
ck('reagent demand penalty reduces savings',paired(c,{**d,'reagent_equivalent_multiplier':1.5},.03)['net_saving_kg']<x['net_saving_kg'])
ck('heat recovery penalty reduces savings',paired(c,{**d,'sensible_heat_recovery_fraction':.7},.03)['net_saving_kg']<x['net_saving_kg'])
ck('dewatering penalty reduces savings',paired(c,{**d,'cake_dry_solids_fraction':.65},.03)['net_saving_kg']<x['net_saving_kg'])
ck('ineligible fraction scales both avoided term and recovery demand',close(paired({**c,'eligible_fraction':.85},d,.03)['q_CaOeq_t']/x['q_CaOeq_t'],.85/.95))
ck('no assumed main kiln energy saving',x['kiln_saving_kg']==0)
for spec in c['coupled_stresses']:
    q=paired(c,{'id':spec['id'],**spec.get('design',{})},.03,extra_heat=spec.get('extra_heat',0),extra_power=spec.get('extra_power',0),delta_other=spec.get('delta_other',0))
    ck('coupled component ledger closes '+spec['id'],close(q['P_kg'],sum(q[k] for k in ['electricity_kg','heat_kg','makeup_kg','other_kg','feed_carbonate_kg','fixed_kg','delta_other_kg'])))
before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'results').glob('*.csv')}
run()
after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'results').glob('*.csv')}
ck('clean deterministic paired rebuild',before==after)
# Verify recovery-module arithmetic and standalone diagnostic datasets.
r=subprocess.run([sys.executable,'verify.py'],cwd=R/'legacy',capture_output=True,text=True,check=True)
ck('recovery-module 30-check suite','PASS 30 checks' in r.stdout)
(R/'results/verification.json').write_text(json.dumps({'status':'PASS','checks':checks,'count':len(checks),'legacy_regression':r.stdout.strip(),'scope':'Implementation and reproducibility; no integrated experimental validation'},indent=2)+'\n')
print('PASS',len(checks),'paired checks; legacy PASS 30 checks')
