import numpy as np
from bokeh.io import curdoc, show
from bokeh.models import Circle, ColumnDataSource, Grid, LinearAxis, Plot
from bokeh.layouts import row, column, gridplot
from bokeh.plotting import figure, output_file, show
from bokeh.models import HoverTool
from bokeh.io import show, output_notebook
from bokeh.models import CustomJS, Slider
from bokeh.models.widgets import TextInput
from bokeh.models import Range1d
import copy
import pandas as pd
output_notebook(hide_banner=True)
#curdoc().theme = 'dark_minimal'
class Display:
    def __init__(self):
        self.position = self.positionPMT()
        offset = 10
        mini,maxi = self.position.x.min()-offset,self.position.x.max()+offset
        self.shiftupdown = 150
        self.fig = figure(width=600, height=400,x_range=[mini,maxi+self.shiftupdown],y_range=[mini,maxi])
        self.fig.axis.visible = False
        self.fig.grid.visible = False

    def positionPMT(self):
        #pmtpd = pd.DataFrame(columns=['i','array','x','y'])
        pmtpd=pd.read_csv("pmt_positions_xenonnt.csv",header=1)
        pmtpd['color']='grey'
        pmtpd = pmtpd.rename(columns={'i':"PMTi"})
        return pmtpd

    @staticmethod
    def irgb_string_from_irgb(irgb):
        '''Convert a displayable irgb color (0-255) into a hex string.'''
        if isinstance(irgb[0],float):
            irgb[0]=int(255*irgb[0])
            irgb[1]=int(255*irgb[1])
            irgb[2]=int(255*irgb[2])
        # ensure that values are in the range 0-255
        for index in range (0,3):
            irgb [index] = min (255, max (0, irgb [index]))
        # convert to hex string
        irgb_string = '#%02X%02X%02X' % (irgb[0], irgb[1], irgb[2])
        return irgb_string

    def placePMT(self,pmtenum = None,i=None,color=None):
        pmttmp = self.positionPMT().set_index('PMTi')
        pmttmp['xdisplayed'] = pmttmp['x']
        pmttmp.loc[pmttmp.index>252,'xdisplayed'] = pmttmp['xdisplayed']+self.shiftupdown
        if pmtenum is None:
             pmtenum  = pd.DataFrame()
        if not pmtenum.empty:
            # format index, i,j,{PM1:[r1,g1,b1],{PMT2:[r2,g2,b2]...}
            ind=pmtenum.index.values[0]
            pmtenum = pd.DataFrame(list(pmtenum.head(1)['color'].values[0].items()),columns=['PMTi','color'])
            pmtenum['positionij']=len(pmtenum)*[ind]
            pmttmp = pmttmp.drop(columns=['color'])
            pmttmp = pd.merge(pmttmp,pmtenum, on='PMTi')
        src = ColumnDataSource(pmttmp)
        circ = self.fig.circle(x='xdisplayed', y='y', color='color',size=10, alpha=0.5,source=src)
        hover_tool = HoverTool(tooltips=[("index", "$index"), ("(x, y)", "(@x, @y)")],renderers=[circ])
        self.fig.add_tools(hover_tool)
        return self.fig, src

    #def updatecolor(self,pd=None)
    def showPMT(self,pmtdico=None,i=None,color=None):
        if pmtdico:
            draw=self.placePMT(pmtdico)
        else:
            draw=self.placePMT()

        pmt_slider = Slider(start=0, end=self.position.PMTi.max(), value=1, step=1, title="PMT",name='sliderpmt')
        pmt_input = TextInput(value="", title="PMT n°:",name='textpmt')

        src=draw[1]
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

            var col = data['color']
            for (let i = 0; i < col.length; i++) {
                col[i] = 'grey'
            }
            col[pmti] = 'red';
            source.change.emit();
        """)
        pmt_slider.js_on_change('value', thecallback)
        pmt_input.js_on_change('value', thecallback)
        layout = column(draw[0],row(pmt_slider,pmt_input))
        show(layout)

    @staticmethod
    def retrieveij(strhistname):
        strhistname=strhistname.replace(';1','')
        strhistname=strhistname.replace('hist','')
        i=strhistname[:strhistname.find('_')]
        j=strhistname[strhistname.find('_')+1:]
        return i,j

    def updatePMT(self,pmtpd=None,i=None,j=None,color=None):
        if pmtpd is None:
            show(self.fig)
        else:
            src = ColumnDataSource(pmtpd)

            pmtdisplayed = pmtpd.head(1)
            draw = self.placePMT(pmtdisplayed)
            srcdisplayed = draw[1]
            layout = draw[0]
            if pmtpd.index.min() != pmtpd.index.max():
                ind_slider = Slider(start=pmtpd.index.min(), end=pmtpd.index.max(), value=pmtpd.index.min(), step=1, title="i")
                thecallback = CustomJS(args=dict(source = src, sourcedis = srcdisplayed, ind=ind_slider),
                code = """
                    var datain = source.data;
                    var col = datain['color'];
                    var newcolor = [];
                    var newpmti = [];

                    var dataout  = sourcedis.data;
                    newcolor = dataout['color'];
                    newpmti = dataout['PMTi'];
                    console.log(ind.value);
                    var position_index = ind.value;
                    var dic_color = col[position_index-ind.start];

                    for(var key in dic_color) {
                       newcolor[key] = dic_color[key]
                      // newpmti['key'] = key;//dic_color[key];
                    }
                    sourcedis.change.emit();
                """)
                ind_slider.js_on_change('value', thecallback)
                layout = column(draw[0],row(ind_slider))
            show(layout)
