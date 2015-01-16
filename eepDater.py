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
from efl.elementary.icon import Icon
from efl.elementary.innerwindow import InnerWindow
from efl.elementary.entry import Entry, ELM_TEXT_FORMAT_PLAIN_UTF8
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
from apt.progress.base import OpProgress as BaseOpProgress
from apt.progress.base import AcquireProgress as BaseAcquireProgress
from apt.progress.base import InstallProgress as BaseInstallProgress
import threading
import Queue

EXPAND_BOTH = EVAS_HINT_EXPAND, EVAS_HINT_EXPAND
EXPAND_HORIZ = EVAS_HINT_EXPAND, 0.0
FILL_BOTH = EVAS_HINT_FILL, EVAS_HINT_FILL
FILL_HORIZ = EVAS_HINT_FILL, 0.5
ALIGN_CENTER = 0.5, 0.5

def statusMessage(text, text2="", text3="", text4=""):
    global progressque
    progressque.append("%s%s%s%s"%(text, text2, text3, text4))
    print(text, text2, text3, text4)

class operationProgress(BaseOpProgress):
    """Display the progress of operations such as opening the cache."""

    def update(self, percent=None):
        """Called periodically to update the user interface."""
        BaseOpProgress.update(self, percent)
        statusMessage("UPDATE_OP op:%s  subop:%s  percent:%.1f" % (
              self.op, self.subop, self.percent))

    def done(self):
        """Called once an operation has been completed."""
        BaseOpProgress.done(self)
        statusMessage("DONE_OP")


class updateProgress(BaseAcquireProgress):
    """Called by the apt thread while updating packages cache info"""
    def __init__(self):
        BaseAcquireProgress.__init__(self)

    def start(self):
        BaseAcquireProgress.start(self)
        statusMessage("### START UPDATE ###")

    def stop(self):
        BaseAcquireProgress.stop(self)
        statusMessage("### UPDATE DONE ###")

    def pulse(self, owner):
        BaseAcquireProgress.pulse(self, owner)
        statusMessage("PULSE items:%d/%d bytes:%.1f/%.1f rate:%.1f elapsed:%d" % (
              self.current_items, self.total_items, 
              self.current_bytes, self.total_bytes,
              self.current_cps, self.elapsed_time))
        return True # False to cancel the job

    def ims_hit(self, item):
        """ Invoked when an item is confirmed to be up-to-date """
        statusMessage("IMS_HIT", item.description)
    
    def fetch(self, item):
        """ Invoked when some of the item's data is fetched. """
        statusMessage("FETCH", item.description)

    def done(self, item):
        """ Invoked when an item is successfully and completely fetched. """
        statusMessage("DONE", item.description)

    def fail(self, item):
        """ Invoked when the process of fetching an item encounters an error. """
        statusMessage("FAIL", item.description)


class downloadProgress(BaseAcquireProgress):
    """Called by the apt thread while downloading pakages"""
    def __init__(self):
        BaseAcquireProgress.__init__(self)

    def start(self):
        """Invoked when the Acquire process starts running."""
        BaseAcquireProgress.start(self)
        statusMessage("### START DOWNLOAD ###")

    def stop(self):
        """Invoked when the Acquire process stops running."""
        BaseAcquireProgress.stop(self)
        statusMessage("### DOWNLOAD DONE ###")

    def pulse(self, owner):
        """Periodically invoked while the Acquire process is underway."""
        BaseAcquireProgress.stop(self, owner)
        statusMessage("PULSE  items:%d/%d  bytes:%.1f/%.1f  rate:%.1f  elapsed:%d" % (
              self.current_items, self.total_items, 
              self.current_bytes, self.total_bytes,
              self.current_cps, self.elapsed_time))
        return True # False to cancel the job

    def ims_hit(self, item):
        """Invoked when an item is confirmed to be up-to-date"""
        statusMessage("IMS_HIT", item.description)
    
    def fetch(self, item):
        """Invoked when some of the item's data is fetched."""
        statusMessage("FETCH", item.description)

    def done(self, item):
        """Invoked when an item is successfully and completely fetched."""
        statusMessage("DONE", item.description)

    def fail(self, item):
        """Invoked when the process of fetching an item encounters an error."""
        statusMessage("FAIL", item.description)


