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
import threading
import Queue

EXPAND_BOTH = EVAS_HINT_EXPAND, EVAS_HINT_EXPAND
EXPAND_HORIZ = EVAS_HINT_EXPAND, 0.0
FILL_BOTH = EVAS_HINT_FILL, EVAS_HINT_FILL
FILL_HORIZ = EVAS_HINT_FILL, 0.5
ALIGN_CENTER = 0.5, 0.5


class ThreadedAPT(object):
    def __init__( self ):
        self.cache = apt.Cache()
        self.commandQueue = Queue.Queue()
        self.replyQueue = Queue.Queue()
        self.doneCB = None

        # start the working thread
        self.t = threading.Thread(target=self.threadFunc)
        self.t.start()

        # add a timer to check the data returned by the worker thread
        self.timer = ecore.Timer(0.1, self.checkReplyQueue)

    def run( self, action, doneCB=None ):
        self.doneCB = doneCB
        self.commandQueue.put(getattr(self, action))

    def checkReplyQueue( self ):
        if not self.replyQueue.empty():
            result = self.replyQueue.get_nowait()
            if callable(self.doneCB):
                self.doneCB(result)
        return True

    # all the member below this point run in the thread
    def threadFunc( self ):
        while True:
            # wait here until an item in the queue is present
            func = self.commandQueue.get()
            func()

    def refreshPackages( self ):
        self.cache.update()
        self.cache.open(None)

        upgradables = [pak for pak in self.cache if pak.is_upgradable]
        self.replyQueue.put(upgradables)

    def installUpdates( self ):
        self.cache.commit()
        self.replyQueue.put(True)


