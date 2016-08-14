import re
import os
import subprocess
import kaa
import kaa.utils
from kaa import encodingdef, consts
from kaa.keyboard import *
from kaa.ui.dialog import dialogmode
from kaa.filetype.default import modebase, keybind
from kaa.command import commandid
from kaa.command import norec
from kaa.command import norerun
from kaa.ui.selectlist import filterlist
from kaa.ui.selectfile import selectfile
from kaa.ui.itemlist import itemlistmode
from kaa.ui.pss import pssmode


class PssOption(modebase.SearchOption):
    RE = re

    def __init__(self):
        super().__init__()
        self.tree = True
        self.directory = '.'
        self.filenames = '*.*'
        self.encoding = 'utf-8'
        self.newline = 'auto'

    def clone(self):
        ret = super().clone()
        ret.tree = self.tree
        ret.directory = self.directory
        ret.filenames = self.filenames
        ret.encoding = self.encoding
        ret.newline = self.newline
        return ret

PssOption.LASTOPTION = PssOption()


PssDlgThemes = {
    'basic': [],
}


pssdlg_keys = {
    '\r': ('pssdlg.field.next'),
    '\n': ('pssdlg.field.next'),
    up: ('pssdlg.history'),
    tab: ('pssdlg.select-dir'),
}


