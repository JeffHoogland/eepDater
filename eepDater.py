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
from efl.elementary.popup import Popup
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

    def shutdown( self ):
        self.commandQueue.put('QUIT')

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
            if callable(func):
                func()
            elif func == 'QUIT':
                break

    def refreshPackages( self ):
        self.cache.update()
        self.cache.open(None)

        upgradables = [pak for pak in self.cache if pak.is_upgradable]
        self.replyQueue.put(upgradables)

    def installUpdates( self ):
        self.cache.commit()
        self.replyQueue.put(True)


class MainWin(StandardWindow):
    def __init__( self, app ):
        # create the main window
        StandardWindow.__init__(self, "eepDater", "eepDater - System Updater",
                                autodel=True, size=(320, 320))
        self.callback_delete_request_add(lambda o: elementary.exit())
        self.app = app

        # build the two main boxes
        self.mainBox = self.buildMainBox()
        self.loadBox = self.buildLoadBox()

        # the flip object has the load screen on one side and the GUI on the other
        self.flip = Flip(self, size_hint_weight=EXPAND_BOTH,
                         size_hint_align=FILL_BOTH)
        self.flip.part_content_set("front", self.mainBox)
        self.flip.part_content_set("back", self.loadBox)
        self.resize_object_add(self.flip)
        self.flip.show()

        # show the window
        self.show()

    def buildLoadBox(self):
        # build the load label
        loadLable = Label(self, size_hint_weight=EXPAND_BOTH,
                          size_hint_align=FILL_HORIZ)
        loadLable.text = "<b>Processing</b>"
        loadLable.show()
        
        # build the spinning wheel
        wheel = Progressbar(self, style="wheel", pulse_mode=True,
                            size_hint_weight=EXPAND_BOTH,
                            size_hint_align=FILL_HORIZ)
        wheel.pulse(True)
        wheel.show()

        # build the status label
        self.statusLabel = Label(self, size_hint_weight=EXPAND_BOTH,
                                 size_hint_align=FILL_HORIZ)
        self.statusLabel.show()

        # put all the built objects in a vertical box
        box = Box(self, size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        box.pack_end(loadLable)
        box.pack_end(wheel)
        box.pack_end(self.statusLabel)
        box.show()

        return box

    def buildMainBox(self):
        # build our toolbar
        self.mainTb = Toolbar(self, homogeneous=False,
                              size_hint_weight=(0.0, 0.0),
                              size_hint_align=(EVAS_HINT_FILL, 0.0))
        self.mainTb.item_append("close", "Clear", self.clearPressed)
        self.mainTb.item_append("apps", "Select All", self.selectAllPressed)
        self.mainTb.item_append("refresh", "Refresh", self.refreshPressed)
        self.mainTb.item_append("arrow_down", "Apply", self.installUpdatesPressed)
        self.mainTb.show()

        # build our sortable list that displays packages that need updates
        titles = [("Upgrade", True), ("Package", True),
                  ("Installed", True), ("Available", True)]
        scr = Scroller(self, size_hint_weight=EXPAND_BOTH,
                       size_hint_align=FILL_BOTH)
        self.packageList = sl.SortedList(scr, titles=titles, homogeneous=False,
                                         size_hint_weight=EXPAND_HORIZ)
        scr.content = self.packageList
        scr.show()

        # build the label that shows the package's description
        self.currentDescription = Label(self,
                                        size_hint_weight=FILL_BOTH)
        self.currentDescription.text = "Select a package for information"
        self.currentDescription.line_wrap_set(True)
        self.currentDescription.show()

        self.desFrame = Frame(self, size_hint_weight=EXPAND_HORIZ,
                              size_hint_align=FILL_HORIZ)
        self.desFrame.text = "Description"
        self.desFrame.content = self.currentDescription
        self.desFrame.show()

        # add all of our objects to the box
        box = Box(self, size_hint_weight=EXPAND_BOTH,
                           size_hint_align=FILL_BOTH)
        box.pack_end(self.mainTb)
        box.pack_end(scr)
        box.pack_end(self.desFrame)
        box.show()

        return box

    def clearPressed( self, obj, it ):
        it.selected = False
        for rw in self.packageList.rows:
            rw[0].state = False
            self.app.checkChange(rw[0])

    def selectAllPressed( self, obj, it ):
        it.selected = False
        for rw in self.packageList.rows:
            rw[0].state = True
            self.app.checkChange(rw[0])

    def refreshPressed( self, obj, it ):
        it.selected = False
        self.app.refreshPackages()

    def installUpdatesPressed( self, obj, it ):
        it.selected = False
        self.app.installUpdates()

    def packagePressed( self, obj ):
        self.desFrame.text = "Description - %s" % obj.text
        self.currentDescription.text = obj.data["packageDes"]

    def addPackage( self, pak ):
        row = []

        ourCheck = Check(self)
        ourCheck.data['packageName'] = pak.name
        ourCheck.callback_changed_add(self.app.checkChange)
        ourCheck.show()
        row.append(ourCheck)

        ourName = Button(self, style="anchor", size_hint_weight=EXPAND_HORIZ,
                         size_hint_align=FILL_HORIZ)
        ourName.text = pak.name
        ourName.data["packageDes"] = pak.candidate.description
        ourName.callback_pressed_add(self.packagePressed)
        ourName.show()
        row.append(ourName)

        ourVersion = Label(self, size_hint_weight=EXPAND_HORIZ,
                           size_hint_align=(0.1, 0.5))
        ourVersion.text = pak.installed.version
        ourVersion.show()
        row.append(ourVersion)

        newVersion = Label(self, size_hint_weight=EXPAND_HORIZ,
                           size_hint_align=(0.1, 0.5))
        newVersion.text = pak.candidate.version
        newVersion.show()
        row.append(newVersion)

        self.app.packagesToUpdate[pak.name] = {'check':ourCheck, 'selected':False}
        self.packageList.row_pack(row, sort=False)

    def showDialog(self, title, msg):
        dia = Popup(self)
        dia.part_text_set("title,text", title)
        dia.part_text_set("default", msg)

        bt = Button(dia, text="Ok")
        bt.callback_clicked_add(lambda b: dia.delete())
        dia.part_content_set("button1", bt)

        dia.show()


class eepDater(object):
    def __init__( self ):
        self.packagesToUpdate = {}
        self.apt = ThreadedAPT()
        self.win = MainWin(self)

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

    def installUpdates( self ):
        if len(self.apt.cache.get_changes()) == 0:
            self.win.showDialog("Nothing to do",
                "No packages selected to upgrade.<br>" \
                "You must select at least one package from the list.")
            return
        self.win.statusLabel.text = "<i>Installing selected packages...</i>"
        self.win.flip.go(ELM_FLIP_ROTATE_YZ_CENTER_AXIS)
        self.apt.run("installUpdates", self.installUpdatesDone)

    def installUpdatesDone( self, result ):
        self.win.statusLabel.text = "<i>Refreshing package lists...</i>"
        self.apt.run("refreshPackages", self.refreshPackagesDone)
        self.packagesToUpdate.clear()

    def refreshPackages( self ):
        self.win.statusLabel.text = "<i>Refreshing package lists...</i>"
        self.win.flip.go(ELM_FLIP_ROTATE_YZ_CENTER_AXIS)

        self.apt.run("refreshPackages", self.refreshPackagesDone)
        self.packagesToUpdate.clear()

    def refreshPackagesDone( self, upgradables ):
        # clear the packages list
        storerows = list(self.win.packageList.rows)
        for row in storerows:
            self.win.packageList.row_unpack(row, True)

        # populate the packages list
        for pak in upgradables:
            self.win.addPackage(pak)

        self.win.flip.go(ELM_FLIP_ROTATE_YZ_CENTER_AXIS)


if __name__ == "__main__":
    elementary.init()

    app = eepDater()
    app.refreshPackages()

    elementary.run()
    app.apt.shutdown()

    elementary.shutdown()
