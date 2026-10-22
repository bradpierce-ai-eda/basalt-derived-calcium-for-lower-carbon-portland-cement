"""Scientific figures from the paired model; authored SVG and PNG, no network."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch,Rectangle
from calculate_paired import load,paired
R=Path(__file__).resolve().parent;F=R/'figures';F.mkdir(exist_ok=True)
c=load();d=c['designs'][0]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'basalt-v1.1','savefig.facecolor':'white'})
def save(fig,name):
 fig.savefig(F/(name+'.svg'),bbox_inches='tight',metadata={'Date':None})
 fig.savefig(F/(name+'.png'),dpi=300,bbox_inches='tight');plt.close(fig)

fig=plt.figure(figsize=(8,5.5));gs=fig.add_gridspec(2,1,height_ratios=[1,1.1],hspace=.32)
a=fig.add_subplot(gs[0]);a.set(xlim=(0,1),ylim=(0,1));a.axis('off')
a.text(0,1.02,'A  One circuit must meet the coupled requirements',weight='bold')
a.add_patch(Rectangle((0,.04),1,.91,facecolor='#f5f7f8',edgecolor='#aab5ba'))
def box(x,y,w,h,s):
 a.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=.009',facecolor='white',edgecolor='#24596a'));a.text(x,y,s,ha='center',va='center',fontsize=9)
def arrow(p,q):a.add_patch(FancyArrowPatch(p,q,arrowstyle='-|>',mutation_scale=11,color='#24596a'))
for x,s in zip([.12,.37,.63,.88],['Assay and\nprepare basalt','Selectively dissolve\nand separate','Recover qualified\ncalcium precursor','Make and\nqualify cement']):box(x,.73,.20,.26,s)
for x in [.23,.48,.74]:arrow((x,.73),(x+.025,.73))
box(.36,.25,.25,.23,'Regenerate acid/base\nwith real recycle liquor');arrow((.36,.59),(.36,.38));arrow((.40,.38),(.40,.59))
box(.75,.25,.37,.23,'Count heat, wash, purge, makeup,\nwater and all residual solids');arrow((.63,.59),(.72,.38));arrow((.50,.25),(.55,.25))
a.text(.10,.30,'Internal\nrecycle',ha='center',fontsize=8)
b=fig.add_subplot(gs[1]);x=paired(c,d,.03)
terms=[('Remaining carbonate', [480,24],'#777777',''),('Shared plant inventory',[x['baseline_kg']-480,x['baseline_kg']-480],'#c5d2d7','//'),('Added recovery',[0,x['P_kg']],'#d89940','..')]
left=np.zeros(2)
for label,v,col,hat in terms:b.barh([1,0],v,left=left,color=col,hatch=hat,edgecolor='#444444',linewidth=.5,label=label);left+=v
b.set(yticks=[1,0],yticklabels=['Conventional','Basalt target'],xlabel='Total emissions (kg CO₂e/t equivalent cement)',xlim=(0,840),ylim=(-.6,1.9))
b.text(0,1.07,'B  Same supply: 456 kg avoided pays for 335 kg recovery',transform=b.transAxes,weight='bold')
for y,val in zip([1,0],left):b.text(val+8,y,f'{val:.1f}',va='center',fontsize=10)
b.legend(ncols=3,fontsize=8,loc='upper left',frameon=False);b.grid(axis='x',alpha=.12)
b.text(.01,-.37,'30 g/kWh; λ=1.30; credits=0; shared kiln demand held equal',transform=b.transAxes,fontsize=9)
save(fig,'figure1_chain_budget')

fig,axs=plt.subplots(2,1,figsize=(8,6.3),gridspec_kw={'height_ratios':[1,1.1],'hspace':.65})
ci=np.linspace(0,.10,161);lam=np.linspace(1.1,1.8,100)
z=np.array([[100*paired(c,{'id':'envelope','reagent_equivalent_multiplier':float(v)},float(e))['reduction_fraction'] for e in ci] for v in lam])
a=axs[0];m=a.contourf(ci*1000,lam,z,levels=np.arange(-30,36,5),cmap='RdYlBu',extend='both');cs=a.contour(ci*1000,lam,z,levels=[0,10,20],colors=['#333333']*3,linestyles=[':', '--','-'],linewidths=1)
a.clabel(cs,fmt={0:'0%',10:'10%',20:'20%'},fontsize=9);a.plot(30,1.3,'kx',ms=7,mew=2);a.annotate('Selected target',(30,1.3),(55,1.60),fontsize=9,bbox={'facecolor':'white','edgecolor':'none','alpha':.85},arrowprops={'arrowstyle':'->'})
a.set(xlabel='Delivered electricity lifecycle intensity (g CO₂e/kWh)',ylabel='Reagent multiplier λ',title='A  Target boundaries depend on selectivity and power')
fig.colorbar(m,ax=a,pad=.02,label='Total emissions reduction (%)')
b=axs[1];specs=[('Selective target',{},0,'#007989','-'),('Recovery/selectivity penalty',c['coupled_stresses'][0]['design'],0,'#b77500','--'),('Heat/water penalty',c['coupled_stresses'][1]['design'],100,'#795a9a','-.'),('Combined penalties',c['coupled_stresses'][2]['design'],100,'#b14445',':')]
for label,over,extra,col,ls in specs:b.plot(ci*1000,[100*paired(c,{'id':'line',**over},float(e),extra_power=extra)['reduction_fraction'] for e in ci],color=col,ls=ls,lw=2,label=label)
b.axhspan(10,20,color='#dedede',alpha=.45);b.axhline(0,color='#444444',lw=.7);b.axhline(10,color='#777777',ls='--',lw=.7);b.axhline(20,color='#777777',ls='--',lw=.7)
b.set(xlim=(0,100),ylim=(-20,30),xlabel='Delivered electricity lifecycle intensity (g CO₂e/kWh)',ylabel='Total emissions reduction (%)',title='B  Combined penalties can defeat the development target');b.grid(alpha=.12);b.legend(ncols=2,fontsize=8,frameon=False,loc='upper left',bbox_to_anchor=(0,-.42))
save(fig,'figure2_survival_region')

fig,ax=plt.subplots(figsize=(8,4.4));cases=[(d,.03,{},'Selective\n30 g'),(d,.05,{},'Selective\n50 g'),(c['coupled_stresses'][0]['design'],.03,{},'Recovery/\nselectivity'),(c['coupled_stresses'][2]['design'],.03,{'extra_power':100},'Combined\npenalties'),(c['coupled_stresses'][4]['design'],.03,{},'Broad\nextraction')]
rows=[paired(c,{'id':str(i),**dd},e,**kw) for i,(dd,e,kw,label) in enumerate(cases)]
bottom=np.zeros(5)
for key,label,col,hat in [('electricity_kg','Electricity','#398da5',''),('heat_kg','Heat/drying','#d5a143','//'),('makeup_kg','Paired makeup','#8c76ad','..'),('other_kg','Other recovery','#8aa17a','xx'),('feed_carbonate_kg','Feed carbonates','#b47878','\\'),('fixed_kg','Fixed increment','#bbbbbb','++')]:
 vals=np.array([v[key] for v in rows]);
 ax.bar(range(5),vals,bottom=bottom,color=col,hatch=hat,edgecolor='#444444',linewidth=.35,label=label);bottom+=vals
ax.axhline(456,color='#333333',lw=1.2,ls='--',label='Avoided carbonate CO₂')
for i,v in enumerate(rows):ax.text(i,bottom[i]+12,f"{100*v['reduction_fraction']:+.1f}%",ha='center',fontsize=9)
ax.set(xticks=range(5),xticklabels=[x[3] for x in cases],ylim=(0,1030),ylabel='Added recovery emissions (kg CO₂e/t cement)');ax.legend(ncols=2,frameon=False,fontsize=8,loc='upper left');ax.grid(axis='y',alpha=.12)
save(fig,'figureS1_burdens')

fig,ax=plt.subplots(figsize=(8,4));ff=np.r_[0,np.linspace(.001,1,150)]
for ci,col,ls in [(.02,'#00634f','-'),(.03,'#007d87','--'),(.04,'#a76c00','-.'),(.05,'#b33c49',':')]:ax.plot(ff*100,[100*paired(c,d,ci,float(f))['reduction_fraction'] for f in ff],color=col,ls=ls,lw=2,label=f'{ci*1000:.0f} g/kWh')
ax.axhspan(10,20,color='#dedede',alpha=.4);ax.axhline(0,color='#444444',lw=.8);ax.axhline(10,color='#777777',ls='--',lw=.8);ax.set(xlim=(0,100),ylim=(-3,22),xlabel='Eligible carbonate-calcium replacement (%)',ylabel='Total emissions reduction (%)');ax.legend(frameon=False,ncols=2,fontsize=9);ax.grid(alpha=.12)
save(fig,'figureS2_partial_replacement')
alts={'figure1_chain_budget': 'Recovery, reagent recycle, purge and qualified cement form one coupled circuit. The paired bars share the same conventional plant inventory. At 30 g/kWh and reagent multiplier 1.30, conventional emissions are 756.9 and selected basalt emissions 636.0 kg per tonne: 456 kg avoided carbonate emissions pay for 335.1 kg added recovery emissions, leaving 120.9 kg net savings.', 'figure2_survival_region': 'A contour plot shows 10 and 20 percent reduction boundaries narrowing as reagent demand or electricity intensity rises. The selected multiplier 1.30 gives 10 percent only below 47.4 g/kWh and 20 percent below 18.3 g/kWh. A second plot shows recovery/selectivity and heat/water penalties separately and combined; the combination can erase the development target. Lines and text duplicate color meaning.', 'figureS1_burdens': 'Patterned stacked bars separate recovery electricity, heat, paired makeup, other operations, feed carbonates and fixed burdens. The main target at 30 g/kWh stays below 456 kg avoided emissions; combined penalties and broad extraction consume or exceed the available margin. Percentage labels use paired conventional inventories.', 'figureS2_partial_replacement': 'Four distinct line styles show increasing percentage reduction with more calcium replacement at 20, 30, 40 and 50 g/kWh. A fixed active-process charge causes an initial penalty. Full replacement reaches 19.4, 16.0, 12.5 and 9.1 percent respectively; shading marks the 10 to 20 percent development target.'}
(R/'figure-alt-text.json').write_text(json.dumps(alts,indent=2)+'\n')
print('Built four paired scientific figures as SVG and PNG')
