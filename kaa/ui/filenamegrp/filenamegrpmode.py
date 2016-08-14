import os
import kaa
from kaa import doc_re
from kaa import document
from kaa.keyboard import *
from kaa.theme import Style
from kaa.filetype.default import defaultmode
from kaa.command import commandid
from kaa.command import norec
from kaa.command import norerun
from kaa.filetype.default import modebase

FilenameGrpThemes = {
    'basic': [
        Style('filenamegrp-filename', 'Green', 'Default'),
        Style('filenamegrp-lineno', 'Green', 'Default'),
    ],
}

filenamegrp_keys = {
    '\r': ('filenamegrp.showmatch'),
    '\n': ('filenamegrp.showmatch'),
}


class FilenameGrpMode(defaultmode.DefaultMode):
    # todo: rename key/command names
    DOCUMENT_MODE = False
    USE_UNDO = False
    HIGHLIGHT_CURSOR_ROW = True

    FILENAMEGRP_KEY_BINDS = [
        filenamegrp_keys,
    ]

    encoding = None
    newline = None

    def init_themes(self):
        super().init_themes()
        self.themes.append(FilenameGrpThemes)

    def init_keybind(self):
        super().init_keybind()
        self.register_keys(self.keybind, self.FILENAMEGRP_KEY_BINDS)

    def _locate_doc(self, wnd, doc, lineno):
        wnd.show_doc(doc)

        pos = doc.get_lineno_pos(lineno)
        tol = doc.gettol(pos)
        wnd.cursor.setpos(wnd.cursor.adjust_nextpos(wnd.cursor.pos, tol))
        wnd.activate()

    @commandid('filenamegrp.showmatch')
    @norec
    @norerun
    def show_hit(self, wnd):
        grp_lineno = "1"
        grp_filename = ""

        def lookup_lineno():
            grp_lineno, xxx = line.split(':', 1)
            return grp_lineno
        
        def lookup_filename():
            grp_filename = ""
            storeTEXT = ""
            start = wnd.cursor.pos
            if modebase.SearchOption.LAST_SEARCH.text:
                storeTEXT =  modebase.SearchOption.LAST_SEARCH.text
            modebase.SearchOption.LAST_SEARCH.text = "File:"
            ret = wnd.document.mode.search_prev(start, modebase.SearchOption.LAST_SEARCH)
            if ret:
                f, t = ret.span()
                wnd.cursor.setpos(f)
                wnd.screen.selection.set_range(f, t)
                pos = wnd.cursor.pos
                tol = self.document.gettol(pos)
                eol, line = self.document.getline(tol)
                wnd.cursor.pos = start
                wnd.screen.selection.clear()
                if storeTEXT:
                    modebase.SearchOption.LAST_SEARCH.text = storeTEXT
                try:
                    grp_filename, xxx = line.split(':', 1)
                    if grp_filename == "File":
                        grp_filename = xxx[1:-1]
                except ValueError:
                    grp_filename =""

            return grp_filename

        pos = wnd.cursor.pos
        tol = self.document.gettol(pos)
        eol, line = self.document.getline(tol)
        #kaa.app.messagebar.set_message(line)
        try:
            filename, linexxx = line.split(':', 1)
        except ValueError:
            return

        if filename!="File":
            grp_lineno= lookup_lineno()
            if not grp_filename:
                filename = lookup_filename()
        else:
            filename = linexxx[1:-1]
        lineno = int(grp_lineno)

        if not filename:
             return

        doc = kaa.app.storage.openfile(filename)
        #editor = kaa.app.show_doc(doc)
        #kaa.app.messagebar.set_message("")
        buddy = wnd.splitter.get_buddy()
        if not buddy:
            buddy = wnd.splitter.split(vert=False, doc=doc)
            self._locate_doc(buddy.wnd, doc, lineno)
        else:
            if buddy.wnd and buddy.wnd.document is doc:
                self._locate_doc(buddy.wnd, doc, lineno)
                return

            def callback(canceled):
                if not canceled:
                    buddy.show_doc(doc)
                    self._locate_doc(buddy.wnd, doc, lineno)
            kaa.app.app_commands.save_splitterdocs(wnd, buddy, callback)


    RE_FILENAME = doc_re.compile(
            r'(?P<FILENAME>^[^:\n]+)\:.*$',
        doc_re.M | doc_re.X)

    def is_match(self, pos):
        m = self.RE_FILENAME.match(self.document, pos)
        return m

    def on_global_prev(self, wnd):
        if kaa.app.focus in self.document.wnds:
            if self.is_match(self.document.gettol(wnd.cursor.pos)):
                self.show_hit(kaa.app.focus)
                return True

        pos = wnd.cursor.pos

        while True:
            eol = self.document.gettol(pos)
            if eol:
                tol = self.document.gettol(eol - 1)
            else:
                eol = self.document.endpos()
                tol = self.document.gettol(eol)

            if self.is_match(tol):
                wnd.cursor.setpos(tol)
                self.show_hit(wnd)
                return True

            if tol == 0:
                wnd.cursor.setpos(tol)
                self.document.wnds[0].activate()
                return True

            pos = tol

    def on_global_next(self, wnd):
        if kaa.app.focus in self.document.wnds:
            if self.is_match(self.document.gettol(wnd.cursor.pos)):
                self.show_hit(kaa.app.focus)
                return True

        pos = wnd.cursor.pos
        while True:
            tol = self.document.geteol(pos)
            m = self.is_match(tol)
            if m:
                wnd.cursor.setpos(tol)
                self.show_hit(wnd)
                return True

            if self.document.geteol(tol) == self.document.endpos():
                wnd.cursor.setpos(0)
                self.document.wnds[0].activate()
                return True

            pos = tol
