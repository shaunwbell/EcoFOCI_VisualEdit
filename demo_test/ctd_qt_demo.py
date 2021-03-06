"""

ctd_qt_demo.py

----
Modification of demo

This demo demonstrates how to embed a matplotlib (mpl) plot 
into a PyQt4 GUI application, including:

* Using the navigation toolbar
* Adding data to the plot
* Dynamically modifying the plot's properties
* Processing mpl events
* Saving the plot to a file from a menu

The main goal is to serve as a basis for developing rich PyQt GUI
applications featuring mpl plots (using the mpl OO API).

Eli Bendersky (eliben@gmail.com)
License: this code is in the public domain
Last modified: 19.01.2009
"""

# system stack
import sys, os, random
from PyQt4.QtCore import *
from PyQt4.QtGui import *

#science stack
import numpy as np
import json

#visual stack
import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

#user stack
# Relative User Stack
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(1, parent_dir)
from io_utils.EcoFOCI_netCDF_read import EcoFOCI_netCDF
from io_utils.EcoFOCI_netCDF_write import NetCDF_Create_CTD


class AppForm(QMainWindow):
    example_path = parent_dir+'/example_data/example_ctd_data.nc'

    def __init__(self, parent=None, active_file=example_path):
        QMainWindow.__init__(self, parent)
        self.setWindowTitle('CTD Demo: PyQt with matplotlib')

        self.create_menu()
        self.create_main_frame()

        self.textbox.setText(active_file)
        self.populate_dropdown()
        self.create_status_bar()
        self.inverted = False
        self.on_draw()

    def save_plot(self):
        file_choices = "PNG (*.png)|*.png"
        
        path = unicode(QFileDialog.getSaveFileName(self, 
                        'Save file', '', 
                        file_choices))
        if path:
            self.canvas.print_figure(path, dpi=self.dpi)
            self.statusBar().showMessage('Saved to %s' % path, 2000)
    
    def on_about(self):
        msg = """ A demo of using PyQt with matplotlib:
        
         * Use the matplotlib navigation bar
         * Add values to the text box and press Enter (or click "Draw")
         * Show or hide the grid
         * Drag the slider to modify the width of the bars
         * Save the plot to a file using the File menu
         * Click on a bar to receive an informative message
        """
        QMessageBox.about(self, "About the demo", msg.strip())
    
    def on_pick(self, event):
        # The event received here is of the type
        # matplotlib.backend_bases.PickEvent
        #
        # It carries lots of information, of which we're using
        # only a small amount here.
        # 
        xdata = event.artist.get_xdata()
        ydata = event.artist.get_ydata()
        ind = event.ind
        msg = "You've clicked on a point with coords:\n {0}".format( tuple(zip(xdata[ind], ydata[ind])))
        
        QMessageBox.information(self, "Click!", msg)

    def on_draw(self):
        """ Redraws the figure
        """
        """
        # Following logic associates an arbitrary name to an Epic keycode
        if str(self.param_dropdown.currentText()) == 'Temperature':
            var1,var2 = ['T_28','T2_35']
        elif str(self.param_dropdown.currentText()) == 'Salinity':
            var1,var2 = ['S_41', 'S_42']
        elif str(self.param_dropdown.currentText()) == 'Oxygen':
            var1,var2 = ['O_65','CTDOXY_4221']
        elif str(self.param_dropdown.currentText()) == 'ECO-FLNT':
            var1,var2 = ['F_903','Trb_980']
        elif str(self.param_dropdown.currentText()) == 'PAR':
            var1,var2 = ['PAR_905','']
        else:
            var1,var2 = ['T_28','T2_35'] 
        """
        var1 = str(self.param_dropdown.currentText())
        self.load_netcdf()
        try:
            xdata = self.ncdata[var1][0,:,0,0]
            #xdata2 = self.ncdata[var2][0,:,0,0]
            y = self.ncdata['dep'][:]

            # clear the axes and redraw the plot anew
            #
            self.axes.clear()        
            self.axes.grid(self.grid_cb.isChecked())
            
            self.axes.plot(
                xdata,y,
                #xdata2,y,
                marker='*',
                picker=True)            
        except KeyError:
            xdata = self.ncdata[var1][0,:,0,0]
            y = self.ncdata['dep'][:]

            # clear the axes and redraw the plot anew
            #
            self.axes.clear()        
            self.axes.grid(self.grid_cb.isChecked())
            
            self.axes.plot(
                xdata,y,
                marker='*',
                picker=True)            
        except IndexError:
            xdata = self.ncdata[var1][:]
            y = self.ncdata['dep'][:]

            # clear the axes and redraw the plot anew
            #
            self.axes.clear()        
            self.axes.grid(self.grid_cb.isChecked())
            
            self.axes.plot(
                xdata,y,
                marker='*',
                picker=True)

        self.fig.suptitle(self.station_data, fontsize=12)

        if not self.inverted:
            self.fig.gca().set_ylim(self.axes.get_ylim()[::-1])
            self.inverted = True
        self.canvas.draw()

    def on_save(self):
        """
        save to same location with .ed.nc ending
        """
        file_out = unicode(self.textbox.text()).replace('.nc','.ed.nc')
        self.save_netcdf(file_out)
    
    def create_main_frame(self):
        self.main_frame = QWidget()
        
        # Create the mpl Figure and FigCanvas objects. 
        # 5x4 inches, 100 dots-per-inch
        #
        self.dpi = 100
        self.fig = Figure((5.0, 8.0), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.main_frame)
        
        # Since we have only one plot, we can use add_axes 
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        #
        self.axes = self.fig.add_subplot(111)
        
        # Bind the 'pick' event for clicking on one of the bars
        #
        self.canvas.mpl_connect('pick_event', self.on_pick)
        
        # Create the navigation toolbar, tied to the canvas
        #
        self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_frame)
        
        # Other GUI controls
        # 
        self.textbox = QLineEdit()
        self.textbox.setMinimumWidth(200)
        self.connect(self.textbox, SIGNAL('editingFinished ()'), self.on_draw)
        
        self.draw_button = QPushButton("&Draw")
        self.connect(self.draw_button, SIGNAL('clicked()'), self.on_draw)

        self.save_button = QPushButton("&save")
        self.connect(self.save_button, SIGNAL('clicked()'), self.on_save)
                
        self.grid_cb = QCheckBox("Show &Grid")
        self.grid_cb.setChecked(False)
        self.connect(self.grid_cb, SIGNAL('stateChanged(int)'), self.on_draw)
        
        self.param_dropdown = QComboBox()

        self.connect(self.param_dropdown, SIGNAL('clicked()'), self.on_draw)
        
        #
        # Layout with box sizers
        # 
        hbox = QHBoxLayout()
        
        for w in [  self.textbox, self.draw_button, self.grid_cb,
                    self.param_dropdown, self.save_button]:
            hbox.addWidget(w)
            hbox.setAlignment(w, Qt.AlignVCenter)
        
        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)
        vbox.addWidget(self.mpl_toolbar)
        vbox.addLayout(hbox)
        
        self.main_frame.setLayout(vbox)
        self.setCentralWidget(self.main_frame)

    def populate_dropdown(self):
        self.load_netcdf()
        self.station_data = {}
        for k in self.vars_dic.keys():
            if k not in ['time','time2','lat','lon']:
                self.param_dropdown.addItem(k)
            else:
                self.station_data[k] =str(self.ncdata[k][0])

        """
        #Use following code if hardwired variable names are desired.  This just sets up
        # the options in the dropdown menu and is useful for multiple plots per screen
        self.param_dropdown.addItem("Temperature")
        self.param_dropdown.addItem("Salinity")
        self.param_dropdown.addItem("Oxygen")
        self.param_dropdown.addItem("ECO-FLNT")
        self.param_dropdown.addItem("PAR")
        """

    def create_status_bar(self):
        self.status_text = QLabel(json.dumps(self.station_data))
        self.statusBar().addWidget(self.status_text, 1)
        
    def create_menu(self):        
        self.file_menu = self.menuBar().addMenu("&File")
        
        load_file_action = self.create_action("&Save plot",
            shortcut="Ctrl+S", slot=self.save_plot, 
            tip="Save the plot")
        quit_action = self.create_action("&Quit", slot=self.close, 
            shortcut="Ctrl+Q", tip="Close the application")
        
        self.add_actions(self.file_menu, 
            (load_file_action, None, quit_action))
        
        self.help_menu = self.menuBar().addMenu("&Help")
        about_action = self.create_action("&About", 
            shortcut='F1', slot=self.on_about, 
            tip='About the demo')
        
        self.add_actions(self.help_menu, (about_action,))

    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def create_action(  self, text, slot=None, shortcut=None, 
                        icon=None, tip=None, checkable=False, 
                        signal="triggered()"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/%s.png" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action

    def load_netcdf( self, file=parent_dir+'/example_data/example_ctd_data.nc'):
        df = EcoFOCI_netCDF(unicode(self.textbox.text()))
        self.vars_dic = df.get_vars()
        self.ncdata = df.ncreadfile_dic()
        df.close()

    def save_netcdf( self, file):
        ncinstance = NetCDF_Create_CTD(savefile=file)
        ncinstance.file_create()
        ncinstance.dimension_init(time_len=len(self.ncdata['time']))
        ncinstance.variable_init(self.vars_dic)
        ncinstance.add_coord_data(depth=self.ncdata['depth'], latitude=self.ncdata['lat'], 
                longitude=self.ncdata['lon'], time1=self.ncdata['time'], time2=self.ncdata['time1'],)
        ncinstance.add_data(self.vars_dic,data_dic=self.ncdata)
        ncinstance.close()

def main():
    app = QApplication(sys.argv)
    args = app.arguments()
    try:
        form = AppForm(active_file=args[1])
    except:
        form = AppForm()
    app.setStyle("plastique")
    form.show()
    app.exec_()


if __name__ == "__main__":
    main()