class Interface(object):
    def __init__( self ):
        self.packagesToUpdate = {}
        self.apt = ThreadedAPT()

        #Build our GUI
        self.mainWindow = StandardWindow("eepDater", "eepDater - System Updater",
                                         autodel=True, size=(320, 320))
        self.mainWindow.callback_delete_request_add(lambda o: elementary.exit())

        #Our flip object has a load screen on one side and the GUI on the other
        self.flipBox = Box(self.mainWindow, size_hint_weight=EXPAND_BOTH,
                           size_hint_align=FILL_BOTH)
        self.flipBox.show()

        self.fl = fl = Flip(self.mainWindow, size_hint_weight=EXPAND_BOTH,
                            size_hint_align=FILL_BOTH)
        self.flipBox.pack_end(fl)
        fl.show()
        
        #Build our loading screen
        self.loadBox = Box(self.mainWindow, size_hint_weight=EXPAND_BOTH,
                           size_hint_align=FILL_BOTH)
        self.loadBox.show()

        loadLable = Label(self.mainWindow, size_hint_weight=EXPAND_BOTH,
                          size_hint_align=FILL_HORIZ)
        loadLable.text = "<b>Processing</b>"
        loadLable.show()
        self.loadBox.pack_end(loadLable)

        pb7 = Progressbar(self.mainWindow, style="wheel", text="Style: wheel",
                          pulse_mode=True, size_hint_weight=EXPAND_BOTH,
                          size_hint_align=FILL_HORIZ)
        self.loadBox.pack_end(pb7)
        pb7.pulse(True)
        pb7.show()

        self.statusLabel = statusLable = Label(self.mainWindow,
                                               size_hint_weight=EXPAND_BOTH,
                                               size_hint_align=FILL_HORIZ)
        statusLable.show()
        self.loadBox.pack_end(statusLable)

        self.mainBox = Box(self.mainWindow, size_hint_weight=EXPAND_BOTH,
                           size_hint_align=FILL_BOTH)
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

        ourName = Button(self.mainWindow, style="anchor",
                         size_hint_weight=EXPAND_HORIZ,
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
        ourPackage = self.apt.cache[packageName]
        if obj.state_get() == True:
            ourPackage.mark_upgrade()
            self.packagesToUpdate[packageName]['selected'] = True
        else:
            self.packagesToUpdate[packageName]['selected'] = False

            changes = self.apt.cache.get_changes()
            self.apt.cache.clear()
            for ourPackage in changes:
                markupgrade = True
                if self.packagesToUpdate[ourPackage.name]['selected'] == False:
                    markupgrade = False

                if markupgrade:
                    ourPackage.mark_upgrade()

        for pak in self.packagesToUpdate:
            self.packagesToUpdate[pak]['check'].state_set(False)
            self.packagesToUpdate[pak]['check'].text = ""

        for pak in self.apt.cache.get_changes():
            if pak.name in self.packagesToUpdate:
                self.packagesToUpdate[pak.name]['check'].state_set(True)
                if self.packagesToUpdate[pak.name]['selected'] == False:
                    self.packagesToUpdate[pak.name]['check'].text = "dep"

    def packagePress( self, obj ):
        self.desFrame.text = "Description - %s" % obj.text
        self.currentDescription.text = obj.data["packageDes"]

    def clearPress( self, obj, it ):
        it.selected_set(False)
        for rw in self.packageList.rows:
            rw[0].state_set(False)
            self.checkChange(rw[0])

    def selectAllPress( self, obj, it ):
        for rw in self.packageList.rows:
            rw[0].state_set(True)
            self.checkChange(rw[0])
        it.selected_set(False)

    def refreshPress( self, obj, it ):
        it.selected_set(False)
        self.refreshPackages()

    def installUpdatesPress( self, obj, it ):
        it.selected_set(False)
        self.installUpdates()

    def installUpdates( self ):
        self.statusLabel.text = "<i>Installing selected pacakges...</i>"
        self.fl.go(ELM_FLIP_ROTATE_YZ_CENTER_AXIS)
        self.apt.run("installUpdates", self.installUpdatesDone)

    def installUpdatesDone( self, result ):
        self.statusLabel.text = "<i>Refreshing package lists...</i>"
        self.apt.run("refreshPackages", self.refreshPackagesDone)
        self.packagesToUpdate.clear()

    def refreshPackages( self ):
        self.statusLabel.text = "<i>Refreshing package lists...</i>"
        self.fl.go(ELM_FLIP_ROTATE_YZ_CENTER_AXIS)

        self.apt.run("refreshPackages", self.refreshPackagesDone)
        self.packagesToUpdate.clear()

    def refreshPackagesDone( self, upgradables ):
        # clear the packages list
        storerows = list(self.packageList.rows)
        for row in storerows:
            self.packageList.row_unpack(row, True)

        # populate the packages list
        for pak in upgradables:
            ourPackage = pak.name
            ourVersion = str(pak.candidate).split(":")[3][:-1].replace("'", "")
            ourDescription = pak.candidate.description
            self.addPackage(ourPackage, ourVersion, ourDescription)

        self.fl.go(ELM_FLIP_ROTATE_YZ_CENTER_AXIS)

    def launch( self ):
        self.mainWindow.show()
        self.buildmaingui()

    def buildmaingui( self ):
        #Build our toolbar
        self.mainTb = Toolbar(self.mainWindow, homogeneous=False,
                              size_hint_weight=(0.0, 0.0),
                              size_hint_align=(EVAS_HINT_FILL, 0.0))
        
        self.mainTb.item_append("close", "Clear", self.clearPress)
        self.mainTb.item_append("apps", "Select All", self.selectAllPress)
        self.mainTb.item_append("refresh", "Refresh", self.refreshPress)
        self.mainTb.item_append("arrow_down", "Apply", self.installUpdatesPress)

        self.mainTb.show()

        #Build our sortable list that displays packages that need updates
        scr = Scroller(self.mainWindow, size_hint_weight = EXPAND_BOTH,
                       size_hint_align = FILL_BOTH)
    
        titles = [("Upgrade", True), ("Package", True), ("Version", True)]

        self.packageList = sl.SortedList(scr, titles=titles, homogeneous=False,
                                         size_hint_weight=EXPAND_HORIZ)

        #Get package list
        self.refreshPackages()

        scr.content = self.packageList
        scr.show()

        #Add a label that shows the package's description
        self.desFrame = Frame(self.mainWindow, size_hint_weight=EXPAND_HORIZ,
                              size_hint_align=FILL_HORIZ)
        
        self.currentDescription = Label(self.mainWindow,
                                        size_hint_weight=FILL_BOTH)
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
