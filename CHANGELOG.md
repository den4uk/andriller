CHANGELOG
===

### 3.5.3 (2020-11-17)

- Bugfix related to file size retrieval from the remote device.
- File pull bug using adb (with root), affecting Windows.
- Improvements for backwards support on older Android versions.


### 3.5.2 (2020-10-28)

- Switched timeouts to `wrapt_timeout_decorator` to fix bug with Python 3.8


### 3.5.1 (2020-10-15)

- Critical fix in WhatsApp crypt decoding.
- Improved SQLite database handling on erroneous text entries.
- Bugfix in decoding databases containing additional sources, which affected decoders for: "Facebook", "Kik", "WhatsApp".
- Bugfix date decoding in "Android Browser History".
- Added Python 3.9 to the tox test suite.
