Andriller CE (Community Edition)
=====
Andriller - is software utility with a collection of forensic tools for smartphones. It performs read-only, forensically sound, non-destructive acquisition from Android devices. It has features, such as powerful Lockscreen cracking for Pattern, PIN code, or Password; custom decoders for Apps data from Android (some Apple iOS & Windows) databases for decoding communications. Extraction and decoders produce reports in HTML and Excel formats.

## Features
- Automated data extraction and decoding
- Data extraction of non-rooted without devices by Android Backup (Android versions 4.x, varied/limited support)
- Data extraction with root permissions: root ADB daemon, CWM recovery mode, or SU binary (Superuser/SuperSU)
- Data parsing and decoding for Folder structure, Tarball files (from nanddroid backups), and Android Backup (_backup.ab_ files)
- Selection of individual database decoders for Android apps
- Decryption of encrypted WhatsApp archived databases (.crypt to .crypt12, must have the right _key_ file)
- Lockscreen cracking for Pattern, PIN, Password (not gatekeeper)
- Unpacking the Android backup files
- Screen capture of a device's display screen
---


## Python Requirements
- 3.6.x - 3.7.x


## Dependencies
- `adb`
- `python3-tk`

Install from Terminal (Debian based):
```bash
$ sudo apt-get install android-tools-adb python3-tk
```


## Installation (from source, editable)
```bash
$ pip install -e .
```


## Installation (from PYPI)
```bash
$ pip install andriller -U
```


## Quick Start (run GUI)
```bash
$ python -m andriller
```


## License
MIT License
