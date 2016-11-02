#!/usr/bin/env python

"""

Background
----------

ctd_qt_demo.py

----

Merge of ctd_qt_demo.py (matplotlib data viewer based on mpl_qt_demo.py)
and
table_ctd_qt_demo.py (qt tableview with editable columns)

Purpose:
--------

    View and Edit EcoFOCI CTD data in netcdf (EPIC flavored currently) and save edited files

History:
--------

2016-10-24: Bell - Begin merging ctd_qt_demo and table_ctd_qt_demo.py

"""

# system stack
import sys, os, datetime 
from PyQt4 import QtGui, QtCore
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
from io_utils.EcoFOCI_netCDF_read import EcoFOCI_netCDF
from io_utils.EcoFOCI_netCDF_write import NetCDF_Create_CTD
from io_utils import ConfigParserLocal


__author__   = 'Shaun Bell'
__email__    = 'shaun.bell@noaa.gov'
__created__  = datetime.datetime(2016, 10, 24)
__modified__ = datetime.datetime(2016, 10, 24)
__version__  = "0.1.0"
__status__   = "Development"

class AppForm(QMainWindow):
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    example_path = parent_dir+'/example_data/example_ctd_data.nc'

    def __init__(self, parent=None, active_file=example_path):
        QMainWindow.__init__(self, parent)
        self.setWindowTitle('EcoFOCI CTD Viewer')

        self.create_menu()
        self.create_main_frame()

        self.textbox.setText(active_file)
        self.populate_dropdown()
        self.load_netcdf()
        self.create_status_bar()
        self.inverted = False
        self.load_table()
        self.on_draw()

        self.clip = QtGui.QApplication.clipboard()

    def save_plot(self):
        file_choices = "PNG (*.png)|*.png"
        
        path = unicode(QFileDialog.getSaveFileName(self, 
                        'Save file', '', 
                        file_choices))
        if path:
            self.canvas.print_figure(path, dpi=self.dpi)
            self.statusBar().showMessage('Saved to %s' % path, 2000)

    def on_about(self):
        msg = """ EcoFOCI CTD Viewer and {soon .... Editor}:
        
         * Use the matplotlib navigation bar to explore the plot
         * Change the file explored (Reload)
         * Show or hide the grid
         * Allow edits or not of table data
         * Save the plot to a file using the File menu
        """
        QMessageBox.about(self, "About the program", msg.strip())
    
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


    def keyPressEvent(self, e):
        if (e.modifiers() & QtCore.Qt.ControlModifier):
            selected = self.tableview.selectedIndexes()

            s = ''
            if e.key() == QtCore.Qt.Key_C: #copy
                row_stat = [ival.row()  for ival in selected]
                col_stat = [ival.column() for ival in selected]
                
                # cycle through unique rows and columns for selection
                # using list(set(list)) allows for selecting non-adjacent cells
                for r in list(set(row_stat)):
                    for c in list(set(col_stat)):
                        try:
                            s += str(self.tablemodel.index( r, c, QModelIndex() ).data( Qt.DisplayRole ).toString()) + "\t"
                        except AttributeError:
                            s += "\t"
                    s = s[:-1] + "\n" #eliminate last '\t'
                self.clip.setText(s)
                

    """-------------------------------------
    matplotlib graphics window - plot data 
    ----------------------------------------"""

    def on_draw(self):
        """ 
        Draws/Redrwas the figure

        """
        #choose data source to plot from, table or file
        if self.update_table_cb.isChecked():
            var1 = str(self.param_dropdown.currentText())
            updated_data = self.table2dic()

            xdata = np.array(updated_data[var1],dtype=float)
            y = np.array(updated_data['dep'],dtype=float)
            #make missing data unplotted
            ind = xdata > 1e34
            xdata[ind] = np.nan
            # clear the axes and redraw the plot anew
            #
            self.axes.clear()        
            self.axes.grid(self.grid_cb.isChecked())
            
            self.axes.plot(
                xdata,y,
                marker='o',
                picker=5)            


            self.fig.suptitle(self.station_data, fontsize=12)
        else:

            var1 = str(self.param_dropdown.currentText())
            try:
                #make missing data unplotted
                xdata = np.copy(self.ncdata[var1][0,:,0,0])
                ind = xdata >1e34
                xdata[ind] = np.nan
                y = self.ncdata['dep'][:]

                # clear the axes and redraw the plot anew
                #
                self.axes.clear()        
                self.axes.grid(self.grid_cb.isChecked())
                
                self.axes.plot(
                    xdata,y,
                    marker='o',
                    picker=5)            
            except:
                #make missing data unplotted
                xdata = np.copy(self.ncdata[var1][:])
                ind = xdata >1e34
                xdata[ind] = np.nan
                y = self.ncdata['dep'][:]

                # clear the axes and redraw the plot anew
                #
                self.axes.clear()        
                self.axes.grid(self.grid_cb.isChecked())
                
                self.axes.plot(
                    xdata,y,
                    marker='o',
                    picker=5)

            self.fig.suptitle(self.station_data, fontsize=12)

        if not self.inverted:
            self.fig.gca().set_ylim(self.axes.get_ylim()[::-1])
            self.inverted = True
        self.canvas.draw()

        #reload table data
        if self.update_table_cb.isChecked():
            self.highlight_table_column()
        else:
            self.load_table()
            self.highlight_table_column()

    def highlight_table_column(self):
        #higlight column with chosen variable plotted
        self.tableview.selectColumn(self.table_header.index(self.param_dropdown.currentText()))


    """-------------------------------------
    Buttons and Actions
    ----------------------------------------"""

    def on_save(self):
        """
        save to same location with .ed.nc ending
        """
        updated_data = self.table2dic()
        file_out = unicode(self.textbox.text()).replace('.nc','.ed.nc')
        self.save_netcdf(file_out, data=updated_data)
    

    def on_reload(self):
        """
            Reloads (or loads) selcted data file
        """
        self.load_netcdf()
        self.on_draw()

    def populate_dropdown(self):
        self.load_netcdf()
        self.station_data = {}
        for k in self.vars_dic.keys():
            if k not in ['time','time2','lat','lon']:
                self.param_dropdown.addItem(k)
            else:
                self.station_data[k] =str(self.ncdata[k][0])

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
        
    """-------------------------------------
    Main Frame
    ----------------------------------------"""

    def create_main_frame(self):
        self.main_frame = QWidget()
        
        # Create the mpl Figure and FigCanvas objects. 
        # 5x8 inches, 100 dots-per-inch
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

        self.reload_button = QPushButton("&Reload")
        self.connect(self.reload_button, SIGNAL('clicked()'), self.on_reload)

        self.save_button = QPushButton("&save")
        self.connect(self.save_button, SIGNAL('clicked()'), self.on_save)
                
        self.grid_cb = QCheckBox("Show &Grid")
        self.grid_cb.setChecked(False)
        self.connect(self.grid_cb, SIGNAL('stateChanged(int)'), self.on_draw)

        self.update_table_cb = QCheckBox("Use Updated Table")
        self.update_table_cb.setChecked(False)
        self.connect(self.update_table_cb, SIGNAL('stateChanged(int)'), self.on_draw)
                
        self.param_dropdown = QComboBox()

        self.connect(self.param_dropdown, SIGNAL('clicked()'), self.on_draw)
        
        self.tableview = QTableView()

        #
        # Layout with box sizers
        # 
        mhbox = QHBoxLayout()
        
        for w in [  self.textbox, self.reload_button, self.draw_button]:
            mhbox.addWidget(w)
            mhbox.setAlignment(w, Qt.AlignVCenter)

        mhbox2 = QHBoxLayout()

        for w2 in [ self.grid_cb, self.update_table_cb,
                    self.param_dropdown, self.save_button]:
            mhbox2.addWidget(w2)
            mhbox2.setAlignment(w2, Qt.AlignVCenter)

        lv_box = QVBoxLayout()
        lv_box.addWidget(self.canvas)
        lv_box.addWidget(self.mpl_toolbar)
        lv_box.addLayout(mhbox)
        lv_box.addLayout(mhbox2)

        h_box = QHBoxLayout()
        h_box.addLayout(lv_box)
        h_box.addWidget(self.tableview)
       
        self.main_frame.setLayout(h_box)
        self.setCentralWidget(self.main_frame)

    """-------------------------------------
    Convert Data Format
    ----------------------------------------"""

    def dic2list(self, test=False):
        """ Converts a dictionary array of numpy data into a list of lists for the table viewer such that 
                columns are per variable and rows are per depth

            Hard coded in this routine is the name of the dimensions expected (lat,lon,dep,time,time2)
            
            Todo: remove variable naming dependency

        """

        if test:
            tabledata = [[1234567890,2,3,4,5],
                         [6,7,8,9,10],
                         [11,12,13,14,15],
                         [16,17,18,19,20]]     
            header = ['col1','col2','col3','col4','col5']
        else:
            tabledata = [val[0,:,0,0].tolist() for key, val in self.ncdata.iteritems() if key not in ['lat','lon','dep','time','time2']]
            tabledata = [self.ncdata['dep'].tolist()] + tabledata
            trans_tabledata = map(list, zip(*tabledata))

            header = [key for key in self.ncdata.keys() if key not in ['lat','lon','dep','time','time2'] ]
            header = ['dep'] + header

        return trans_tabledata, header

    def table2dic(self):
        """
        cycle through each column
        """
        updated_data = {}
        

        for col in range(self.tablemodel.columnCount(parent=QtCore.QModelIndex())):
            temp = []
            for row in range(self.tablemodel.rowCount(parent=QtCore.QModelIndex())):
                value = self.tablemodel.index( row, col, QModelIndex() ).data( Qt.DisplayRole ).toString()
                temp = temp + [str(value)]
            updated_data[self.table_header[col]] = temp

        return updated_data

    """-------------------------------------
    Load and Save Data
    ----------------------------------------"""

    def load_table(self):
        
        self.table_rawdata, self.table_header = self.dic2list()

        self.tablemodel = MyTableModel(self.table_rawdata, self.table_header, self)

        self.tableview.setModel(self.tablemodel)

        #set view sizes
        self.tableview.setMinimumSize(720,568)
        self.tableview.resizeColumnsToContents()

    def load_netcdf( self, file=parent_dir+'/example_data/example_ctd_data.nc'):
        df = EcoFOCI_netCDF(unicode(self.textbox.text()))
        self.glob_atts = df.get_global_atts()
        self.vars_dic = df.get_vars()
        self.ncdata = df.ncreadfile_dic()
        df.close()

    def save_netcdf( self, file, **kwargs):
        if 'data' in kwargs.keys():
            data=kwargs['data']
        else:
            data = self.ncdata

        #read in basic epic key parameters
        epic_vars = ConfigParserLocal.get_config(parent_dir+'/config/ctd_epickeys.json')

        ncinstance = NetCDF_Create_CTD(savefile=file)
        ncinstance.file_create()
        ncinstance.sbeglobal_atts(**self.glob_atts)
        ncinstance.dimension_init(depth_len=len(self.ncdata['dep']))
        ncinstance.variable_init(epic_vars)
        ncinstance.add_coord_data(depth=self.ncdata['dep'], latitude=self.ncdata['lat'], 
                longitude=self.ncdata['lon'], time1=self.ncdata['time'], time2=self.ncdata['time2'],)
        if 'data' in kwargs.keys():
            ncinstance.add_data(epic_vars,data_dic=data)
        else:
            ncinstance.add_data(epic_vars,data_dic=self.ncdata)
        #ncinstance.add_history('Profile edited and QC\'d')

        ncinstance.close()

"""-------------------------------------Table Model----------------------------------------------"""

# creation of the table model
class MyTableModel(QAbstractTableModel):
    def __init__(self, datain, headerdata, parent = None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = datain
        self.headerdata = headerdata

    def rowCount(self, parent):
        return len(self.arraydata)

    def columnCount(self, parent):
        return len(self.arraydata[0])

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        return (self.arraydata[index.row()][index.column()])

    def setData(self, index, value, role):
        self.arraydata[index.row()][index.column()] = value
        return True

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headerdata[col])
        return QVariant()

    def flags(self, index):
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

"""-------------------------------------Main Loop----------------------------------------------"""

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