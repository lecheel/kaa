import kaa
import os
from kaa import document
from kaa.ui.filenamegrp import filenamegrpmode

def show(self):
    mode = PssMode()
    doc = kaa.app.storage.openfile(mode.DEFAULT_GRP)
    doc.setmode(mode)
    mode = doc.mode
    style_filename = mode.get_styleid('filenamegrp-filename')
    style_lineno = mode.get_styleid('filenamegrp-lineno')

    for m in mode.RE_FILENAME.finditer(doc):
        f, t = m.span('FILENAME')
        doc.setstyles(f, t, style_filename, update=False)

    kaa.app.show_doc(doc)


class PssMode(filenamegrpmode.FilenameGrpMode):
    DEFAULT_GRP = os.getenv("HOME")+"/fte.grp"
    MODENAME = 'Pss'


"""
example 
~/fte.grp
grep in group view like Ag/Ack/sift/grin/pss with full path for reuse
pss fork on https://github.com/lecheel/pss/tree/lestyle
grin fork on https://github.com/lecheel/grin
----
File: /home/foo/work/foo.py
12:   qweer foo
24:   qazwsx foo
"""
