from tkinter import messagebox
from . import __app_name__, __license__, __website__, __version__


def about_msg():
    return messagebox.showinfo(f'\
About {__app_name__}', f"\
Version: {__version__}\n\
License: {__license__}\n\
Copyright \u00A9 2012-2019\n\
Website: {__website__}")


def msg_do_backup():
    return messagebox.showwarning('Extraction via Backup method', '\
Attention!\n\
1. Unlock the screen;\n\
2. Tap on "Back up my data".\n\
Click OK to Continue\n\
(Extraction may take some time..)')


def screen_guide():
    return messagebox.showinfo('Usage Guide', '''
USAGE INSTRUCTIONS
- Works with Android versions 4.x and above.
- Connect a device via cable with USB debugging enabled.
- Press [Capture] to take a screen shot.
- Single captures can be saved.

REPORTING
- Select an output directory.
- Custom comments can be added with each capture.
- Tick [Remember] to reuse last comment.
- Captures can be taken just by pressing <Enter>.
- Press [Report] to generate and open a HTML report.''')


content_protect = "** Content Protection Enabled! **\nIt is not possible to capture this type of content."


GUIDE_WA = '''
This utility will decode multiple WhatsApp databases and produce combined messages on one report (without duplicates).
Use recovered and decrypted backup databases.

Instructions: Browse and select the folder with all "msgstore.db" (unencrypted and/or decrypted) databases.
'''


def select_output():
    return messagebox.showwarning(
        'Error!',
        "Select the 'Output' directory first!")


def device_not_detected():
    return messagebox.showwarning(
        'Device not detected!',
        '- Is an Android device connected?\n- Is USB Debugging enabled?\n- Are device Drivers installed?\n- Did you accept the RSA fingerprint?')


def license_applied(exp):
    return messagebox.showinfo(
        'License update',
        f'License code successfully written!\nExpiry date:{exp}\nPlease restart Andriller.')
