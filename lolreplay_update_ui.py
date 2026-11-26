"""Manual updater panel. All network and installation work runs in a child process."""
import json
from pathlib import Path
import sys
from PySide6.QtCore import Qt, QProcess
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QCheckBox, QComboBox, QPlainTextEdit, QMessageBox, QSizePolicy
from lolreplay_i18n import t
from lolreplay_updater import VERSION
from lolreplay_widgets import fit_combo

class UpdatePanel(QWidget):
    def __init__(self,window):
        super().__init__(window); self.window=window; self.mode=None; self.items=[]; self.installed=False
        self.setObjectName('updatePanel'); layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(10)
        self.current=QLabel(t('Installed version: {0}',VERSION)); self.current.setObjectName('section'); self.current.setWordWrap(True); layout.addWidget(self.current)
        info=QLabel(t('Updates are manual. Nothing is downloaded or installed without your approval.')); info.setWordWrap(True); layout.addWidget(info)
        self.experimental=QCheckBox(t('Include preview releases')); layout.addWidget(self.experimental)
        self.check=QPushButton(t('Check for updates')); self.check.clicked.connect(self.check_updates); layout.addWidget(self.check)
        self.versions=fit_combo(QComboBox()); self.versions.setAccessibleName(t('Available versions')); self.versions.currentIndexChanged.connect(self.select); layout.addWidget(self.versions)
        self.notes=QPlainTextEdit(); self.notes.setReadOnly(True); self.notes.setMinimumHeight(90); self.notes.setMaximumHeight(210); self.notes.setAccessibleName(t('Release notes')); layout.addWidget(self.notes)
        self.apply=QPushButton(t('Install selected version')); self.apply.setObjectName('primary'); self.apply.clicked.connect(self.confirm); self.apply.setEnabled(False); layout.addWidget(self.apply)
        self.status=QLabel(''); self.status.setTextFormat(Qt.TextFormat.PlainText); self.status.setWordWrap(True); self.status.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred); layout.addWidget(self.status)
        self.process=QProcess(self); self.process.finished.connect(self.finished); self.process.errorOccurred.connect(self.error); self.experimental.toggled.connect(self.clear)
    def busy(self): return self.mode is not None
    def clear(self,*args):
        self.items=[]; self.versions.clear(); self.notes.clear(); self.apply.setEnabled(False)
    def select(self,index):
        r=self.versions.currentData(); self.notes.setPlainText(r['notes'] if r else ''); self.apply.setEnabled(bool(r) and not self.busy() and not self.installed)
    def launch(self,mode,args):
        self.mode=mode; self.check.setEnabled(False); self.experimental.setEnabled(False); self.versions.setEnabled(False); self.apply.setEnabled(False); self.status.setText(t('Checking…') if mode=='check' else t('Downloading and installing…'))
        script=Path(__file__).resolve().with_name('lolreplay_updater.py')
        self.process.start(sys.executable,[str(script),*args,*(['--experimental'] if self.experimental.isChecked() else [])])
    def check_updates(self):
        if self.busy() or self.installed: return
        self.clear(); self.launch('check',['--json'])
    def confirm(self):
        r=self.versions.currentData()
        if not r or self.busy() or self.installed: return
        if self.window.editor.busy() or self.window.pending is not None:
            self.status.setText(t('Finish current operations before updating.')); return
        answer=QMessageBox.question(self,t('Install selected version'),t('Install {0} now? Save any wanted replay and stop capture first. Restart required.',r['tag']),QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
        if answer==QMessageBox.StandardButton.Yes:
            self.launch('install',[r['tag'],'--yes','--digest',r['digest']])
            self.window.centralWidget().setEnabled(False)
            for sc in self.window.shortcuts: sc.setEnabled(False)
    def restore_controls(self):
        self.mode=None; self.window.centralWidget().setEnabled(True);
        for sc in self.window.shortcuts: sc.setEnabled(self.window.prefs['keyboard_shortcuts'])
        self.check.setEnabled(not self.installed); self.experimental.setEnabled(not self.installed); self.versions.setEnabled(not self.installed); self.select(self.versions.currentIndex())
    def error(self,error):
        if error==QProcess.ProcessError.FailedToStart:
            self.restore_controls(); self.status.setText(t('Update failed.'))
    def finished(self,code,exit_status):
        mode=self.mode; out=bytes(self.process.readAllStandardOutput()).decode('utf-8','replace'); err=bytes(self.process.readAllStandardError()).decode('utf-8','replace')
        self.restore_controls()
        if code or exit_status!=QProcess.ExitStatus.NormalExit:
            self.status.setText(t('Update failed.')+'\n'+(err or out)[-3000:]); return
        if mode=='check':
            try: self.items=json.loads(out)
            except ValueError: self.status.setText(t('Update failed.')); return
            for r in self.items: self.versions.addItem(r['tag']+' · '+t('Preview release' if r['prerelease'] else 'Stable release'),r)
            self.status.setText(t('Choose a version to install.') if self.items else t('No eligible newer releases.'))
        elif mode=='install':
            self.installed=True; self.restore_controls(); self.current.setText(t('Update installed. Restart lolreplay.')); self.status.setText(t('Update installed. Restart lolreplay.'))
            QMessageBox.information(self,t('Updates'),t('Update installed. Restart lolreplay.'))
            self.window.close()
