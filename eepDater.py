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
from efl.elementary.progressbar import Progressbar
from efl.elementary.flip import Flip, ELM_FLIP_ROTATE_X_CENTER_AXIS, \
    ELM_FLIP_ROTATE_Y_CENTER_AXIS, ELM_FLIP_ROTATE_XZ_CENTER_AXIS, \
    ELM_FLIP_ROTATE_YZ_CENTER_AXIS, ELM_FLIP_CUBE_LEFT, ELM_FLIP_CUBE_RIGHT, \
    ELM_FLIP_CUBE_UP, ELM_FLIP_CUBE_DOWN, ELM_FLIP_PAGE_LEFT, \
    ELM_FLIP_PAGE_RIGHT, ELM_FLIP_PAGE_UP, ELM_FLIP_PAGE_DOWN, \
    ELM_FLIP_DIRECTION_UP, ELM_FLIP_DIRECTION_DOWN, \
    ELM_FLIP_DIRECTION_LEFT, ELM_FLIP_DIRECTION_RIGHT, \
    ELM_FLIP_INTERACTION_NONE, ELM_FLIP_INTERACTION_ROTATE, \
    ELM_FLIP_INTERACTION_CUBE, ELM_FLIP_INTERACTION_PAGE
import efl.ecore as ecore

import sortedlist as sl
import apt

EXPAND_BOTH = EVAS_HINT_EXPAND, EVAS_HINT_EXPAND
EXPAND_HORIZ = EVAS_HINT_EXPAND, 0.0
FILL_BOTH = EVAS_HINT_FILL, EVAS_HINT_FILL
FILL_HORIZ = EVAS_HINT_FILL, 0.5
ALIGN_CENTER = 0.5, 0.5

