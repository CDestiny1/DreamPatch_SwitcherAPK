[app]
title = Dream Patch Scoreboard Switcher
package.name = dreamscoreboards
package.domain = org.cein
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 2.0

requirements = python3,kivy,pyjnius

orientation = portrait
fullscreen = 0

# INTERNET para FTP. En Android 11+ MANAGE_EXTERNAL_STORAGE permite usar
# /ScoreboardsCein/ directamente en el almacenamiento interno (app sideload).
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a

# icon.filename = %(source.dir)s/icon.png

[buildozer]
log_level = 2
warn_on_root = 1
