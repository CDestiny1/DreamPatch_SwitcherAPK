# -*- coding: utf-8 -*-
"""
Dream Patch Scoreboard Switcher (Android -> PS4 por FTP)

- Escanea dinámicamente /ScoreboardsCein/ en el almacenamiento interno.
- Cada subcarpeta válida debe contener DreamPatch_Scoreboard.cpk.
- El usuario elige un marcador y la app lo sube a:
  /data/GoldHEN/AFR/CUSA18740/DreamPatch_Scoreboard.cpk
- Muestra progreso y verifica el tamaño remoto cuando el servidor FTP lo permite.
"""

import os
import json
import threading
from ftplib import FTP, error_perm, all_errors

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.clock import mainthread
from kivy.metrics import dp

CPK_FILENAME = "DreamPatch_Scoreboard.cpk"
REMOTE_DIR = "/data/GoldHEN/AFR/CUSA18740"
REMOTE_FILE = "DreamPatch_Scoreboard.cpk"
REMOTE_PATH = REMOTE_DIR + "/" + REMOTE_FILE
FTP_PORT_DEFAULT = 2121
CONFIG_FILENAME = "config.json"
LOCAL_ROOT_NAME = "ScoreboardsCein"


def get_scoreboards_dir():
    """Devuelve Almacenamiento interno/ScoreboardsCein."""
    try:
        from android.storage import primary_external_storage_path
        base = primary_external_storage_path()
    except Exception:
        base = os.path.expanduser("~")
    return os.path.join(base, LOCAL_ROOT_NAME)


def request_android_storage_access():
    """Pide el permiso adecuado según la versión de Android.

    En Android 11+ la app se distribuye por sideload y usa MANAGE_EXTERNAL_STORAGE
    para poder leer una carpeta simple en la raíz del almacenamiento interno.
    """
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE,
        ])
    except Exception:
        return

    try:
        from jnius import autoclass
        BuildVersion = autoclass("android.os.Build$VERSION")
        if int(BuildVersion.SDK_INT) < 30:
            return

        Environment = autoclass("android.os.Environment")
        if Environment.isExternalStorageManager():
            return

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        Uri = autoclass("android.net.Uri")

        activity = PythonActivity.mActivity
        package_name = activity.getPackageName()
        intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
        intent.setData(Uri.parse("package:" + package_name))
        activity.startActivity(intent)
    except Exception:
        # En algunos dispositivos el diálogo especial puede no existir.
        pass


class Config:
    def __init__(self, app):
        self.path = os.path.join(app.user_data_dir, CONFIG_FILENAME)
        self.data = {
            "ip": "",
            "port": FTP_PORT_DEFAULT,
            "user": "anonymous",
            "pass": "",
            "verified": False,
        }
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except Exception:
                pass

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)


def connect_ftp(config, timeout=10):
    ip = str(config.data.get("ip", "")).strip()
    port = int(config.data.get("port", FTP_PORT_DEFAULT))
    user = str(config.data.get("user", "anonymous") or "anonymous")
    password = str(config.data.get("pass", ""))

    if not ip:
        raise RuntimeError("Configura primero la IP de tu PS4.")
    if not (1 <= port <= 65535):
        raise RuntimeError("El puerto FTP no es válido.")

    ftp = FTP()
    ftp.connect(ip, port, timeout=timeout)
    ftp.login(user=user, passwd=password)
    ftp.set_pasv(True)
    ftp.cwd("/")
    return ftp


def cwd_absolute(ftp, path, create_missing=True):
    """Navega desde / hasta una ruta PS4 respetando mayúsculas/minúsculas."""
    ftp.cwd("/")
    for part in [p for p in path.split("/") if p]:
        try:
            ftp.cwd(part)
        except error_perm as exc:
            if not create_missing:
                raise RuntimeError("No existe la ruta remota: " + path) from exc
            try:
                ftp.mkd(part)
                ftp.cwd(part)
            except error_perm as mk_exc:
                raise RuntimeError(
                    "No se pudo acceder o crear '/{0}' en la PS4: {1}".format(part, mk_exc)
                ) from mk_exc


