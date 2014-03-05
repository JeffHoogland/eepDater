#eepDater - an GUI system updater for apt-get powered systems written in python and elementary
#
#Written by: Jeff Hoogland
#Started: 03/04/2014

from efl.evas import EVAS_HINT_EXPAND, EVAS_HINT_FILL
from efl import elementary
from efl.elementary.window import StandardWindow
from efl.elementary.box import Box
from efl.elementary.button import Button
from efl.elementary.toolbar import Toolbar, ELM_TOOLBAR_SHRINK_MENU, \
    ELM_OBJECT_SELECT_MODE_NONE
from efl.elementary.frame import Frame
from efl.elementary.label import Label
from efl.elementary.scroller import Scroller
from efl.elementary.check import Check

import sortedlist as sl

EXPAND_BOTH = EVAS_HINT_EXPAND, EVAS_HINT_EXPAND
EXPAND_HORIZ = EVAS_HINT_EXPAND, 0.0
FILL_BOTH = EVAS_HINT_FILL, EVAS_HINT_FILL
FILL_HORIZ = EVAS_HINT_FILL, 0.5
ALIGN_CENTER = 0.5, 0.5

class Interface(object):
    def __init__( self ):
        self.mainWindow = StandardWindow("eppDater", "eppDater - System Updater", autodel=True, size=(320, 320))
        self.mainWindow.callback_delete_request_add(lambda o: elementary.exit())
        
        self.mainBox = Box(self.mainWindow, size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        self.mainWindow.resize_object_add(self.mainBox)

        #Build our toolbar
        self.mainTb = Toolbar(self.mainWindow, homogeneous=False, size_hint_weight=(0.0, 0.0), size_hint_align=(EVAS_HINT_FILL, 0.0))
        
        self.mainTb.item_append("close", "Clear", self.clearPress)
        self.mainTb.item_append("apps", "Select All", self.selectAllPress)
        self.mainTb.item_append("refresh", "Refresh", self.refreshPress)
        self.mainTb.item_append("arrow_down", "Apply", self.installUpdatesPress)

        self.mainTb.show()

        #Build our sortable list that displays packages that need updates
        scr = Scroller(self.mainWindow, size_hint_weight = EXPAND_BOTH, size_hint_align = FILL_BOTH)
    
        titles = [("Upgrade", False), ("Package", True), ("Version", True)]

        self.packageList = sl.SortedList(scr, titles=titles, size_hint_weight=EXPAND_BOTH, homogeneous=False)

        #Add a list of dummy packages for testing purposes
        self.addPackage("test", "1.1.1", "A testing pacakge")
        self.addPackage("burp", "0.2", "Goober's smelly burps")
        self.addPackage("derp", "1.3", "Big'ol dummy")

        scr.content = self.packageList
        scr.show()

        #Add a label that shows the package's description
        self.desFrame = Frame(self.mainWindow, size_hint_weight = (EVAS_HINT_EXPAND, 0.0), size_hint_align = (-1.0, 0.0))
        
        self.currentDescription = Label(self.mainWindow, size_hint_weight = FILL_BOTH)
        self.currentDescription.text = "Select a package for information"
        self.currentDescription.show()

        self.desFrame.text = "Description"
        self.desFrame.content = self.currentDescription
        self.desFrame.show()

        #Add all of our objects to the window
        self.mainBox.pack_end(self.mainTb)
        self.mainBox.pack_end(scr)
        self.mainBox.pack_end(self.desFrame)
        self.mainBox.show()

    def addPackage( self, packageName, versionNumber, packageDescription ):
        row = []
        
        ourCheck = Check(self.mainWindow)
        ourCheck.show()
        row.append(ourCheck)

        ourName = Button(self.mainWindow, style="anchor", size_hint_weight=EXPAND_HORIZ,
                    size_hint_align=FILL_HORIZ)
        ourName.text = packageName
        ourName.data["packageDes"] = packageDescription
        ourName.callback_pressed_add( self.packagePress )
        ourName.show()
        row.append(ourName)

        ourVersion = Label(self.mainWindow, size_hint_weight=EXPAND_HORIZ,
                    size_hint_align=(0.1, 0.5))
        ourVersion.text = versionNumber
        ourVersion.show()
        row.append(ourVersion)

        self.packageList.row_pack(row, sort=False)

    def packagePress( self, obj ):
        self.desFrame.text = "Description - %s" % obj.text
        self.currentDescription.text = obj.data["packageDes"]

    def clearPress( self, obj, it ):
        pass

    def selectAllPress( self, obj, it ):
        pass

    def refreshPress( self, obj, it ):
        pass

    def installUpdatesPress( self, obj, it ):
        pass

    def launch( self ):
        self.mainWindow.show()

if __name__ == "__main__":
    elementary.init()

    GUI = Interface()
    GUI.launch()

    elementary.run()
    elementary.shutdown()