class Interface(object):
    def __init__( self ):
        #Store our apt cache object
        self.cache = apt.Cache()
        self.packagesToUpdate = {}
    
        #Build our GUI
        self.mainWindow = StandardWindow("eppDater", "eppDater - System Updater", autodel=True, size=(320, 320))
        self.mainWindow.callback_delete_request_add(lambda o: elementary.exit())

        self.flipBox = Box(self.mainWindow, size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        self.flipBox.show()

        self.fl = fl = Flip(self.mainWindow, size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        self.flipBox.pack_end(fl)
        fl.show()
        
        self.loadBox = Box(self.mainWindow, size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        self.loadBox.show()

        pb7 = Progressbar(self.mainWindow, style="wheel", text="Style: wheel", pulse_mode=True,
                    size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_HORIZ)
        self.loadBox.pack_end(pb7)
        pb7.pulse(True)
        pb7.show()


        self.mainBox = Box(self.mainWindow, size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        self.mainWindow.resize_object_add(self.flipBox)

        fl.part_content_set("back", self.loadBox)
        fl.part_content_set("front", self.mainBox)

        self.mainBox.show()

    def addPackage( self, packageName, versionNumber, packageDescription ):
        row = []
        
        ourCheck = Check(self.mainWindow)
        ourCheck.data['packageName'] = packageName
        ourCheck.callback_changed_add( self.checkChange )
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

        self.packagesToUpdate[packageName] = {'check':ourCheck, 'selected':False}
        self.packageList.row_pack(row, sort=False)

    def checkChange( self, obj ):
        packageName = obj.data['packageName']
        ourPackage = self.cache[packageName]
        if obj.state_get() == True:
            ourPackage.mark_upgrade()
            self.packagesToUpdate[packageName]['selected'] = True
        else:
            self.packagesToUpdate[packageName]['selected'] = False

            changes = self.cache.get_changes()
            self.cache.clear()
            for ourPackage in changes:
                markupgrade = True
                if self.packagesToUpdate[ourPackage.name]['selected'] == False:
                    markupgrade = False

                if markupgrade:
                    ourPackage.mark_upgrade()

        for pak in self.packagesToUpdate:
            self.packagesToUpdate[pak]['check'].state_set(False)
            self.packagesToUpdate[pak]['check'].text = ""

        for pak in self.cache.get_changes():
            if pak.name in self.packagesToUpdate:
                self.packagesToUpdate[pak.name]['check'].state_set(True)
                if self.packagesToUpdate[pak.name]['selected'] == False:
                    self.packagesToUpdate[pak.name]['check'].text = "dep"

    def packagePress( self, obj ):
        self.desFrame.text = "Description - %s" % obj.text
        self.currentDescription.text = obj.data["packageDes"]

    def clearPress( self, obj, it ):
        for rw in self.packageList.rows:
            rw[0].state_set(False)
            self.checkChange(rw[0])

    def selectAllPress( self, obj, it ):
        for rw in self.packageList.rows:
            rw[0].state_set(True)
            self.checkChange(rw[0])

    def refreshPress( self, obj, it ):
        self.refreshPackages()

    def installUpdatesPress( self, obj, it ):
        self.cache.commit()
        self.refreshPackages()

    def refreshPackages( self ):
        #Clear out old packages
        storerows = list(self.packageList.rows)
        for rw in storerows:
            self.packageList.row_unpack(rw, True)

        print len(self.packageList.rows)
        self.packagesToUpdate.clear()

        self.cache.update()
        self.cache.open(None)        

        for pak in self.cache:
            if pak.is_upgradable:
                ourPackage = pak.name
                ourVersion = str(pak.candidate).split(":")[3][:-1].replace("'", "")
                ourDescription = pak.candidate.description
                self.addPackage(ourPackage, ourVersion, ourDescription)

        #Add a list of dummy packages for testing purposes
        #self.addPackage("test", "1.1.1", "A testing pacakge")
        #self.addPackage("burp", "0.2", "Goober's smelly burps")
        #self.addPackage("derp", "1.3", "Big'ol dummy")

    def launch( self ):
        self.mainWindow.show()
        self.buildmaingui()

    def buildmaingui( self ):
        #Build our toolbar
        self.mainTb = Toolbar(self.mainWindow, homogeneous=False, size_hint_weight=(0.0, 0.0), size_hint_align=(EVAS_HINT_FILL, 0.0))
        
        self.mainTb.item_append("close", "Clear", self.clearPress)
        self.mainTb.item_append("apps", "Select All", self.selectAllPress)
        self.mainTb.item_append("refresh", "Refresh", self.refreshPress)
        self.mainTb.item_append("arrow_down", "Apply", self.installUpdatesPress)

        self.mainTb.show()

        #Build our sortable list that displays packages that need updates
        scr = Scroller(self.mainWindow, size_hint_weight = EXPAND_BOTH, size_hint_align = FILL_BOTH)
    
        titles = [("Upgrade", True), ("Package", True), ("Version", True)]

        self.packageList = sl.SortedList(scr, titles=titles, size_hint_weight=EXPAND_BOTH, homogeneous=False)

        #Get package list
        self.refreshPackages()

        scr.content = self.packageList
        scr.show()

        #Add a label that shows the package's description
        self.desFrame = Frame(self.mainWindow, size_hint_weight = (EVAS_HINT_EXPAND, 0.0), size_hint_align = (-1.0, 0.0))
        
        self.currentDescription = Label(self.mainWindow, size_hint_weight = FILL_BOTH)
        self.currentDescription.text = "Select a package for information"
        self.currentDescription.line_wrap_set(True)
        self.currentDescription.show()

        self.desFrame.text = "Description"
        self.desFrame.content = self.currentDescription
        self.desFrame.show()

        #Add all of our objects to the window
        self.mainBox.pack_end(self.mainTb)
        self.mainBox.pack_end(scr)
        self.mainBox.pack_end(self.desFrame)

if __name__ == "__main__":
    elementary.init()

    GUI = Interface()
    GUI.launch()

    elementary.run()
    elementary.shutdown()