class SettingsScreen(Screen):
    def __init__(self, config, on_saved, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.on_saved = on_saved

        root = BoxLayout(orientation="vertical", padding=dp(22), spacing=dp(10))
        root.add_widget(Label(
            text="Dream Patch · Conexión PS4",
            font_size=dp(22),
            size_hint_y=None,
            height=dp(44),
        ))

        root.add_widget(Label(text="IP de la PS4", size_hint_y=None, height=dp(22)))
        self.ip_input = TextInput(
            text=self.config.data.get("ip", ""), multiline=False,
            hint_text="Ej. 192.168.1.50", size_hint_y=None, height=dp(46)
        )
        root.add_widget(self.ip_input)

        root.add_widget(Label(text="Puerto FTP", size_hint_y=None, height=dp(22)))
        self.port_input = TextInput(
            text=str(self.config.data.get("port", FTP_PORT_DEFAULT)),
            multiline=False, input_filter="int", size_hint_y=None, height=dp(46)
        )
        root.add_widget(self.port_input)

        root.add_widget(Label(text="Usuario FTP", size_hint_y=None, height=dp(22)))
        self.user_input = TextInput(
            text=self.config.data.get("user", "anonymous"),
            multiline=False, size_hint_y=None, height=dp(46)
        )
        root.add_widget(self.user_input)

        root.add_widget(Label(text="Contraseña (si aplica)", size_hint_y=None, height=dp(22)))
        self.pass_input = TextInput(
            text=self.config.data.get("pass", ""), multiline=False,
            password=True, size_hint_y=None, height=dp(46)
        )
        root.add_widget(self.pass_input)

        self.status = Label(text="", size_hint_y=None, height=dp(34))
        root.add_widget(self.status)

        buttons = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        test_btn = Button(text="Probar conexión")
        test_btn.bind(on_release=self.test_connection)
        save_btn = Button(text="Guardar y continuar")
        save_btn.bind(on_release=self.save)
        buttons.add_widget(test_btn)
        buttons.add_widget(save_btn)
        root.add_widget(buttons)
        root.add_widget(BoxLayout())
        self.add_widget(root)

    def _copy_inputs_to_config(self):
        new_ip = self.ip_input.text.strip()
        try:
            new_port = int(self.port_input.text.strip())
        except ValueError:
            new_port = FTP_PORT_DEFAULT
        new_user = self.user_input.text.strip() or "anonymous"
        new_pass = self.pass_input.text

        # Si cambia cualquier dato de conexión, la verificación anterior ya no aplica.
        changed = (
            new_ip != self.config.data.get("ip", "")
            or new_port != self.config.data.get("port", FTP_PORT_DEFAULT)
            or new_user != self.config.data.get("user", "anonymous")
            or new_pass != self.config.data.get("pass", "")
        )
        if changed:
            self.config.data["verified"] = False

        self.config.data["ip"] = new_ip
        self.config.data["port"] = new_port
        self.config.data["user"] = new_user
        self.config.data["pass"] = new_pass

    def save(self, *_):
        self._copy_inputs_to_config()
        self.config.save()
        self.on_saved()

    def test_connection(self, *_):
        self._copy_inputs_to_config()
        self.config.save()
        self.status.text = "Conectando..."
        threading.Thread(target=self._test_connection_worker, daemon=True).start()

    def _test_connection_worker(self):
        ftp = None
        try:
            ftp = connect_ftp(self.config, timeout=8)
            cwd_absolute(ftp, REMOTE_DIR, create_missing=False)
            self.config.data["verified"] = True
            self.config.save()
            self._set_status("✓ PS4 conectada y ruta encontrada")
        except Exception as exc:
            self.config.data["verified"] = False
            self.config.save()
            self._set_status("Error: " + str(exc))
        finally:
            if ftp is not None:
                try:
                    ftp.quit()
                except Exception:
                    try:
                        ftp.close()
                    except Exception:
                        pass

    @mainthread
    def _set_status(self, text):
        self.status.text = text


class MainScreen(Screen):
    def __init__(self, config, go_to_settings, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.go_to_settings = go_to_settings
        self.busy = False

        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(9))

        header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        header.add_widget(Label(text="Dream Patch Scoreboards", font_size=dp(20)))
        refresh = Button(text="Actualizar", size_hint_x=None, width=dp(105))
        refresh.bind(on_release=lambda *_: self.refresh_list())
        settings = Button(text="Ajustes", size_hint_x=None, width=dp(90))
        settings.bind(on_release=lambda *_: self.go_to_settings())
        header.add_widget(refresh)
        header.add_widget(settings)
        root.add_widget(header)

        self.connection_label = Label(text="", size_hint_y=None, height=dp(28))
        root.add_widget(self.connection_label)

        self.status_label = Label(text="", size_hint_y=None, height=dp(46))
        root.add_widget(self.status_label)

        self.progress = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(10))
        root.add_widget(self.progress)

        self.scroll = ScrollView()
        self.list_box = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(4)
        )
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        root.add_widget(self.scroll)

        root.add_widget(Label(
            text="Destino fijo: " + REMOTE_PATH,
            size_hint_y=None, height=dp(26), font_size=dp(12)
        ))
        self.add_widget(root)

    def on_pre_enter(self, *_):
        ip = self.config.data.get("ip", "")
        port = self.config.data.get("port", FTP_PORT_DEFAULT)
        self.connection_label.text = "PS4: {0}:{1}".format(ip or "sin configurar", port)
        self.refresh_list()

    def refresh_list(self):
        if self.busy:
            return

        self.list_box.clear_widgets()
        self.progress.value = 0
        base_dir = get_scoreboards_dir()

        try:
            os.makedirs(base_dir, exist_ok=True)
        except Exception as exc:
            self.status_label.text = "Sin acceso a almacenamiento: " + str(exc)
            return

        competitions = []
        try:
            names = sorted(os.listdir(base_dir), key=lambda s: s.lower())
        except Exception as exc:
            self.status_label.text = (
                "No puedo leer ScoreboardsCein. Concede acceso a todos los archivos.\n" + str(exc)
            )
            return

        for name in names:
            folder = os.path.join(base_dir, name)
            cpk_path = os.path.join(folder, CPK_FILENAME)
            if os.path.isdir(folder) and os.path.isfile(cpk_path):
                competitions.append((name, cpk_path, os.path.getsize(cpk_path)))

        if not competitions:
            self.status_label.text = (
                "No hay marcadores válidos. Crea carpetas dentro de:\n" + base_dir
            )
            return

        self.status_label.text = "{0} marcador(es) encontrado(s)".format(len(competitions))

        for name, cpk_path, size in competitions:
            row = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8))
            label = Label(text="{0}\n{1}".format(name, self._format_size(size)))
            row.add_widget(label)
            btn = Button(text="Instalar", size_hint_x=None, width=dp(110))
            btn.bind(on_release=lambda _b, n=name, p=cpk_path, s=size: self.confirm_apply(n, p, s))
            row.add_widget(btn)
            self.list_box.add_widget(row)

    @staticmethod
    def _format_size(size):
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024.0 or unit == "GB":
                return "{0:.1f} {1}".format(value, unit)
            value /= 1024.0

    def confirm_apply(self, name, cpk_path, size):
        if self.busy:
            return

        if not self.config.data.get("verified", False):
            self._show_unverified_warning(name, cpk_path, size)
            return

        self._show_confirm_popup(name, cpk_path, size)

    def _show_unverified_warning(self, name, cpk_path, size):
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        content.add_widget(Label(
            text=(
                "Aun no has probado la conexion con tu PS4.\n\n"
                "Si la ruta " + REMOTE_PATH + " no existe todavia,\n"
                "la app la creara sola y dira 'instalado' aunque\n"
                "el juego nunca lea ese archivo.\n\n"
                "Se recomienda ir a Ajustes y usar 'Probar conexion' primero."
            )
        ))
        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        popup = Popup(title="Conexion no verificada", content=content, size_hint=(0.92, 0.60))

        goto_btn = Button(text="Ir a Ajustes")
        anyway_btn = Button(text="Instalar de todos modos")
        cancel_btn = Button(text="Cancelar")
        buttons.add_widget(goto_btn)
        buttons.add_widget(anyway_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        cancel_btn.bind(on_release=lambda *_: popup.dismiss())
        goto_btn.bind(on_release=lambda *_: (popup.dismiss(), self.go_to_settings()))
        anyway_btn.bind(on_release=lambda *_: (popup.dismiss(), self._show_confirm_popup(name, cpk_path, size)))

        popup.open()

    def _show_confirm_popup(self, name, cpk_path, size):
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        content.add_widget(Label(
            text=(
                "¿Instalar '{0}'?\n\n"
                "Se reemplazará:\n{1}\n\nTamaño: {2}"
            ).format(name, REMOTE_PATH, self._format_size(size))
        ))
        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        popup = Popup(title="Confirmar marcador", content=content, size_hint=(0.92, 0.50))
        yes_btn = Button(text="Sí, instalar")
        no_btn = Button(text="Cancelar")
        buttons.add_widget(yes_btn)
        buttons.add_widget(no_btn)
        content.add_widget(buttons)
        no_btn.bind(on_release=lambda *_: popup.dismiss())
        yes_btn.bind(on_release=lambda *_: (popup.dismiss(), self.apply_scoreboard(name, cpk_path, size)))
        popup.open()

    def apply_scoreboard(self, name, cpk_path, expected_size):
        if self.busy:
            return
        if not self.config.data.get("ip", "").strip():
            self.status_label.text = "Configura primero la IP de la PS4."
            return

        self.busy = True
        self.progress.value = 0
        self.status_label.text = "Conectando con PS4..."
        threading.Thread(
            target=self._ftp_upload,
            args=(name, cpk_path, expected_size),
            daemon=True,
        ).start()

    def _ftp_upload(self, name, cpk_path, expected_size):
        ftp = None
        sent = [0]

        def on_chunk(chunk):
            sent[0] += len(chunk)
            if expected_size > 0:
                percent = min(100.0, sent[0] * 100.0 / expected_size)
                self._set_progress(percent, "Subiendo '{0}'... {1:.0f}%".format(name, percent))

        try:
            if not os.path.isfile(cpk_path):
                raise RuntimeError("El CPK seleccionado ya no existe.")

            local_size = os.path.getsize(cpk_path)
            ftp = connect_ftp(self.config, timeout=12)
            self._set_status("PS4 conectada. Preparando destino...")
            cwd_absolute(ftp, REMOTE_DIR, create_missing=True)

            with open(cpk_path, "rb") as f:
                ftp.storbinary("STOR " + REMOTE_FILE, f, blocksize=128 * 1024, callback=on_chunk)

            # Verificación de tamaño; algunos servidores FTP no soportan SIZE.
            verified = False
            remote_size = None
            try:
                ftp.sendcmd("TYPE I")
                remote_size = ftp.size(REMOTE_FILE)
                if remote_size is not None:
                    if int(remote_size) != int(local_size):
                        raise RuntimeError(
                            "La subida terminó, pero el tamaño remoto no coincide "
                            "({0} != {1}).".format(remote_size, local_size)
                        )
                    verified = True
            except error_perm:
                pass

            self._set_progress(100, "✓ '{0}' instalado correctamente".format(name))
            if verified:
                self._set_status("✓ Instalado y verificado: " + name)
            else:
                self._set_status("✓ Instalado: " + name + " (servidor sin verificación SIZE)")

        except all_errors as exc:
            self._set_status("Error FTP: " + str(exc))
        except Exception as exc:
            self._set_status("Error: " + str(exc))
        finally:
            if ftp is not None:
                try:
                    ftp.quit()
                except Exception:
                    try:
                        ftp.close()
                    except Exception:
                        pass
            self._finish_upload()

    @mainthread
    def _set_status(self, text):
        self.status_label.text = text

    @mainthread
    def _set_progress(self, value, text=None):
        self.progress.value = value
        if text:
            self.status_label.text = text

    @mainthread
    def _finish_upload(self):
        self.busy = False


class ScoreboardSwitcherApp(App):
    def build(self):
        request_android_storage_access()
        self.config_obj = Config(self)
        self.sm = ScreenManager()
        self.main_screen = MainScreen(self.config_obj, self.go_to_settings, name="main")
        self.settings_screen = SettingsScreen(self.config_obj, self.go_to_main, name="settings")
        self.sm.add_widget(self.main_screen)
        self.sm.add_widget(self.settings_screen)
        self.sm.current = "settings" if not self.config_obj.data.get("ip") else "main"
        return self.sm

    def on_resume(self):
        # Al volver de Ajustes de Android (permiso de archivos), refresca la lista.
        try:
            if self.sm.current == "main":
                self.main_screen.refresh_list()
        except Exception:
            pass
        return True

    def go_to_settings(self):
        self.sm.current = "settings"

    def go_to_main(self):
        self.sm.current = "main"


if __name__ == "__main__":
    ScoreboardSwitcherApp().run()