class installProgress(BaseInstallProgress):
    """Called by the apt thread while installing pakages"""
    def __init__(self):
        BaseInstallProgress.__init__(self)

    def conffile(current, new):
        """Called when a conffile question from dpkg is detected."""
        BaseInstallProgress.conffile(self, current, new)
        statusMessage("CONFFILE", current, new)

    def start_update(self):
        """(Abstract) Start update."""
        statusMessage("START_UPDATE")

    def finish_update(self):
        """(Abstract) Called when update has finished."""
        statusMessage("FINISH_UPDATE")

    def error(self, pkg, errormsg):
        """(Abstract) Called when a error is detected during the install."""
        statusMessage("ERROR_UPDATE", pkg, errormsg)

    def status_change(self, pkg, percent, status):
        """(Abstract) Called when the APT status changed."""
        statusMessage("STATUS_CHANGE", pkg, percent, status)

    def processing(self, pkg, stage):
        """(Abstract) Sent just before a processing stage starts."""
        statusMessage("PROCESSING", pkg, stage)


class ThreadedAPT(object):
    def __init__(self):
        # the accessible apt cache object
        self.cache = apt.Cache()

        # private stuff
        self._commandQueue = Queue.Queue()
        self._replyQueue = Queue.Queue()
        self._doneCB = None

        # instances of the classes used to report progress
        self._op_progress = operationProgress()
        self._update_progress = updateProgress()
        self._download_progress = downloadProgress()
        self._install_progress = installProgress()

        # add a timer to check the data returned by the worker thread
        self._timer = ecore.Timer(0.1, self.checkReplyQueue)

        # start the working thread
        threading.Thread(target=self.threadFunc).start()

    def run(self, action, doneCB=None):
        self._doneCB = doneCB
        self._commandQueue.put(getattr(self, action))

    def shutdown(self):
        self._timer.delete()
        self._commandQueue.put('QUIT')

    def checkReplyQueue(self):
        if not self._replyQueue.empty():
            result = self._replyQueue.get_nowait()
            if callable(self._doneCB):
                self._doneCB(result)
        return True

    # all the member below this point run in the thread
    def threadFunc(self):
        while True:
            # wait here until an item in the queue is present
            func = self._commandQueue.get()
            if callable(func):
                func()
            elif func == 'QUIT':
                break

    def refreshPackages(self):
        self.cache.update(self._update_progress)
        self.cache.open(self._op_progress)

        upgradables = [pak for pak in self.cache if pak.is_upgradable]
        self._replyQueue.put(upgradables)

    def installUpdates(self):
        self.cache.commit(self._download_progress, self._install_progress)
        self._replyQueue.put(True)


