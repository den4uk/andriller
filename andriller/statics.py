WHATSAPP_CRYPT = '''
Utility for WhatsApp crypt databases decryption.

Encrypted databases are usually located here:
/sdcard/WhatsApp/Databases/

The `key` file must be obtained from the following location:
/data/data/com.whatsapp/files/key
(Must have root permissions to read this file)

Supported crypt files with the following extensions:
- *.crypt7
- *.crypt8
- *.crypt9
- *.crypt10
- *.crypt11
- *.crypt12

Instructions:
- Browse to select the directory with crypt files.
- Browse to select the `key` file.
- Secelt individual databases or all to decrypt.
- Databases will be decrypted to the same directory.
'''

GUIDE_WA = '''
This utility will decode multiple WhatsApp databases and produce combined messages on one report (without duplicates).
Use recovered and decrypted backup databases.

Instructions: Browse and select the folder with all "msgstore.db" (unencrypted and/or decrypted) databases.
'''

DEFAULT_HEADER = '<font color="#FF0000" size=""># This report was generated using Andriller CE # (This field is editable in Preferences)</font>'

DEFAULT_FOOTER = '<i># andriller.com # (This field is editable in Preferences)</i>'
