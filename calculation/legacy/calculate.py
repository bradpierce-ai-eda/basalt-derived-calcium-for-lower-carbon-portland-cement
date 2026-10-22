#!/usr/bin/env python3
"""Deterministic standard-library carbon-budget screening. No network required."""
from pathlib import Path
from copy import deepcopy
import argparse,csv,hashlib,itertools,json,math
ROOT=Path(__file__).resolve().parent

def load(path=ROOT/'inputs.json'):
    c=json.loads(Path(path).read_text());
    for key in ['coproduct_credit_kg','carbon_removal_credit_kg','allocation_away_from_cement_fraction']:
        if c[key]!=0:raise ValueError('Principal case prohibits '+key)
    if not 0<c['reference']['eligible_calcination_fraction']<=1:raise ValueError('eligible calcination fraction')
    for d in c['designs']:
        if d.get('coproduct_credit_kg',0)!=0 or d.get('carbon_removal_credit_kg',0)!=0:raise ValueError('Credits prohibited')
    return c

def evaluate(c,design,f,ci):
    d={**c['defaults'],**design};k=c['constants'];r=c['reference']
    for x in ['coproduct_credit_kg','carbon_removal_credit_kg']:
        if d[x]!=0:raise ValueError('Credits prohibited')
    if not 0<=f<=1 or ci<0:raise ValueError('fraction/intensity outside domain')
    for x in ['feed_CaO_fraction','overall_Ca_recovery','cake_dry_solids_fraction','dryer_efficiency']:
        if not 0<d[x]<=1:raise ValueError(x)
    if not 0<=d['sensible_heat_recovery_fraction']<1:raise ValueError('heat recovery')
    if not 0<=d['makeup_loss_fraction']<=1:raise ValueError('makeup loss')
    if min(d['acid_M'],d['base_M'])<=0 or d['reagent_equivalent_multiplier']<1:raise ValueError('reagent specification')
    if not 0<d['acid_to_base_equivalent_yield']<=1:raise ValueError('acid/base yield')
    if d['stack_auxiliary_multiplier']<1:raise ValueError('auxiliary multiplier')
    rho=k['molar_CO2_g']/k['molar_CaO_g']
    D=r['calcination_kg_per_tcement']*r['eligible_calcination_fraction']
    q_t=D/1000/rho
    ca_t=f*q_t;rock_t=ca_t/(d['feed_CaO_fraction']*d['overall_Ca_recovery'])
    ca_mol=ca_t*1e6/k['molar_CaO_g'];eq=2*ca_mol*d['reagent_equivalent_multiplier']
    base_generated_eq=eq/d['acid_to_base_equivalent_yield']
    base_kg=base_generated_eq*k['molar_NaOH_g']/1000
    # Full stack electricity is charged ONCE; paired acid is not a coproduct credit.
    bmed_stack=base_kg*d['bmed_kWh_per_kgNaOH']
    bmed_aux=bmed_stack*(d['stack_auxiliary_multiplier']-1)
    mill=rock_t*d['grinding_kWh_per_trock'];process_aux=f*d['process_aux_kWh_per_full_tcement']
    electricity=bmed_stack+bmed_aux+mill+process_aux
    # Volume follows stoichiometric reagent demand AND concentration: 1M=1000mol/m3.
    acid_m3=eq/(1000*d['acid_M']);base_m3=base_generated_eq/(1000*d['base_M'])
    heated_solution_t=acid_m3+d['heated_base_fraction']*base_m3 # density~1 selected approximation
    gross_sensible=(heated_solution_t*k['water_cp_MJ_per_t_K']+rock_t*k['rock_cp_MJ_per_t_K'])*d['leach_deltaT_K']/1000
    sensible=gross_sensible*(1-d['sensible_heat_recovery_fraction'])
    hydroxide_t=ca_t*k['molar_CaOH2_g']/k['molar_CaO_g']
    cake_water_t=hydroxide_t*(1/d['cake_dry_solids_fraction']-1)
    dryer=cake_water_t*k['evaporation_MJ_per_kg']/d['dryer_efficiency'] # t*MJ/kg = GJ
    extra_heat=(sensible+dryer)*d['heat_loss_multiplier']
    makeup=base_kg*d['makeup_loss_fraction']*d['makeup_pair_kgCO2e_per_kgNaOH_equiv']
    other=rock_t*d['other_burden_kgCO2e_per_trock']
    feed_carbonate=rock_t*d['feed_carbonate_CO2_kg_per_trock']
    fixed=d['fixed_increment_kgCO2e_per_active_tcement'] if f>0 else 0
    kiln_saved=f*d['kiln_saving_GJ_per_full_tcement']*d['heat_kgCO2e_per_GJ_delivered']
    electricity_em=electricity*ci;heat_em=extra_heat*d['heat_kgCO2e_per_GJ_delivered']
    nonelectric=heat_em+makeup+other+feed_carbonate+fixed-kiln_saved
    P=electricity_em+nonelectric;avoided=f*D;net=avoided-P;B=r['gwp_kg_per_tcement']
    return dict(design=d['id'],replacement_fraction=f,electricity_kg_per_kWh=ci,baseline_kg=B,eligible_calcination_kg=D,q_CaOeq_t=q_t,rock_t=rock_t,reagent_pairs_mol=eq,generated_base_mol=base_generated_eq,base_equivalent_kg=base_kg,acid_m3=acid_m3,base_m3=base_m3,acid_L_per_kgrock=acid_m3/rock_t if rock_t else 0,bmed_stack_kWh=bmed_stack,bmed_aux_kWh=bmed_aux,grinding_kWh=mill,process_aux_kWh=process_aux,electricity_kWh=electricity,gross_sensible_GJ=gross_sensible,net_sensible_GJ=sensible,cake_water_t=cake_water_t,drying_GJ=dryer,extra_heat_GJ=extra_heat,electricity_kg=electricity_em,heat_kg=heat_em,makeup_kg=makeup,other_kg=other,feed_carbonate_kg=feed_carbonate,fixed_kg=fixed,kiln_saving_kg=kiln_saved,non_electric_kg=nonelectric,P_kg=P,avoided_kg=avoided,net_saving_kg=net,new_kg=B-net,reduction_fraction=net/B,coproduct_credit_kg=0,carbon_removal_credit_kg=0)