class MainWin(StandardWindow):
    def __init__(self, app):
        # create the main window
        StandardWindow.__init__(self, "eepdater", "eepDater - System Updater",
                                autodel=True, size=(320, 320))
        self.callback_delete_request_add(lambda o: elementary.exit())
        self.app = app

        icon = Icon(self)
        icon.size_hint_weight_set(EVAS_HINT_EXPAND, EVAS_HINT_EXPAND)
        icon.size_hint_align_set(EVAS_HINT_FILL, EVAS_HINT_FILL)
        icon.standard_set('update-manager')
        icon.show()
        self.icon_object_set(icon.object_get())

        # build the two main boxes
        self.mainBox = self.buildMainBox()
        self.loadBox = self.buildLoadBox()
        
        # build the information details inwin object
        self.buildDetailsWin()

        # the flip object has the load screen on one side and the GUI on the other
        self.flip = Flip(self, size_hint_weight=EXPAND_BOTH,
                         size_hint_align=FILL_BOTH)
        self.flip.part_content_set("front", self.mainBox)
        self.flip.part_content_set("back", self.loadBox)
        self.resize_object_add(self.flip)
        self.flip.show()

        # show the window
        self.show()

    def buildDetailsWin(self):
        self.updateText = Entry(self, size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        self.updateText.editable_set(False)
        self.updateText.scrollable_set(True)
        self.updateText.show()

        closebtn = Button(self)
        closebtn.text_set("Done")
        closebtn.callback_pressed_add(self.innerWinHide)
        closebtn.show()

        box = Box(self, size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        box.pack_end(self.updateText)
        box.pack_end(closebtn)
        box.show()

        self.innerWin = InnerWindow(self, size_hint_weight=EXPAND_BOTH,
                          size_hint_align=FILL_HORIZ)
        self.innerWin.content_set(box)

    def innerWinShow(self, obj=False):
        self.innerWin.show()
        self.innerWin.activate()

    def innerWinHide(self, obj=False):
        self.innerWin.hide()

    def buildLoadBox(self):
        # build the load label
        loadLable = Label(self, size_hint_weight=EXPAND_BOTH,
                          size_hint_align=FILL_HORIZ)
        loadLable.text = "<b>Processing</b>"
        loadLable.show()
        
        # build the spinning wheel
        wheel = Progressbar(self, pulse_mode=True,
                            size_hint_weight=EXPAND_BOTH,
                            size_hint_align=FILL_HORIZ)
        wheel.pulse(True)
        wheel.show()

        detailsbtn = Button(self, style="anchor")
        detailsbtn.text_set("Details")
        detailsbtn.callback_pressed_add(self.innerWinShow)
        detailsbtn.show()

        # build the status label
        self.statusLabel = Label(self, size_hint_weight=EXPAND_BOTH,
                                 size_hint_align=FILL_HORIZ)
        self.statusLabel.show()

        # put all the built objects in a vertical box
        box = Box(self, size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        box.pack_end(loadLable)
        box.pack_end(wheel)
        box.pack_end(self.statusLabel)        
        box.pack_end(detailsbtn)
        box.show()

        return box

    def buildMainBox(self):
        # build our toolbar
        self.mainTb = Toolbar(self, homogeneous=False,
                              size_hint_weight=(0.0, 0.0),
                              size_hint_align=(EVAS_HINT_FILL, 0.0))
        self.mainTb.item_append("remove", "Clear", self.clearPressed)
        self.mainTb.item_append("add", "Select All", self.selectAllPressed)
        self.mainTb.item_append("view-refresh", "Refresh", self.refreshPressed)
        self.mainTb.item_append("info", "Log", self.detailsPressed)
        self.mainTb.item_append("system-upgrade", "Apply", self.installUpdatesPressed)
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

    def detailsPressed(self, obj, it):
        it.selected = False
        self.innerWinShow()

    def clearPressed(self, obj, it):
        it.selected = False
        for rw in self.packageList.rows:
            rw[0].state = False
            self.app.checkChange(rw[0])

    def selectAllPressed(self, obj, it):
        it.selected = False
        for rw in self.packageList.rows:
            rw[0].state = True
            self.app.checkChange(rw[0])

    def refreshPressed(self, obj, it):
        it.selected = False
        self.app.refreshPackages()

    def installUpdatesPressed(self, obj, it):
        it.selected = False
        self.app.installUpdates()

    def packagePressed(self, obj):
        self.desFrame.text = "Description - %s" % obj.text
        self.currentDescription.text = obj.data["packageDes"]

    def addPackage(self, pak):
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
    def __init__(self):
        self.packagesToUpdate = {}
        self.apt = ThreadedAPT()

        #Takes status updates from apt to populate the GUI
        global progressque
        progressque = []

        self._timer = ecore.Timer(0.5, self.updateStatus)

        self.win = MainWin(self)

    def updateStatus(self):
        global progressque

        if len(progressque) > 0:
            for update in progressque:
                self.win.updateText.entry_append("%s"%update)
                self.win.updateText.entry_append("<br>")

            progressque = []

        return True

    def checkChange(self, obj):
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

    def installUpdates(self):
        if len(self.apt.cache.get_changes()) == 0:
            self.win.showDialog("Nothing to do",
                "No packages selected to upgrade.<br>" \
                "You must select at least one package from the list.")
            return
        self.win.statusLabel.text = "<i>Installing selected packages...</i>"
        self.win.flip.go(ELM_FLIP_ROTATE_YZ_CENTER_AXIS)
        self.apt.run("installUpdates", self.installUpdatesDone)

    def installUpdatesDone(self, result):
        self.win.statusLabel.text = "<i>Refreshing package lists...</i>"
        self.apt.run("refreshPackages", self.refreshPackagesDone)
        self.packagesToUpdate.clear()

    def refreshPackages(self):
        self.win.statusLabel.text = "<i>Refreshing package lists...</i>"
        self.win.flip.go(ELM_FLIP_ROTATE_YZ_CENTER_AXIS)

        self.apt.run("refreshPackages", self.refreshPackagesDone)
        self.packagesToUpdate.clear()

    def refreshPackagesDone(self, upgradables):
        # clear the packages list
        storerows = list(self.win.packageList.rows)
        for row in storerows:
            self.win.packageList.row_unpack(row, True)

        # populate the packages list
        for pak in upgradables:
            self.win.addPackage(pak)

        #self.win.innerWinHide()
        self.win.flip.go(ELM_FLIP_ROTATE_YZ_CENTER_AXIS)


if __name__ == "__main__":
    elementary.init()

    app = eepDater()
    app.refreshPackages()

    elementary.run()
    app.apt.shutdown()

    elementary.shutdown()
