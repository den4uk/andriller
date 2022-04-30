CHANGELOG
===

### 3.6.3 (2022-04-30)

- Support for Python 3.10


### 3.6.2 (2022-04-29)

- Dependency pins for Jinja2 and MarkupSafe
- Tar extraction to local (from temp path, which can be limited in size)


### 3.6.1 (2021-10-31)

- Bugfix for the package gui modules not being included when building.


### 3.6.0 (2021-10-30)

- GUI restructured
- Bugfix with WA decoder
- Dependencies updated
- CI/CD pipelines changed to Github Actions
- Minor FB decoding bugfix when no stickers column is present


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