def threshold(c,d,f,target):
    x=evaluate(c,d,f,0)
    allowance=x['avoided_kg']-target*x['baseline_kg']
    threshold=(allowance-x['non_electric_kg'])/x['electricity_kWh'] if x['electricity_kWh'] else None
    return dict(design=d['id'],replacement_fraction=f,target_fraction=target,net_processing_allowance_kg=allowance,non_electric_kg=x['non_electric_kg'],max_electricity_kg_per_kWh=threshold,feasible_at_nonnegative_electricity=threshold is not None and threshold>=0)

def write_csv(p,rows):
    with p.open('w',newline='') as s:
        w=csv.DictWriter(s,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def run(c,out):
    out.mkdir(parents=True,exist_ok=True)
    scenarios=[evaluate(c,d,f,ci) for d,f,ci in itertools.product(c['designs'],c['replacement_fractions'],c['electricity_kg_per_kWh'])]
    limits=[threshold(c,d,f,t) for d,f,t in itertools.product(c['designs'],[.25,.5,.75,1],c['targets'])]
    write_csv(out/'scenarios.csv',scenarios);write_csv(out/'thresholds.csv',limits)
    # A lower comparison footprint is applied to the SAME calculated new route.
    # Replacing B in both routes would silently improve the unmodelled retained plant.
    stricter=[]
    for x in scenarios:
        if x['replacement_fraction']!=1:continue
        for comparator in [919,822,750]:
            stricter.append(dict(design=x['design'],electricity_kg_per_kWh=x['electricity_kg_per_kWh'],fixed_new_route_kg=x['new_kg'],comparison_baseline_kg=comparator,reduction_fraction=1-x['new_kg']/comparator,classification='919 source reference;822 source product-class context not matched assay;750 selected counterfactual, no waste-fuel reallocation'))
    write_csv(out/'unchanged_route_comparator_stress.csv',stricter)
    # Separate modeled kiln sensitivity: source1.2GJ/tPC difference, scaled by clinker fraction.
    kiln=[]
    for d in c['designs'][:2]:
        alt={**d,'kiln_saving_GJ_per_full_tcement':1.2*c['reference']['clinker_mass_fraction']}
        for ci in c['electricity_kg_per_kWh']:
            x=evaluate(c,alt,1,ci);x['design']+='__modeled_kiln_saving';kiln.append(x)
    write_csv(out/'modeled_kiln_sensitivity.csv',kiln)
    # Deterministic joint stress grid: counts are coverage of selected combinations, NOT probabilities.
    joint=[]
    for grade,recovery,sec,equiv,hr,loss,ci in itertools.product([.08,.10,.12],[.7,.85,.95],[1.4,1.8,2.1,2.6],[1.1,1.25,1.6,4.0],[.5,.75,.85,.9],[.01,.02,.05],[.03,.05,.1,.2,.4]):
        d={**c['designs'][1],'feed_CaO_fraction':grade,'overall_Ca_recovery':recovery,'bmed_kWh_per_kgNaOH':sec,'reagent_equivalent_multiplier':equiv,'sensible_heat_recovery_fraction':hr,'makeup_loss_fraction':loss}
        x=evaluate(c,d,1,ci)
        joint.append(dict(feed_CaO_fraction=grade,overall_Ca_recovery=recovery,bmed_kWh_per_kgNaOH=sec,reagent_equivalent_multiplier=equiv,heat_recovery=hr,makeup_loss=loss,electricity_kg_per_kWh=ci,new_kg=x['new_kg'],reduction_fraction=x['reduction_fraction']))
    write_csv(out/'joint_sensitivity.csv',joint)
    # Focused one-at-a-time and bundled stresses against the integrated target.
    # Uninventoried utility additions are explicit increments, not free operations.
    focused=[]
    stress_specs=[
        ('reference',{}, {},0,0),
        ('eligible_calcination_85pct',{}, {'eligible_calcination_fraction':.85},0,0),
        ('makeup_pair_factor_5',{'makeup_pair_kgCO2e_per_kgNaOH_equiv':5},{},0,0),
        ('other_reserve_15',{'other_burden_kgCO2e_per_trock':15},{},0,0),
        ('other_reserve_25',{'other_burden_kgCO2e_per_trock':25},{},0,0),
        ('heat_factor_100',{'heat_kgCO2e_per_GJ_delivered':100},{},0,0),
        ('heat_recovery_70pct',{'sensible_heat_recovery_fraction':.70},{},0,0),
        ('cake_solids_65pct',{'cake_dry_solids_fraction':.65},{},0,0),
        ('unlisted_utilities_plus_1GJ_100kWh',{}, {},1,100),
        ('unlisted_utilities_plus_3GJ_300kWh',{}, {},3,300),
        ('bundled_practical_stress',{'makeup_pair_kgCO2e_per_kgNaOH_equiv':5,'other_burden_kgCO2e_per_trock':15,'sensible_heat_recovery_fraction':.75,'cake_dry_solids_fraction':.75}, {'eligible_calcination_fraction':.85},1,100)
    ]
    for label,overrides,ref_overrides,extra_GJ,extra_kWh in stress_specs:
        alt=deepcopy(c);alt['reference'].update(ref_overrides)
        for ci in [.02,.03,.05]:
            x=evaluate(alt,{**c['designs'][0],**overrides},1,ci)
            extra=extra_GJ*c['defaults']['heat_kgCO2e_per_GJ_delivered']+extra_kWh*ci
            focused.append(dict(stress=label,electricity_kg_per_kWh=ci,extra_heat_GJ=extra_GJ,extra_electricity_kWh=extra_kWh,added_unlisted_utility_kg=extra,new_kg=x['new_kg']+extra,reduction_fraction=1-(x['new_kg']+extra)/x['baseline_kg'],specification=json.dumps({'design_overrides':overrides,'reference_overrides':ref_overrides},sort_keys=True)))
    write_csv(out/'focused_stress.csv',focused)
    summary={'coproduct_credit_kg':0,'carbon_removal_credit_kg':0,'number_scenarios':len(scenarios),'number_joint_combinations':len(joint),'named_full_replacement_cases':[x for x in scenarios if x['replacement_fraction']==1], 'case_thresholds_full_replacement':[x for x in limits if x['replacement_fraction']==1], 'meaningful_target_definition':'10%,20%,30%,40% are chosen targets, not universal materiality standards','joint_counts_are_not_probabilities':True,'reference_calculation':'919kgCO2e and480kgcalcination from PCA2023 Table4;95%eligible fraction selected'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    # Reproduce a published arithmetic chain independently of the new model.
    fixture={'source':'Prancevic2026 feasibility/Table2; rounded source arithmetic','salt_splitting_GJ':11000*2*202/1e6,'plus_clinkering_GJ':11000*2*202/1e6+1.7,'table2_electricity_implied_grid_kg_per_kWh':551/(6.2/0.0036),'source_reported':{'regeneration_GJ':4.5,'total_GJ':6.2},'interpretation':'not used as new route full-boundary inventory or copied as measured plant data'}
    (out/'published_arithmetic_check.json').write_text(json.dumps(fixture,indent=2)+'\n')
    return scenarios,limits

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--inputs',type=Path,default=ROOT/'inputs.json');a.add_argument('--out',type=Path,default=ROOT/'results');args=a.parse_args();rows,_=run(load(args.inputs),args.out);print('Built',len(rows),'named cases; outputs in',args.out)
