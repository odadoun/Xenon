# Olivier Dadoun dadoun@in2p3.fr
# PMT Xenon display (only for TPC)
# Standalone PMT Bokeh display
# PMT position uses pmt_positions_xenonnt.csv file from straxen
# at the end class to convert rootfile into desired pandas
# December 2023
import numpy as np
from bokeh.io import curdoc, show
from bokeh.models import Circle, ColumnDataSource, Grid, LinearAxis, Plot
from bokeh.layouts import row, column, gridplot
from bokeh.plotting import figure, output_file, show
from bokeh.io import show, output_notebook
from bokeh.models import CustomJS, Slider
from bokeh.models.widgets import TextInput
from bokeh.models import Range1d
from bokeh.models import HoverTool, ColorBar, LinearColorMapper, BasicTicker, LogColorMapper, LogTicker,Ellipse
from bokeh.transform import transform
from bokeh.palettes import Spectral5, Viridis256
import copy
import pandas as pd
import uproot
output_notebook(hide_banner=True)
#curdoc().theme = 'dark_minimal'
class Display:
    def __init__(self,scale='Linear'):
        '''
            Init some variables
            define size of the bokeh figure
        '''
        self.scale = scale
        self.idPMT = []
        self.coloridPMT = 'black'
        self.position = self.positionPMT()

        self.Rpmt = 3*2.54/2 #3" diameter
        self.Rtpc = 66.2
        self.offset = 4*self.Rpmt

        self.abs_xmax = self.offset/2.+2*self.Rtpc+self.Rpmt
        self.abs_ymax = self.Rtpc+self.Rpmt

        self.width, self.height = 630, 300
        self.fig = figure(width = self.width, height = self.height,
                   x_range = [-self.abs_xmax,self.abs_xmax], y_range = [-self.abs_ymax,self.abs_ymax],
                   match_aspect=True)
        self.fig.axis.visible = False
        self.fig.grid.visible = False
        if scale not in ['Log','Linear']:
            print(" What do you mean exactly by " + scale + " ?")
        self.scale = scale
        self.colorbardrawn = False
        self.ticker = BasicTicker()
        self.draw_welding_line=False
        self.angle_weldingline=0


    def drawTPCradius(self):
        '''
            Draw circle of Rtpc radius which represent the TPC radius delimation
        '''
        #self.fig.circle(x = -self.Rtpc, y=0, color=None, radius=self.Rtpc, alpha=0.5,line_color='red',line_width=3,radius_dimension='max')
        #self.fig.circle(x = self.Rtpc, y=0, color=None, radius=self.Rtpc, alpha=0.5,line_color='red',line_width=3,radius_dimension='max')
        glyph = Ellipse(x=-self.abs_xmax/2., y=0, width=2*self.Rtpc, height=2*self.Rtpc, angle=0, fill_color=None,line_color='red',line_width=3)
        self.fig.add_glyph(glyph)
        glyph = Ellipse(x=self.abs_xmax/2., y=0, width=2*self.Rtpc, height=2*self.Rtpc, angle=0, fill_color=None,line_color='red',line_width=3)
        self.fig.add_glyph(glyph)
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
        if len(self.idPMT) !=0 :
            pmtpd.loc[pmtpd.PMTi.isin(self.idPMT),'color']='black'
        if self.coloridPMT != 'black' :
            pmtpd.loc[pmtpd.PMTi.isin(self.idPMT),'color']=self.coloridPMT
        return pmtpd

    def placePMT(self,pmtenum = None, position = 'topbottom',i = None, color = None):
        '''
            Place the PMT on the bokeh figure and the colormap associated
            xdisplayed is a meaningless variable - use only for the display
            return a bokeh figure and a ColumnDataSource (Bokeh format)
        '''
        self.drawTPCradius()
        pmttmp = self.positionPMT().set_index('PMTi')

        if position not in ['topbottom','top','bottom']:
            print(position, 'value not present in orignal csv pmt file, please have look !')
        else:
            if position != 'topbottom':
                pmttmp=pmttmp.loc[pmttmp.array==position]

        pmttmp['xdisplayed'] = pmttmp['x']
        if position == 'topbottom':
            pmttmp.loc[pmttmp.index<=252,'xdisplayed'] = pmttmp['xdisplayed']-self.abs_xmax/2.
            pmttmp.loc[pmttmp.index>252,'xdisplayed'] = pmttmp['xdisplayed']+self.abs_xmax/2.

        if position == 'bottom':
            pmttmp.loc[:,'xdisplayed'] = pmttmp['xdisplayed']+self.abs_xmax
        if position == 'top':
            pmttmp.loc[:,'xdisplayed'] = pmttmp['xdisplayed']-self.abs_xmax/2.
        if pmtenum is None:
             pmtenum  = pd.DataFrame()

        if not pmtenum.empty:
            if isinstance(pmtenum.hits[0], dict):
                # format index, i,j, {PM1:hits,PMT2:hits,...}
                ind=pmtenum.index.values[0]
                if 'xextra' and 'yextra' in pmtenum.columns:
                    x = pmtenum.xextra.values[0]
                    y = pmtenum.yextra.values[0]
                first = list(pmtenum.head(1)['hits'].values[0].items())
                #first = pmtenum.head(1)['hits'].values[0]
                pmtenum = pd.DataFrame(first,columns=['PMTi','hits'])
                pmtenum['positionij']=len(pmtenum)*[ind]
                if 'xextra' and 'yextra' in pmtenum.columns:
                    pmtenum['xextra'] = len(pmtenum)*[x]
                    pmtenum['yextra'] = len(pmtenum)*[y]
                pmttmp = pmttmp.drop(columns=['color'])
                pmttmp = pd.merge(pmttmp,pmtenum, on='PMTi')
            else:
                pmttmp = pmttmp.join(pmtenum)

        palette = Viridis256

        colormap = LinearColorMapper(palette = palette,low=0,high=50)
        if position == 'top':
            if self.scale=='Log':
                colormap = LogColorMapper(palette = palette ,low=1e-4,high=50)
                self.ticker = LogTicker()

        if 'hits' in pmttmp.columns:
            color = transform('hits', colormap)
        else:
            pmttmp['hits'] = -1 # by default no hits
            pmttmp['color'] = 'grey'
            if len(self.idPMT) !=0 :
                pmttmp.loc[pmttmp.index.isin(self.idPMT),'color']='black'
            if self.coloridPMT != 'black' :
                pmttmp.loc[pmttmp.index.isin(self.idPMT),'color']=self.coloridPMT
            color = 'color'

        colormap.low  = pmttmp.hits.min()
        colormap.high = pmttmp.hits.max()
        color_bar = ColorBar(color_mapper = colormap, label_standoff = 10, location = (0,0), ticker = self.ticker)

        src = ColumnDataSource(pmttmp)
        circ = self.fig.circle(x='xdisplayed', y='y', color = color, radius=self.Rpmt, alpha=1,source=src,line_color='black')#,radius_dimension='max')
        hover_tool = HoverTool(tooltips=[("PMT n°=", "$index"), ("(x, y)", "(@x, @y)"),("hits","@hits")],renderers=[circ])
        self.fig.add_tools(hover_tool)
        return src, color_bar

    def showPMT(self, pmtdico = None):
        '''
            Use for PMT location purpose
            Can take a Pandas as an input
            Here the callback is defined (JS stuff for HMTL slider interaction)
            return a bokeh figure
        '''
        color_bar = None
        if pmtdico:
            if isinstance(pmtdico, pd.DataFrame):
                draw = self.placePMT(pmtdico)
            else:
                '''
                if pmtdico is from placePMT so ntuple src, color_bar
                '''
                draw = pmtdico
                color_bar = draw[1]
        else:
            draw = self.placePMT()

        pmt_slider = Slider(start=0, end=self.position.PMTi.max(), value=1, step=1, title="PMT",name='sliderpmt')
        pmt_input = TextInput(value="", title="PMT n°:",name='textpmt')
        src = draw[0]

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
        if self.draw_welding_line:
            #set welding line invisible and reraw up to the PMT
            welding = self.fig.select_one({'name': 'weldingline'})
            welding.visible = False
            self.addweldingling(self.angle_weldingline)
        if color_bar:
            layout = self.fig
            self.fig.add_layout(color_bar, 'left')
        else:
            layout = column(self.fig,row(pmt_slider,pmt_input))
        show(layout)

    def updatePMT(self,pmtpd = None):
        '''
            Can take a Pandas as an input
            Columns are ['i', 'j', 'hits'] and the index is the PMT number
            Here the callback is defined (JS stuff for HMTL slider interaction)
            return a bokeh figure
        '''
        if pmtpd is None:
            show(self.fig)
        else:
            src = ColumnDataSource(pmtpd)

            pmtdisplayed = pmtpd.head(1)

            drawtop = self.placePMT(pmtdisplayed,'top')
            drawbottom = self.placePMT(pmtdisplayed,'bottom')

            layout = self.fig
            srcposition = ColumnDataSource()
            extra = 'notused'
            if 'xextra' and 'yextra' in pmtpd.columns:
                srcposition = ColumnDataSource(data={'xextra':[pmtdisplayed['xextra'].values[0]-self.Rtpc],\
                                                 'yextra':[pmtdisplayed['yextra'].values[0]]})
                self.fig.cross(x='xextra', y='yextra',size=20, color='red',source=srcposition,line_width=2)
                extra = 'extra'
            if pmtpd.index.min() != pmtpd.index.max():
                ind_slider = Slider(start=pmtpd.index.min(), end=pmtpd.index.max(), value=pmtpd.index.min(), step=1, title="i")
                thecallback = CustomJS(args=dict(source = src, sourcedis_top =  drawtop[0], sourcedis_bottom = drawbottom[0],
                ind = ind_slider, mappy_top = drawtop[1], mappy_bottom = drawbottom[1], srcpos = srcposition,
                cursorposition = extra, shiftcursor = self.Rtpc),
                code = """
                    var datain = source.data;
                    var hitsin = datain['hits'];
                    if(cursorposition === 'extra'){
                    var xin = datain['xextra'];
                    var yin = datain['yextra'];
                    }
                    var newhitstop = [];
                    var newpmtitop = [];
                    var dataouttop  = sourcedis_top.data;
                    newhitstop= dataouttop['hits'];
                    newpmtitop = dataouttop['PMTi'];
                    var lowtop = mappy_top.low;
                    var hightop = mappy_top.high;

                    var newhitsbottom =[];
                    var newpmtibottom = [];
                    var dataoutbottom  = sourcedis_bottom.data;
                    newhitsbottom= dataoutbottom['hits'];
                    newpmtibottom = dataoutbottom['PMTi'];
                    var lowbottom = mappy_bottom.low;
                    var highbottom = mappy_bottom.high;

                    var position_index = ind.value;
                    var dic_hits = hitsin[position_index-ind.start];

                    var pos = srcpos.data;
                    if(cursorposition === 'extra'){
                        var x = pos['xextra'];
                        var y = pos['yextra'];
                        x[0] = xin[position_index-ind.start]-shiftcursor;
                        y[0] = yin[position_index-ind.start];
                    }
                    for(var key in dic_hits) {
                        if(parseInt(key)<=252) newhitstop[key] = dic_hits[key];
                        else  newhitsbottom[key-253] = dic_hits[key];
                    }

                    mappy_top.color_mapper.low = Math.min.apply(Math,newhitstop);
                    mappy_top.color_mapper.high = Math.max.apply(Math,newhitstop);
                    mappy_bottom.color_mapper.low = Math.min.apply(Math,newhitsbottom);
                    mappy_bottom.color_mapper.high = Math.max.apply(Math,newhitsbottom);

                    sourcedis_top.change.emit();
                    sourcedis_bottom.change.emit();
                    srcpos.change.emit();
                """)
                ind_slider.js_on_change('value', thecallback)
                if not self.colorbardrawn: # avoid multiple colorbar
                    #self.fig.plot_width=650
                    #self.fig.plot_height=400
                    self.fig.add_layout(drawtop[1], 'left')
                    self.fig.add_layout(drawbottom[1], 'right')
                    self.colorbardrawn = True
                layout = column(self.fig,ind_slider)
            show(layout)

    def addweldingling(self, angle = 0.):
        if self.draw_welding_line :
            angle = angle*np.pi/180.
        x = self.Rtpc*np.cos(angle)
        y = self.Rtpc*np.sin(angle)
        self.draw_welding_line = True
        self.angle_weldingline = angle
        self.fig.segment(x0=[self.abs_xmax/2.,self.abs_xmax/2.], y0=[0,0],
                        x1=[self.abs_xmax/2.-x,self.abs_xmax/2.+x], y1=[-y,y], color="red", line_width=3,name='weldingline')

    def showPrecisePMT(self,id=[],color = None):
        self.idPMT = id
        if color:
            self.coloridPMT=color
        else:
            self.coloridPMT = 'black'


class RootParser:
    def __init__(self):
        pass

    @staticmethod
    def root2pandas(rootfile = None, norm = True):
        '''
            Convert rootfile from the mc Xenon Geant4 simulation
            into pandas output - variables can be added easely, see
            tree.keys() to display all the avalaible variable
        '''
        try:
            file = uproot.open(rootfile)
            tree = file["events"]
        except OSError:
            print("An existing root file must be specified !")

        mytree=tree.arrays(["pmthitID"],library='pd').sort_values(by='pmthitID').reset_index()
        mytree['hits']=mytree.groupby('pmthitID')['pmthitID'].transform('count')
        mytree=mytree[['pmthitID','hits']].drop_duplicates()
        mytree=mytree.set_index('pmthitID')
        nprimary = tree.num_entries
        index = pd.Index(range(494))
        mytree=mytree.reindex(index,fill_value=0)
        if norm:
            mytree['hits'] = mytree['hits']/nprimary
        return mytree
