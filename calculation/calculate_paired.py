"""Paired, zero-credit carbon screen. Python standard library; no network."""
from pathlib import Path
from copy import deepcopy
import csv, json, sys, itertools
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'legacy'))
from calculate import evaluate,load as legacy_load

def load():
    c=json.loads((R/'paired-inputs.json').read_text())
    for k in ['coproduct_credit_kg','carbon_removal_credit_kg','allocation_away_from_cement_fraction']:
        if c[k]!=0:raise ValueError('Credits/allocation prohibited: '+k)
    return c

def paired(c,design,ci,f=1,heat=None,u=None,extra_heat=0,extra_power=0,delta_other=0):
    for k in ['coproduct_credit_kg','carbon_removal_credit_kg','allocation_away_from_cement_fraction']:
        if c[k]!=0:raise ValueError('Credits/allocation prohibited: '+k)
    old=legacy_load(R/'legacy/inputs.json');old=deepcopy(old)
    old['reference']['calcination_kg_per_tcement']=c['calcination_kg']
    old['reference']['eligible_calcination_fraction']=c['eligible_fraction']
    old['defaults']['heat_kgCO2e_per_GJ_delivered']=c['recovery_heat_factor'] if heat is None else heat
    old['defaults']['kiln_saving_GJ_per_full_tcement']=0
    d={**old['designs'][0],**c['designs'][0],**design}; x=evaluate(old,d,f,ci)
    if not 0<=f<=1 or min(ci,extra_heat,extra_power,delta_other)<0:raise ValueError('domain')
    kh=c['kiln_heat_factor'] if heat is None else heat
    ph=old['defaults']['heat_kgCO2e_per_GJ_delivered']
    common_heat=c['kiln_GJ_per_tclinker']*c['clinker_fraction']
    common_power=c['common_kWh_per_tcement']
    U=c['common_other_kg'] if u is None else u
    B=c['calcination_kg']+common_heat*kh+common_power*ci+U
    P=x['P_kg']+extra_heat*ph+extra_power*ci+delta_other
    saving=x['avoided_kg']-P
    return {**x,'design':design.get('id','integrated'),'baseline_kg':B,'new_kg':B-saving,'reduction_fraction':saving/B,'net_saving_kg':saving,'P_kg':P,'shared_heat_GJ':common_heat,'shared_power_kWh':common_power,'common_other_kg':U,'kiln_heat_factor':kh,'recovery_heat_factor':ph,'extra_heat_GJ':x['extra_heat_GJ']+extra_heat,'electricity_kWh':x['electricity_kWh']+extra_power,'electricity_kg':x['electricity_kg']+extra_power*ci,'heat_kg':x['heat_kg']+extra_heat*ph,'delta_other_kg':delta_other,'margin10_kg':saving-.1*B,'margin20_kg':saving-.2*B,'calcium_source_effect_kg':saving}

def ceiling(c,design,target,f=1,**kw):
    x=paired(c,design,0,f,**kw)
    # B depends on common power as CI varies; solve against each paired denominator.
    return (x['avoided_kg']-x['P_kg']-target*x['baseline_kg'])/(x['electricity_kWh']+target*x['shared_power_kWh'])

def csvout(name,rows):
    with (R/'results'/name).open('w',newline='') as s:
        w=csv.DictWriter(s,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def run():
    c=load();(R/'results').mkdir(exist_ok=True)
    sc=[paired(c,d,ci,f) for d,ci,f in itertools.product(c['designs'],c['electricity_factors'],[0,.5,.75,1])]
    csvout('paired-scenarios.csv',sc)
    targets=[dict(design=d['id'],target_fraction=t,max_electricity_kg_per_kWh=ceiling(c,d,t)) for d,t in itertools.product(c['designs'],[0,.1,.2])]
    csvout('paired-thresholds.csv',targets)
    stresses=[]
    for s in c['coupled_stresses']:
        for ci in [.03,.05]:
            x=paired(c,{'id':s['id'],**s.get('design',{})},ci,extra_heat=s.get('extra_heat',0),extra_power=s.get('extra_power',0),delta_other=s.get('delta_other',0))
            stresses.append(x)
    csvout('coupled-stresses.csv',stresses)
    extra=[]
    for name,overrides,kwargs in [('lambda1.5',{'reagent_equivalent_multiplier':1.5},{}),('lambda1.6',{'reagent_equivalent_multiplier':1.6},{}),('heat_recovery70',{'sensible_heat_recovery_fraction':.7},{}),('cake65',{'cake_dry_solids_fraction':.65},{}),('heat_factor100',{}, {'heat':100})]:
        for ci in [.03,.05]:extra.append(paired(c,{'id':name,**overrides},ci,**kwargs))
    csvout('supplementary-stresses.csv',extra)
    sensitivity=[]
    for h,heat,w,u,eligible,ci in itertools.product([3.1,3.5,3.9],[50,70,100],[90,120,150],[0,50,100],[.85,.95],[.02,.03,.05,.10,.4]):
        q={**c,'kiln_GJ_per_tclinker':h,'common_kWh_per_tcement':w,'common_other_kg':u,'eligible_fraction':eligible}
        x=paired(q,c['designs'][0],ci,heat=heat)
        sensitivity.append(dict(kiln_GJ_per_tclinker=h,heat_factor=heat,common_kWh=w,common_other=u,eligible_fraction=eligible,ci=ci,baseline=x['baseline_kg'],new=x['new_kg'],reduction=x['reduction_fraction']))
    csvout('paired-baseline-sensitivity.csv',sensitivity)
    attrib=[]
    for ci in [.02,.03,.05,.4]:
        base=paired(c,c['designs'][0],.4)
        x=paired(c,c['designs'][0],ci)
        attrib.append(dict(ci=ci,conventional_kg=x['baseline_kg'],basalt_kg=x['new_kg'],same_supply_source_effect=x['net_saving_kg'],conventional_clean_power_effect=base['baseline_kg']-x['baseline_kg'],basalt_clean_power_effect=base['new_kg']-x['new_kg'],combined_difference_from_ordinary_conventional=base['baseline_kg']-x['new_kg']))
    csvout('energy-attribution.csv',attrib)
    boundaries=[]
    for lam,hr,ci in itertools.product([1.1,1.25,1.6,2,4],[.5,.7,.75,.85,.9],[.02,.03,.05]):
        x=paired(c,{'id':'operating_envelope','reagent_equivalent_multiplier':lam,'sensible_heat_recovery_fraction':hr},ci)
        boundaries.append(dict(lambda_value=lam,heat_recovery=hr,ci=ci,baseline=x['baseline_kg'],P=x['P_kg'],reduction=x['reduction_fraction'],margin10=x['margin10_kg'],margin20=x['margin20_kg']))
    csvout('operating-envelope.csv',boundaries)
    summary={'main30':paired(c,c['designs'][0],.03),'main50':paired(c,c['designs'][0],.05),'thresholds':targets,'coupled30':[x for x in stresses if x['electricity_kg_per_kWh']==.03],'counts':{'scenarios':len(sc),'baseline_sensitivity':len(sensitivity),'operating_envelope':len(boundaries)}}
    (R/'results/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary

if __name__=='__main__':
    s=run();print(json.dumps({k:s[k] for k in ['thresholds','counts']},indent=2))
