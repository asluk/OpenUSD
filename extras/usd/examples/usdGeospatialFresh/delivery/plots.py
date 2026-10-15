"""Scientific plots of executed results. No invented location or backdrop data."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'evidence';A=ROOT/'delivery/assets';A.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':13,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#283d48','text.color':'#162e3b','axes.edgecolor':'#9baab2','figure.facecolor':'#f5f8fa','axes.facecolor':'#f5f8fa','savefig.facecolor':'#f5f8fa'})
survey=json.loads((E/'survey-controls.json').read_text());fig,ax=plt.subplots(figsize=(10,5.1))
names=['France geographic to geocentric','France CC49 to Lambert-93','Colorado to calibrated site grid']
y=np.arange(3);ax.barh(y-.15,[r['max_control_error_m']*1000 for r in survey],height=.28,color='#147d92',label='Python');ax.barh(y+.15,[r['native_all_control_error_m']*1000 for r in survey],height=.28,color='#85b647',label='C++');ax.set_yticks(y,names);ax.invert_yaxis();ax.set_xlabel('Largest distance from supplied control coordinates (mm)');ax.set_xlim(0,.13);ax.legend(frameon=False,loc='lower right');fig.tight_layout();fig.savefig(A/'survey-error.png',dpi=180);plt.close(fig)

data=json.loads((E/'Climate-resolved.json').read_text())['samples'];first=[r for r in data if r['index'][0]==0]
p=np.array([r['resolved_coordinates'] for r in first]).reshape(37,72,3)/1e6
temperature=np.array([r['value'] for r in first]).reshape(37,72)
fig=plt.figure(figsize=(10,7));ax=fig.add_subplot(111,projection='3d');ax.plot_surface(p[:,:,0],p[:,:,1],p[:,:,2],facecolors=plt.cm.magma(Normalize(temperature.min(),temperature.max())(temperature)),rstride=1,cstride=1,shade=False,antialiased=True)
ax.set_box_aspect((1,1,1));ax.view_init(20,-45);ax.set_axis_off();fig.colorbar(plt.cm.ScalarMappable(norm=Normalize(temperature.min(),temperature.max()),cmap='magma'),ax=ax,shrink=.58,pad=.01,label='Source temperature values (K)');fig.tight_layout(pad=0);fig.savefig(A/'global-climate.png',dpi=180,bbox_inches='tight');plt.close(fig)

data=json.loads((E/'Railway-resolved.json').read_text())['samples'];coords=np.array([r['resolved_coordinates'] for r in data]);native=np.array([r['coordinates'] for r in data]);lon,lat=np.radians(native[0,:2]);basis=np.array([[-np.sin(lon),np.cos(lon),0],[-np.sin(lat)*np.cos(lon),-np.sin(lat)*np.sin(lon),np.cos(lat)],[np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)]])
local=(coords-coords[0])@basis.T
fig,ax=plt.subplots(figsize=(10,5.7));scatter=ax.scatter(local[:,0],local[:,1],c=native[:,2],s=9,cmap='viridis',zorder=2)
from collections import defaultdict
segments=defaultdict(list)
for i,row in enumerate(data):segments[tuple(row['index'][:-1])].append(i)
for indexes in segments.values():
    line=local[indexes];ax.plot(line[:,0],line[:,1],c='#466e78',lw=.5,zorder=1)
ax.set_aspect('equal');ax.set_xlabel('East displacement in display ENU (m)');ax.set_ylabel('North displacement (m)');fig.colorbar(scatter,ax=ax,label='Source height component (m)');fig.tight_layout();fig.savefig(A/'railway.png',dpi=180);plt.close(fig)

# Independent analytic counterexample, not an implementation-generated oracle.
theta=np.linspace(-1,1,201)*np.pi/180;radius=6378137.;x=radius*np.cos(theta);y=radius*np.sin(theta)
fig,ax=plt.subplots(figsize=(10,4.5));ax.plot(y/1000,x-radius,label='Interpolate longitude, then resolve',c='#147d92',lw=3);ax.plot([y[0]/1000,y[-1]/1000],[x[0]-radius,x[-1]-radius],label='Interpolate resolved ECEF endpoints',c='#ba5c35',lw=3);ax.scatter([0],[0],c='#147d92',s=65);ax.text(0,-450,'971.4 m midpoint difference',ha='center',fontsize=13);ax.set_xlabel('Geocentric Y (km)');ax.set_ylabel('Geocentric X minus Earth radius (m)');ax.legend(frameon=False,loc='lower center',bbox_to_anchor=(.5,1.01));fig.tight_layout();fig.savefig(A/'interpolation.png',dpi=180);plt.close(fig)
print('Created scientific plots from measured results and the analytic interpolation control')
