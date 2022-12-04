# Olivier Dadoun dadoun@in2p3.fr
# PMT Xenon display (only for TPC)
# Standalone PMT Bokeh display
# pmt_positions_xenonnt.csv file from straxen
# December 2022
import numpy as np
from bokeh.io import curdoc, show
from bokeh.models import Circle, ColumnDataSource, Grid, LinearAxis, Plot
from bokeh.layouts import row, column, gridplot
from bokeh.plotting import figure, output_file, show
from bokeh.io import show, output_notebook
from bokeh.models import CustomJS, Slider
from bokeh.models.widgets import TextInput
from bokeh.models import Range1d
from bokeh.models import HoverTool, ColorBar, LinearColorMapper, BasicTicker, LogColorMapper, LogTicker
from bokeh.transform import transform
from bokeh.palettes import Spectral5, Viridis256
import copy
import pandas as pd
output_notebook(hide_banner=True)
#curdoc().theme = 'dark_minimal'
class Display:
    def __init__(self,scale='Linear'):
        '''
            Init some variables
            define size of the bokeh figure
        '''
        self.scale = scale
        self.position = self.positionPMT()
        offset = 10
        self.Rpmt = 3*2.54/2 #3" diameter
        mini,maxi = self.position.x.min()-self.Rpmt - offset,\
                    self.position.x.max()+self.Rpmt + offset
        self.Rtpc = 66.4
        self.PMTshiftupdown = 150
        self.width, self.height=600, 300
        self.fig = figure(width=self.width, height=self.height,
                   x_range=[mini,maxi+self.PMTshiftupdown],y_range=[mini,maxi],
                   match_aspect=True)
        self.fig.axis.visible = False
        self.fig.grid.visible = False
        self.colormap = LinearColorMapper(palette = 'Viridis256',low=0,high=50)
        if scale=='Log':
            self.colormap = LogColorMapper(palette = 'Viridis256',low=1e-4,high=50)
        if scale not in ['Log','Linear']:
            print(" What do you mean exactly by " + scale + " ?")
        self.colorbardrawn = False

    def drawTPCradius(self):
        '''
            Draw circle of Rtpc radius which represent the TPC radius delimation
        '''
        self.fig.circle(x=0, y=0, color=None,radius=self.Rtpc, alpha=0.5,line_color='red',line_width=3)
        self.fig.circle(x=self.PMTshiftupdown, y=0, color=None,radius=self.Rtpc, alpha=0.5,line_color='red',line_width=3)
        return self.fig

    def positionPMT(self):
        '''
            Just a csv parser, use local pmt_positions_xenonnt.csv
            Can use file from a web site
            Define a default PMT color
        '''
        pmtpd=pd.read_csv("pmt_positions_xenonnt.csv",header=1)
        pmtpd['color']='grey'
        pmtpd = pmtpd.rename(columns={'i':"PMTi"})
        return pmtpd

    def placePMT(self,pmtenum = None, i = None, color = None):
        '''
            Place the PMT on the bokeh figure
            xdisplayed is a meaningless variable - use only for the display
            return a bokeh figure and a ColumnDataSource (Bokeh format)
        '''
        self.drawTPCradius()
        pmttmp = self.positionPMT().set_index('PMTi')
        pmttmp['xdisplayed'] = pmttmp['x']
        pmttmp.loc[pmttmp.index>252,'xdisplayed'] = pmttmp['xdisplayed']+self.PMTshiftupdown
        if pmtenum is None:
             pmtenum  = pd.DataFrame()
        if not pmtenum.empty:
            # format index, i,j, {PM1:hits,PMT2:hits,...}
            ind=pmtenum.index.values[0]
            if 'xextra' and 'yextra' in pmtenum.columns:
                x = pmtenum.xextra.values[0]
                y = pmtenum.yextra.values[0]
            first = list(pmtenum.head(1)['hits'].values[0].items())
            if self.scale=='Log':
                first = list(({ k : (np.log10(v) if v != 0. else 2)\
                        for k,v in pmtenum.head(1)['hits'].values[0].items()}).items())
            pmtenum = pd.DataFrame(first,columns=['PMTi','hits'])
            pmtenum['positionij']=len(pmtenum)*[ind]
            if 'xextra' and 'yextra' in pmtenum.columns:
                pmtenum['xextra'] = len(pmtenum)*[x]
                pmtenum['yextra'] = len(pmtenum)*[y]
            self.colormap.low = pmtenum.hits.min()
            self.colormap.high = pmtenum.hits.max()

            pmttmp = pmttmp.drop(columns=['color'])
            pmttmp = pd.merge(pmttmp,pmtenum, on='PMTi')
        if 'hits' in pmttmp.columns:
            color = transform('hits', self.colormap)
        else:
            pmttmp['hits'] = -1 # by default no hits
            pmttmp['color'] = 'grey'
            color = 'color'
        src = ColumnDataSource(pmttmp)
        circ = self.fig.circle(x='xdisplayed', y='y', color = color, radius=self.Rpmt, alpha=1,source=src,line_color='black')
        hover_tool = HoverTool(tooltips=[("index", "$index"), ("(x, y)", "(@x, @y)"),("hits","@hits")],renderers=[circ])
        self.fig.add_tools(hover_tool)
        return src

    def showPMT(self, pmtdico = None):
        '''
            Use for PMT location purpose
            Can take a Pandas as an input
            Here the callback is defined (JS stuff for HMTL slider interaction)
            return a bokeh figure
        '''
        if pmtdico:
            draw = self.placePMT(pmtdico)
        else:
            draw = self.placePMT()
        pmt_slider = Slider(start=0, end=self.position.PMTi.max(), value=1, step=1, title="PMT",name='sliderpmt')
        pmt_input = TextInput(value="", title="PMT n°:",name='textpmt')
        src = draw
        thecallback = CustomJS(args=dict(source=src, slidervalue=pmt_slider,textvalue=pmt_input),
        code = """
            const data = source.data;
            if (cb_obj.name == 'sliderpmt'){
                textvalue.value = slidervalue.value.toString()
            }
            else if (cb_obj.name =='textpmt'){
                slidervalue.value = parseInt(textvalue.value)
            }
            const pmti = parseFloat(slidervalue.value);
            var col = data['color'];
            for (let i = 0; i < col.length; i++) {
                col[i] = 'grey';
            }
            col[pmti] = 'red';
            source.change.emit();
        """)
        pmt_slider.js_on_change('value', thecallback)
        pmt_input.js_on_change('value', thecallback)
        layout = column(self.fig,row(pmt_slider,pmt_input))
        show(layout)

    def updatePMT(self,pmtpd = None):
        '''
            Can take a Pandas as an input
            Columns are ['i', 'j', 'hits'] and the index is the PMT number
            Here the callback is defined (JS stuff for HMTL slider interaction)
            return a bokeh figure
        '''
        ticker = BasicTicker()
        if self.scale=='Log':
            ticker = LogTicker()
        color_bar = ColorBar(color_mapper = self.colormap, label_standoff = 14,\
                                location = (0,0), ticker = ticker)
        if pmtpd is None:
            show(self.fig)
        else:
            src = ColumnDataSource(pmtpd)
            pmtdisplayed = pmtpd.head(1)
            draw = self.placePMT(pmtdisplayed)
            srcdisplayed = draw
            layout = self.fig
            srcposition = ColumnDataSource()
            extra = 'notused'
            if 'xextra' and 'yextra' in pmtpd.columns:
                srcposition = ColumnDataSource(data={'xextra':[pmtdisplayed['xextra'].values[0]],\
                                                 'yextra':[pmtdisplayed['yextra'].values[0]]})
                self.fig.cross(x='xextra', y='yextra',size=20, color='red',source=srcposition,line_width=2)
                extra = 'extra'
            if pmtpd.index.min() != pmtpd.index.max():
                ind_slider = Slider(start=pmtpd.index.min(), end=pmtpd.index.max(), value=pmtpd.index.min(), step=1, title="i")
                thecallback = CustomJS(args=dict(source = src, sourcedis = srcdisplayed,
                ind = ind_slider, mappy = color_bar, srcpos = srcposition, cursorposition = extra, scale = self.scale),
                code = """
                    var datain = source.data;
                    var hitsin = datain['hits'];
                    if(cursorposition === 'extra'){
                    var xin = datain['xextra'];
                    var yin = datain['yextra'];
                    }
                    var newhits = [];
                    var newpmti = [];
                    var dataout  = sourcedis.data;
                    newhits = dataout['hits'];
                    newpmti = dataout['PMTi'];
                    var position_index = ind.value;
                    var dic_hits = hitsin[position_index-ind.start];
                    var low = mappy.low;
                    var high = mappy.high;

                    var pos = srcpos.data;
                    if(cursorposition === 'extra'){
                    var x = pos['xextra'];
                    var y = pos['yextra'];
                    x[0] = xin[position_index-ind.start];
                    y[0] = yin[position_index-ind.start];
                    }
                    for(var key in dic_hits) {
                     if(scale==='Log'){
                       if(dic_hits[key]<=0)
                        dic_hits[key]=1e-4;
                        newhits[key] = Math.log10(dic_hits[key]);
                      }
                      else  newhits[key] = dic_hits[key];
                    }
                    if(scale==='Linear'){
                    mappy.color_mapper.low = Math.min.apply(Math,newhits);
                    mappy.color_mapper.high = Math.max.apply(Math,newhits);
                    }
                    sourcedis.change.emit();
                    srcpos.change.emit();
                """)
                ind_slider.js_on_change('value', thecallback)
                if not self.colorbardrawn: # avoid multiple colorbar
                    self.fig.plot_width=700
                    self.fig.add_layout(color_bar, 'left')
                    self.colorbardrawn = True
                layout = column(self.fig,ind_slider)
            show(layout)
