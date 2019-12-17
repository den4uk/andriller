Andriller CE (Community Edition)
=====
[![Build Status](https://travis-ci.org/den4uk/andriller.svg?branch=master)](https://travis-ci.org/den4uk/andriller)
[![License](https://img.shields.io/github/license/den4uk/andriller.svg)](https://pypi.python.org/pypi/andriller)
[![PyPI Version](http://img.shields.io/pypi/v/andriller.svg)](https://pypi.python.org/pypi/andriller)
![Twitter Follow](https://img.shields.io/twitter/follow/den4uk?style=social)

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
- 3.6+


## System Dependencies
- `adb`
- `python3-tk`

[Ubuntu/Debian] Install from Terminal:
```bash
$ sudo apt-get install android-tools-adb python3-tk
```

[Mac] Install from brew cask:
```bash
$ brew cask install android-platform-tools
```

[Windows] : _Included._


## Installation (from PYPI, recommended)
```bash
$ pip install andriller -U
```


## Installation (from source, editable)
```bash
$ pip install -e .
```


## Quick Start (run GUI)
```bash
$ python -m andriller
```


## License
MIT License


## Contrinuting
Contributions are welcome, please make your pull requests to the `dev` branch of the repository.


## Bug Tracker
Bugs and issues can be submitted in the ([Issues](https://github.com/den4uk/andriller/issues)) section.


## Donations
You may make donations to the projects, or you can also just _buy me a beer_:

[![Donate](https://www.paypalobjects.com/en_US/GB/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=\_s-xclick&hosted\_button\_id=8AHFL65LMTLLE&source=url)