class PssDlgMode(dialogmode.DialogMode):
    autoshrink = True

    KEY_BINDS = [
        keybind.cursor_keys,
        keybind.edit_command_keys,
        keybind.emacs_keys,
        keybind.macro_command_keys,
        pssdlg_keys,
    ]

    target = None

    def __init__(self, wnd=None):
        super().__init__()
        if isinstance(wnd.document.mode, pssmode.PssMode):
            PssOption.LASTOPTION = wnd.document.mode.pssoption
            self.target = wnd
        else:
            config = kaa.app.config

            if wnd and wnd.screen.selection.is_selected():
                f, t = wnd.screen.selection.get_selrange()
                s = wnd.document.gettext(f, t).split('\n')
                if s:
                    s = s[0].strip()
                    if s:
                        PssOption.LASTOPTION.text = s

            pssdir = config.hist('pss_dirname').get()
            if pssdir:
                PssOption.LASTOPTION.directory = pssdir[0][0]

        self.option = PssOption.LASTOPTION

    def close(self):
        super().close()

    def init_keybind(self):
        super().init_keybind()

        self.register_keys(self.keybind, self.KEY_BINDS)

    def init_themes(self):
        super().init_themes()
        self.themes.append(PssDlgThemes)

    def on_add_window(self, wnd):
        super().on_add_window(wnd)

        cursor = dialogmode.DialogCursor(wnd,
                                         [dialogmode.MarkRange('searchtext'),
                                          dialogmode.MarkRange('directory')])
        wnd.set_cursor(cursor)
        f, t = self.document.marks['searchtext']
        wnd.cursor.setpos(f)
        wnd.screen.selection.set_range(f, t)

    def build_document(self):
        with dialogmode.FormBuilder(self.document) as f:
            # search text
            f.append_text('caption', '   Search:')
            f.append_text('default', ' ')
            f.append_text('default', self.option.text, mark_pair='searchtext')
            f.append_text('default', '\n')

            # directory
            f.append_text('caption', 'Directory:')
            f.append_text('default', ' ')

            path = self.option.directory
            if path:
                p = kaa.utils.shorten_filename(path)
                path = p if len(p) < len(path) else path
            f.append_text('default', path, mark_pair='directory')
            f.append_text('default', '\n')
            
            """
            # filename
            f.append_text('caption', 'Filenames:')
            f.append_text('default', ' ')
            f.append_text('default', self.option.filenames,
                          mark_pair='filenames')
            f.append_text('default', '\n')
            """

            # working directory
            f.append_text('default', '(current dir)')
            f.append_text('default', ' ')
            f.append_text('default', os.getcwd())
            f.append_text('default', '\n')

            # buttons
            f.append_text('right-button', '[&Search]',
                          shortcut_style='right-button.shortcut',
                          on_shortcut=self.run_pss)

            f.append_text('right-button', '[&Ignore case]',
                          mark_pair='ignore-case',
                          on_shortcut=self.toggle_option_ignorecase,

                          shortcut_style='right-button.shortcut',
                          shortcut_mark='shortcut-i')

            self.update_option_style()
            kaa.app.messagebar.set_message(
                "Hit alt+S to begin search. Hit up to show history.")

    def _set_option_style(self, mark, style,
                          shortcutmark, shortcutstyle):
        f, t = self.document.marks[mark]
        self.document.setstyles(f, t, self.get_styleid(style))

        f = self.document.marks[shortcutmark]
        self.document.setstyles(f, f + 1, self.get_styleid(shortcutstyle))

    def _get_optionstylename(self, f):
        if f:
            return '.checked'
        else:
            return ''

    def update_option_style(self):
        style = self._get_optionstylename(self.option.ignorecase)
        self._set_option_style(
            'ignore-case', 'right-button' + style, 'shortcut-i',
            'right-button.shortcut' + style)

    def _option_updated(self):
        self.update_option_style()
        self.document.style_updated()

    def _select_dir(self, wnd):
        def cb(dir):
            wnd.set_visible(True)
            if dir:
                path = kaa.utils.shorten_filename(dir)
                self.set_dir(wnd, path)

        wnd.set_visible(False)
        dir = os.path.abspath(self.get_dir())
        selectfile.show_selectdir(dir, cb)

    @commandid('pssdlg.field.next')
    @norec
    @norerun
    def field_next(self, wnd):
        searchfrom, searchto = wnd.document.marks['searchtext']
        dirfrom, dirto = wnd.document.marks['directory']

        if searchfrom <= wnd.cursor.pos <= searchto:
            wnd.cursor.setpos(dirfrom)
            wnd.screen.selection.set_range(dirfrom, dirto)

        else:
            wnd.cursor.setpos(searchfrom)
            wnd.screen.selection.set_range(searchfrom, searchto)

    @commandid('pssdlg.history')
    @norec
    @norerun
    def pss_history(self, wnd):
        searchfrom, searchto = wnd.document.marks['searchtext']
        dirfrom, dirto = wnd.document.marks['directory']

        if searchfrom <= wnd.cursor.pos <= searchto:
            def callback(result):
                if result:
                    f, t = wnd.document.marks['searchtext']
                    wnd.document.replace(f, t, result)
                    wnd.cursor.setpos(f)
                    f, t = wnd.document.marks['searchtext']
                    wnd.screen.selection.set_range(f, t)

            filterlist.show_listdlg('Recent searches',
                                    [s for s,
                                        info in kaa.app.config.hist('pss_text').get(
                                        )],
                                    callback)

        else:
            def callback(result):
                if result:
                    f, t = wnd.document.marks['directory']
                    wnd.document.replace(f, t, result)
                    wnd.cursor.setpos(f)
                    f, t = wnd.document.marks['directory']
                    wnd.screen.selection.set_range(f, t)

            hist = []
            for p, info in kaa.app.config.hist('pss_dirname').get():
                path = kaa.utils.shorten_filename(p)
                hist.append(path if len(path) < len(p) else p)

            filterlist.show_listdlg('Recent directories',
                                    hist, callback)


    @commandid('pssdlg.select-dir')
    @norec
    @norerun
    def select_dir(self, wnd):
        f, t = self.document.marks['directory']
        if f <= wnd.cursor.pos <= t:
            self._select_dir(wnd)

    def toggle_option_tree(self, wnd):
        self.option.tree = not self.option.tree
        self._option_updated()

    def toggle_option_ignorecase(self, wnd):
        self.option.ignorecase = not self.option.ignorecase
        self._option_updated()

    def toggle_option_word(self, wnd):
        self.option.word = not self.option.word
        self._option_updated()

    def toggle_option_regex(self, wnd):
        self.option.regex = not self.option.regex
        self._option_updated()

    def _get_encnames(self):
        return sorted(encodingdef.encodings + ['japanese'],
                      key=lambda k: k.upper())

    def select_encoding(self, wnd):
        encnames = self._get_encnames()

        def callback(n):
            if n is None:
                return

            enc = encnames[n]
            if enc != self.option.encoding:
                self.option.encoding = enc
                f, t = self.document.marks['enc']
                # [Encoding:{mode}]
                # 01234567890    10
                self.document.replace(f + 10, t - 1, self.option.encoding)

        doc = itemlistmode.ItemListMode.build(
            'Select character encoding:',
            encnames,
            encnames.index(self.option.encoding),
            callback)

        kaa.app.show_dialog(doc)

    def get_search_str(self):
        f, t = self.document.marks['searchtext']
        return self.document.gettext(f, t)

    def get_dir(self):
        f, t = self.document.marks['directory']
        return self.document.gettext(f, t)

    def set_dir(self, wnd, dir):
        f, t = self.document.marks['directory']
        self.replace_string(
            wnd, f, t, dir, update_cursor=True)

    def run_pss(self, wnd):
        self.option.text = self.get_search_str()
        self.option.directory = self.get_dir()

        if (self.option.text and self.option.directory and
                self.option.filenames):

            kaa.app.config.hist('pss_text').add(self.option.text)
            path = os.path.abspath(os.path.expanduser(
                self.option.directory))
            kaa.app.config.hist('pss_dirname').add(path)

        wnd.get_label('popup').destroy()
#        TODO pss have problem in stream output lost group option
#        cmd = "pss --fte %s >~/fte.grp 2>&1" % (self.option.text) 
        cmd = "cd %s; grin --fte %s >~/fte.grp 2>&1" % (self.option.directory,self.option.text) 
#        cmd = "ag --fte %s >~/fte.grp 2>&1" % (self.option.text) 
        subprocess.check_output(cmd,shell=True,)
        kaa.app.messagebar.set_message("grep is done")

    def on_esc_pressed(self, wnd, event):
        wnd.get_label('popup').destroy()
        kaa.app.messagebar.set_message("")