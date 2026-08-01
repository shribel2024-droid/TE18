[app]
title = Daily Expense Tracker
package.name = dailyexpense
package.domain = org.expensetracker

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db

version = 1.0.0
requirements = python3,kivy==2.3.0,sqlite3,hostpython3

orientation = portrait
fullscreen = 0

# Android specific configurations
android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
