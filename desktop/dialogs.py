"""Owned WinForms dialogs marshalled to the window's GUI thread.

No JavaScript, argv/env credential source, persistent password or key exports.
Clearing controls/references is best effort, not Python/.NET memory zeroization.
"""
from threading import Event


def validate_password(password, confirmation, *, creating):
    from vault_crypto import _encode_password
    from vault_format import VaultPasswordError
    _encode_password(password, creating=creating)
    if creating and password != confirmation:
        raise VaultPasswordError()


class NativeDialogs:
    def __init__(self, window):
        self._window = window
        self._closed = Event()
        self._active = None  # Only the GUI thread accesses/disposes this dialog.

    def _on_gui(self, function):
        if self._closed.is_set():
            return None
        from System import Action
        done, result, failed = Event(), [], []
        def execute():
            try:
                if not self._closed.is_set():
                    result.append(function())
            except Exception:
                failed.append(True)
            finally:
                done.set()
        native = self._window.native
        native.BeginInvoke(Action(execute))
        while not done.wait(0.1):
            if self._closed.is_set():
                return None
        if failed:
            raise RuntimeError("Native dialog unavailable") from None
        return result[0] if result and not self._closed.is_set() else None

    def close(self):
        self._closed.set()
        # Nonblocking: pywebview's closing event runs on the GUI thread.
        try:
            from System import Action
            def cancel():
                if self._active is not None:
                    self._active.Dispose()
            self._window.native.BeginInvoke(Action(cancel))
        except Exception:
            pass

    def choose_file(self, *, creating):
        return self._on_gui(lambda: self._file_dialog(creating))

    def password(self, *, creating):
        return self._on_gui(lambda: self._password_dialog(creating))

    def choose_pdf(self):
        return self._on_gui(lambda: self._pdf_dialog(None))

    def choose_pdf_output(self, suggested_name):
        return self._on_gui(lambda: self._pdf_dialog(suggested_name))

    def _pdf_dialog(self, suggested_name):
        from System.Windows.Forms import DialogResult, OpenFileDialog, SaveFileDialog
        from .pdf_io import output_choice
        saving = suggested_name is not None
        dialog = SaveFileDialog() if saving else OpenFileDialog()
        approved = []
        try:
            self._active = dialog
            dialog.Title = 'HybridSign — Save signed PDF' if saving else 'HybridSign — Choose unsigned PDF'
            dialog.Filter = 'PDF document (*.pdf)|*.pdf'
            dialog.DefaultExt, dialog.AddExtension = 'pdf', True
            dialog.RestoreDirectory = dialog.CheckPathExists = True
            if saving:
                dialog.FileName, dialog.OverwritePrompt = suggested_name, True
                def file_ok(_, event):
                    try:
                        approved.clear()
                        approved.append(output_choice(str(dialog.FileName)))
                    except Exception:
                        event.Cancel = True
                dialog.FileOk += file_ok
            else:
                dialog.CheckFileExists, dialog.Multiselect = True, False
            if dialog.ShowDialog(self._window.native) != DialogResult.OK: return None
            return approved[0] if saving and approved else None if saving else str(dialog.FileName)
        finally:
            self._active = None
            dialog.Dispose()

    def signing_close_notice(self):
        """GUI closing event only; do not marshal/join from this callback."""
        from System.Windows.Forms import MessageBox
        MessageBox.Show(self._window.native,
                        'Signing is in progress. Wait for its result before closing. Publication cannot be cancelled here.',
                        'HybridSign — Signing in progress')

    def _file_dialog(self, creating):
        from System.Windows.Forms import DialogResult, OpenFileDialog, SaveFileDialog
        dialog = SaveFileDialog() if creating else OpenFileDialog()
        try:
            self._active = dialog
            dialog.Title = "HybridSign — Save a new encrypted vault" if creating else "HybridSign — Open encrypted vault"
            dialog.Filter = "Encrypted hybrid vault (*.hvault)|*.hvault|All files (*.*)|*.*"
            dialog.DefaultExt = "hvault"
            dialog.AddExtension = True
            dialog.RestoreDirectory = True
            dialog.CheckPathExists = True
            if creating:
                dialog.OverwritePrompt = False  # Existing destinations always reject in the worker.
            else:
                dialog.CheckFileExists = True
                dialog.Multiselect = False
            return str(dialog.FileName) if dialog.ShowDialog(self._window.native) == DialogResult.OK else None
        finally:
            self._active = None
            dialog.Dispose()

    def _build_password_dialog(self, creating):
        from System.Windows.Forms import Form
        form = Form()
        try:
            return self._configure_password_dialog(form, creating)
        except Exception:
            form.Dispose()
            raise

    def _configure_password_dialog(self, form, creating):
        from System.Drawing import Point, Size
        from System.Windows.Forms import (AutoScaleMode, Button, DialogResult,
                                         FormBorderStyle, FormStartPosition, Label, TextBox)
        form.Text = "HybridSign — Create encrypted vault" if creating else "HybridSign — Unlock encrypted vault"
        form.ClientSize = Size(510, 285 if creating else 235)
        form.FormBorderStyle = FormBorderStyle.FixedDialog
        form.StartPosition = FormStartPosition.CenterParent
        form.AutoScaleMode = AutoScaleMode.Dpi
        form.MinimizeBox = form.MaximizeBox = False
        form.ShowInTaskbar = False
        label = Label()
        label.Text = "Password stays in local Python/.NET memory; never sent to the web UI."
        label.AutoSize = False
        label.Location, label.Size = Point(18, 15), Size(475, 36)
        form.Controls.Add(label)
        boxes = []
        for index, caption in enumerate(["New password (15+ characters)", "Confirm password"] if creating else ["Vault password"]):
            label = Label()
            label.Text, label.AutoSize = caption, True
            label.Location = Point(18, 60 + 58 * index)
            box = TextBox()
            box.UseSystemPasswordChar, box.MaxLength = True, 1024
            box.Name = "vault-password" if index == 0 else "vault-password-confirm"
            box.Location, box.Size = Point(18, 80 + 58 * index), Size(470, 25)
            form.Controls.Add(label)
            form.Controls.Add(box)
            boxes.append(box)
        error = Label()
        error.AutoSize = False
        error.Location, error.Size = Point(18, 180 if creating else 125), Size(470, 42)
        form.Controls.Add(error)
        ok, cancel = Button(), Button()
        ok.Text = "Create Vault" if creating else "Unlock Vault"
        cancel.Text, cancel.DialogResult = "Cancel", DialogResult.Cancel
        y = 240 if creating else 190
        ok.Location, ok.Size = Point(270, y), Size(115, 30)
        cancel.Location, cancel.Size = Point(395, y), Size(93, 30)
        form.Controls.Add(ok)
        form.Controls.Add(cancel)
        form.AcceptButton, form.CancelButton = ok, cancel
        return form, boxes, error, ok

    def _password_dialog(self, creating):
        from System.Windows.Forms import DialogResult
        from vault_format import VaultPasswordError
        form, boxes, error, ok = self._build_password_dialog(creating)
        selected = []
        def submit(*_):
            password = str(boxes[0].Text)
            confirmation = str(boxes[1].Text) if creating else None
            try:
                validate_password(password, confirmation, creating=creating)
            except VaultPasswordError:
                error.Text = "Passwords must match. New passwords need 15+ characters; maximum 1024 UTF-8 bytes." if creating else "Enter a nonempty password of at most 1024 UTF-8 bytes."
                return
            selected.append(password)
            form.DialogResult = DialogResult.OK
            form.Close()
        try:
            self._active = form
            ok.Click += submit
            accepted = form.ShowDialog(self._window.native) == DialogResult.OK
            return selected[0] if accepted and selected and not self._closed.is_set() else None
        finally:
            try:
                for box in boxes:
                    if not box.IsDisposed:
                        box.Clear()
            finally:
                selected.clear()
                self._active = None
                form.Dispose()
