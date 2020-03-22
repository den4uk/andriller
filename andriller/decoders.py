import re
import json
import javaobj
import logging
import pathlib
import itertools
import collections
from . import utils
from .classes import AndroidDecoder

logger = logging.getLogger(__name__)
javaobj.utils._log.level = logging.WARNING


# -----------------------------------------------------------------------------
class SettingsDecoder(AndroidDecoder):
    TARGET = 'settings.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.android.providers.settings'
    exclude_from_menus = True

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        # TODO: template

    def main(self):
        table = 'secure'
        data_ = self.sql_table_as_dict(table)
        self.DICT = collections.ChainMap(*[self.name_val(d) for d in data_])
        keys_ = {
            'bluetooth_address': 'Bluetooth MAC',
            'bluetooth_name': 'Bluetooth Name',
            'android_id': 'Android ID',
            'lockscreen.password_salt': 'Lockscreen Salt',
        }
        for key, name in keys_.items():
            if key in self.DICT:
                item = self.DICT[key]
                # item['text'] = name
                self.DATA.append(item)


# -----------------------------------------------------------------------------
class LocksettingsDecoder(AndroidDecoder):
    TARGET = 'locksettings.db'
    target_is_db = True
    exclude_from_menus = True

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)

    def main(self):
        table = 'locksettings'
        self.DICT = collections.ChainMap(
            *[self.name_val(d) for d in self.sql_table_as_dict(table)])
        # self.DATA = list(self.DICT)

    @property
    def target_path_root(self):
        return f'/data/system/{self.TARGET}'

    @property
    def target_path_posix(self):
        return f'system/{self.TARGET}'


# -----------------------------------------------------------------------------
class AccountsDecoder(AndroidDecoder):
    TARGET = 'accounts.db'
    target_is_db = True

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'accounts.html'
        self.title = 'Accounts (System)'
        self.Titles = {
            '_id': 'Index',
            'type': 'Account type',
            'name': 'Username',
            'password': 'Password',
        }

    def main(self):
        table = 'accounts'
        self.DATA = list(self.sql_table_as_dict(table))

    @property
    def target_path_root(self):
        return f'/data/system/users/0/{self.TARGET}'

    @property
    def target_path_posix(self):
        return f'system/users/0/{self.TARGET}'


# -----------------------------------------------------------------------------
class WifiPasswordsDecoder(AndroidDecoder):
    TARGET = 'wpa_supplicant.conf'

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'wifi_passwords.html'
        self.title = 'Wi-Fi Passwords'
        self.Titles = {
            '_id': 'Index',
            'ssid': 'SSID',
            'psk': 'Password',
            'key_mgmt': 'Key Management',
            'priority': 'Priority',
        }

    def parse_wifi(self, rec: bytes) -> dict:
        d = self.to_chars(rec).split('\n\t')
        keys = (_.split('=')[0] for _ in d)
        vals = (_.split('=')[1].strip('"') for _ in d)
        return dict(zip(keys, vals))

    def main(self):
        rex = re.compile(b'network={\n\t(.+?)\n}', re.DOTALL)
        with open(self.input_file, 'rb') as R:
            for hit in rex.findall(R.read()):
                self.DATA.append(self.parse_wifi(hit))

    @property
    def target_path_root(self):
        return f'/data/misc/wifi/{self.TARGET}'

    @property
    def target_path_ab(self):
        return f'apps/com.android.providers.settings/f/{self.TARGET}'

    @property
    def target_path_posix(self):
        return f'/data/misc/wifi/{self.TARGET}'


class WifiPasswordsAbDecoder(WifiPasswordsDecoder):
    TARGET = 'flattened-data'
    exclude_from_menus = True


# -----------------------------------------------------------------------------
class WebViewDecoder(AndroidDecoder):
    TARGET = 'webview.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.android.browser'

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'web_passwords.html'
        self.title = 'WebView Browser Passwords'
        self.Titles = {
            '_id': 'Index',
            'host': 'Host',
            'username': 'Username',
            'password': 'Password',
        }

    def main(self):
        self.DATA = [*self.sql_table_as_dict('password')]


# -----------------------------------------------------------------------------
class BrowserHistoryDecoder(AndroidDecoder):
    TARGET = 'browser2.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.android.browser'

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'web_history.html'
        self.title = 'Android Browser History'
        self.Titles = {
            'id': 'Index',
            'title': 'Page title',
            'url': 'URL',
            'date': 'Last Time Visited',
            'visits': 'Frequency',
        }

    def main(self):
        table = 'history'
        kw = {'order_by': 'date'}
        for i in self.sql_table_as_dict(table, **kw):
            i['date'] = self.webkit_to_time(i['date'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class ChromeHistoryDecoder(BrowserHistoryDecoder):
    TARGET = 'History'
    NAMESPACE = 'app_chrome/Default'
    PACKAGE = 'com.android.chrome'
    target_is_db = True

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.title = 'Google Chrome History'

    def main(self):
        table = 'urls'
        for i in self.sql_table_as_dict(table, order_by='last_visit_time'):
            i['date'] = self.webkit_to_time(i['last_visit_time'])
            i['visits'] = i['visit_count']
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class ChromePasswordsDecoder(AndroidDecoder):
    TARGET = 'Login Data'
    NAMESPACE = 'app_chrome/Default'
    PACKAGE = 'com.android.chrome'
    target_is_db = True

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'chrome_passwords.html'
        self.title = 'Google Chrome Passwords'
        self.Titles = {
            '_id': 'Index',
            'origin_url': 'URL',
            'username_value': 'Username',
            'password_value': 'Password',
            'date_created': 'Date created',
        }

    def main(self):
        table = 'logins'
        for i in self.sql_table_as_dict(table, order_by='date_created'):
            i['password_value'] = self.safe_str(i['password_value'] or '')
            i['date_created'] = self.webkit_to_time(i['date_created'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class ChromeArchivedHistoryDecoder(ChromeHistoryDecoder):
    TARGET = 'Archived History'
    exclude_from_menus = True

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.title = 'Google Chrome Archived History'


# -----------------------------------------------------------------------------
class GenericCallsDecoder(AndroidDecoder):
    TARGET = 'contacts2.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.android.providers.contacts'

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'call_logs.html'
        self.title = 'Call Logs'
        self.Titles = {
            '_id': 'Index',
            'type': 'Type',
            'number': 'Number',
            'name': 'Name',
            'date': 'Time',
            'duration': 'Duration',
        }

    def main(self):
        table = 'calls'
        for i in self.sql_table_as_dict(table, order_by='date'):
            i['type'] = self.call_type(i['type'])
            i['number'] = self.parse_number(i['number'])
            i['date'] = self.unix_to_time_ms(i['date'])
            i['duration'] = self.duration(i['duration'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class SamsungCallsDecoder(GenericCallsDecoder):
    TARGET = 'logs.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.sec.android.provider.logsprovider'

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.title = 'Samsung Call Logs'

    def main(self):
        table = 'logs'
        kw = {'order_by': 'date', 'where': {'logtype': 100}}
        for i in self.sql_table_as_dict(table, **kw):
            i['type'] = self.call_type(i['type'])
            i['number'] = self.parse_number(i['number'])
            i['date'] = self.unix_to_time_ms(i['date'])
            i['duration'] = self.duration(i['duration'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class SamsungSnippetsDecoder(AndroidDecoder):
    TARGET = 'logs.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.sec.android.provider.logsprovider'

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'samsung_snippets.html'
        self.title = 'Samsung SMS Snippets'
        self.Titles = {
            '_id': 'Index',
            'number': 'Number',
            'name': 'Name',
            'm_content': 'Snippet',
            'type': 'Type',
            'date': 'Time',
        }

    def main(self):
        table = 'logs'
        kw = {'order_by': 'date', 'where': {'logtype': 300}}
        for i in self.sql_table_as_dict(table, **kw):
            i['type'] = self.sms_type(i['type'])
            i['number'] = self.parse_number(i['number'])
            i['date'] = self.unix_to_time_ms(i['date'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class SMSMMSDecoder(AndroidDecoder):
    TARGET = 'mmssms.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.android.providers.telephony'

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'sms_messages.html'
        self.title = 'SMS Messages'
        self.Titles = {
            '_id': 'Index',
            'address': 'Number',
            'body': 'Message',
            'date': 'Time',
            'type': 'Type'
        }

    def main(self):
        table = 'sms'
        for i in self.sql_table_as_dict(table, order_by=f'date'):
            i['address'] = self.parse_number(i['address'])
            i['date'] = self.unix_to_time_ms(i['date'])
            i['type'] = self.sms_type(i['type'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class WhatsAppContactsDecoder(AndroidDecoder):
    TARGET = 'wa.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.whatsapp'

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'whatsapp_contacts.html'
        self.title = 'WhatsApp Contacts'
        self.Titles = {
            '_id': 'Index',
            'display_name': 'Name',
            'number': 'Number',
            'status': 'Status',
        }

    def main(self):
        table = 'wa_contacts'
        kw = {'where': {'is_whatsapp_user': 1}, 'order_by': 'display_name'}
        for i in self.sql_table_as_dict(table, **kw):
            if not i['number']:
                continue
            i['display_name'] = i.get('display_name', '')
            i['status'] = i.get('status', '')
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class WhatsAppCallsDecoder(GenericCallsDecoder):
    TARGET = 'msgstore.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.whatsapp'

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.title = 'WhatsApp Calls'
        # _id, key_remote_jid, timestamp, key_from_me, media_duration

    @staticmethod
    def num(jid):
        return f"+{jid.split('@')[0]}"

    @staticmethod
    def call_type(from_me, duration):
        if from_me == 0 and duration == 0:
            return 'Missed'
        elif from_me == 0 and duration > 0:
            return 'Received'
        elif from_me == 1:
            return 'Dialled'
        else:
            return 'Unknown'

    def main(self):
        table = 'messages'
        kw = {'where': {'media_wa_type': 8}, 'order_by': 'timestamp'}
        for i in self.sql_table_as_dict(table, **kw):
            i['number'] = self.num(i['key_remote_jid'])
            # IDEA: try getting name from wa.db?
            i['date'] = self.unix_to_time_ms(i['timestamp'])
            i['type'] = self.call_type(i['key_from_me'], i['media_duration'])
            i['duration'] = self.duration(i['media_duration'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class WhatsAppMessagesDecoder(AndroidDecoder):
    TARGET = 'msgstore.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.whatsapp'

    def __init__(self, work_dir, input_file, **kwargs):
        self.owner = '(This device)'
        self.parts = collections.defaultdict(list)
        self.thumbs = {}
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'whatsapp_messages.html'
        self.title = 'WhatsApp Messages'
        self.Titles = {
            '_id': 'Index',
            'sender': 'Sender',
            'x_recipients': 'Recipient(s)',
            'x_message': 'Message',
            'type': 'Type',
            'timestamp': 'Time',
        }
        self.add_extra('sp', 'com.whatsapp_preferences.xml')
        self.add_extra('f', 'key')

    @staticmethod
    def num(jid):
        if jid == 'status@broadcast':
            return 'broadcast'
        return f"+{jid.split('@')[0]}"

    @staticmethod
    def key_jid(item, solo='s.whatsapp.net', with_domain=False):
        number, domain = item['key_remote_jid'].split('@')
        if with_domain:
            return f'+{number}', domain == solo  # False = group
        return 'broadcast' if number == 'status' else f'+{number}'

    def get_recipients(self, item):
        jid, solo = self.key_jid(item, with_domain=True)
        if item['key_from_me'] == 0 and solo:
            return [self.owner]
        return self.parts.get(item['key_remote_jid'], [jid])

    def get_sender(self, item):
        if item['key_from_me'] == 1:
            return self.owner
        else:
            jid, solo = self.key_jid(item, with_domain=True)
            return jid if solo else self.num(item['remote_resource'])

    def encode_raw_data(self, item):
        raw_data, key_id = item.get('raw_data'), item.get('key_id')
        if raw_data and item.get('raw_data'):
            return self.b64e(raw_data)
        if key_id and key_id in self.thumbs:
            return self.b64e(self.thumbs[key_id])

    def get_javaobj(self, item):
        if item.get('thumb_image'):
            return javaobj.loads(item['thumb_image'])

    def populate_chats(self):
        self.chats = {
            k: v for (k, v) in self.sql_table_rows(
                'chat_list',
                columns=('key_remote_jid', 'subject'),
                where={'!subject': ''},)}

    def populate_owner(self):
        prefs = self.get_neighbour('com.whatsapp_preferences.xml')
        if prefs:
            owner_num = self.xml_get_tag_text(prefs, 'string', 'name', 'registration_jid')
            if owner_num:
                self.owner = f'+{owner_num}'

    def populate_parts(self):
        # TODO: 'group_patricipants_history' table
        for g, j in self.sql_table_rows('group_participants', columns=('gjid', 'jid')):
            self.parts[g].append(self.num(j) if j else self.owner)

    def populate_broadcast(self):
        for d in self.sql_table_as_dict('message_thumbnails'):
            self.thumbs[d['key_id']] = d['thumbnail']

    def main(self):
        self.populate_chats()
        self.populate_owner()
        self.populate_parts()
        self.populate_broadcast()

        # Process main messages
        table = 'messages'
        kw = {'where': {'!status': [6, -1]}, 'order_by': 'timestamp'}
        for i in self.sql_table_as_dict(table, **kw):
            i['sender'] = self.get_sender(i)
            i['recipients'] = self.get_recipients(i)
            i['x_recipients'] = '\n'.join(i['recipients'])
            i['x_message'] = f"{i['data'] or ''}"
            i['timestamp'] = self.unix_to_time_ms(i['timestamp'])
            i['type'] = 'Sent' if i['key_from_me'] else 'Inbox'
            i['raw_data'] = self.encode_raw_data(i)
            data_obj = self.get_javaobj(i)
            if hasattr(data_obj, 'file') and hasattr(data_obj.file, 'path'):
                i['file_path'] = data_obj.file.path
            if hasattr(data_obj, 'fileSize') and data_obj.fileSize:
                i['file_size'] = utils.human_bytes(data_obj.fileSize)
            i['chat'] = self.chats.get(i['key_remote_jid'], self.key_jid(i))
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class KikMessagesDecoder(AndroidDecoder):
    TARGET = 'kikDatabase.db'
    RETARGET = '*.kikDatabase.db'
    NAMESPACE = 'db'
    PACKAGE = 'kik.android'

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'kik_messages.html'
        self.title = 'Kik Messages'
        self.Titles = {
            '_id': 'Index',
            'partner_jid': 'User ID',
            'display_name': 'Display Name',
            'body': 'Message',
            'type': 'Type',
            'timestamp': 'Time',
        }
        self.add_extra('sp', '*.KikPreferences.xml')

    def main(self):
        # Contacts table
        contacts = {
            d['jid']: d.get('display_name', '') for d in
            self.sql_table_as_dict('KIKcontactsTable')
        }

        table = 'messagesTable'
        kw = {'where': {'read_state': 500}, 'order_by': 'timestamp'}
        for i in self.sql_table_as_dict(table, **kw):
            i['display_name'] = contacts.get(i['partner_jid'], '{}')
            i['timestamp'] = self.unix_to_time_ms(i['timestamp'])
            i['type'] = 'Sent' if i['was_me'] else 'Inbox'
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class FacebookMessagesDecoder(AndroidDecoder):
    TARGET = 'threads_db2'
    NAMESPACE = 'db'
    PACKAGE = 'com.facebook.orca'
    target_is_db = True

    def __init__(self, work_dir, input_file, **kwargs):
        self.parts = collections.defaultdict(list)
        self.users = {}
        self.stickers = {}
        self.sql_tables = []
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'facebook_messages.html'
        self.title = 'Facebook Messenger'
        self.Titles = {
            '_id': 'Index',
            'sender': 'Sender',
            'user_key': 'Sender Account',
            'x_text': 'Message',
            'x_recipients': 'Recipients',
            'timestamp': 'Time',
        }
        self.add_extra('db', 'stickers_db')
        self.add_extra('db', 'stickers_db-journal')

    def process_users(self):
        def user_info(d):
            if not d.get('profile_pic_square'):
                return {}
            img = json.loads(d['profile_pic_square'])
            d['img_sml'] = img[0]['url']
            d['img_lrg'] = img[-1]['url']
            keys = ['username', 'name', 'img_sml', 'img_lrg', 'user_key', 'user_id']
            return {k: v for k, v in d.items() if k in keys}

        self.users = {d['user_key']: user_info(d) for d in self.sql_table_as_dict('thread_users')}

    @staticmethod
    def get_attach(item):
        attachments = item.get('attachments')
        if not attachments:
            return []
        attachments = json.loads(attachments)
        for n, a in enumerate(attachments):
            if 'urls' in a.keys():
                attachments[n]['urls'] = json.loads(a['urls'])
                for k, v in attachments[n]['urls'].items():
                    attachments[n]['urls'][k] = json.loads(v)
        return attachments

    @staticmethod
    def get_shares(item):
        shares = item.get('shares')
        if not shares:
            return []
        return json.loads(shares)

    def process_stickers(self):
        stickers_db = self.get_neighbour('stickers_db')
        if stickers_db:
            dec = AndroidDecoder(None, stickers_db, stage=True)
            for k, v in dec.sql_table_rows('stickers', columns=['id', 'uri']):
                self.stickers[k] = v

    def get_sticker(self, item):
        sticker = item['sticker_id']
        return self.stickers.get(sticker)

    def get_recipients(self, item):
        return [
            self.users.get(user_id, user_id) for user_id in
            self.parts.get(item['thread_key'], []) if
            user_id != item['user_id'] and user_id != item.get('user_key')
        ]

    def recipients_xls(self, items: list):
        return '\n'.join(f"{r.get('name','')} ({r.get('user_key','')})" for r in items)

    def process_parts(self):
        sql_tables = self.get_sql_tables()
        # Current structure (2019)
        if 'thread_participants' in sql_tables:
            for t, u in self.sql_table_rows('thread_participants', columns=['thread_key', 'user_key']):
                self.parts[t].append(u)
        # Legacy structute (~2015)
        elif 'threads' in sql_tables:
            thread_keys = {'thread_key', 'thread_id'}
            thread_key = set(self.get_table_columns('threads')) & thread_keys
            if thread_key:
                for t, p in self.sql_table_rows('threads', columns=[thread_key.pop(), 'participants']):
                    self.parts[t].extend([x['user_key'] for x in json.loads(p)])

    def main(self):
        # Process users, participants, stickers
        self.process_users()
        self.process_parts()
        self.process_stickers()

        # Process main messages
        table = 'messages'
        kw = {'where': {'msg_type': [0, 9]}, 'order_by': 'timestamp_ms'}
        for i in self.sql_table_as_dict(table, **kw):
            sender = json.loads(i['sender'])
            i['sender'] = sender['name']
            i['user_key'] = sender['user_key']
            i['user_id'] = sender['user_key'].split(':')[1]
            i['sender_info'] = self.users.get(i['user_key'], {})
            i['attachments'] = self.get_attach(i)
            i['shares'] = self.get_shares(i)
            i['sticker'] = self.get_sticker(i)
            i['recipients'] = self.get_recipients(i)
            i['timestamp'] = self.unix_to_time_ms(i['timestamp_ms'])
            i['x_recipients'] = self.recipients_xls(i['recipients'])
            i['x_text'] = i.get('text') or '<Media content>'
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class FacebookMessagesLiteDecoder(FacebookMessagesDecoder):
    TARGET = 'core.db'
    PACKAGE = 'com.facebook.mlite'

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.title = 'Facebook Messenger Lite'

    @staticmethod
    def user_info(d):
        return {
            'name': d['name'],
            'user_id': d['contact_user_id'],
            'user_key': d['contact_user_id'],
            'img_sml': d['profile_picture_url'],
            'img_lrg': d['profile_picture_url'],
        }

    def process_users(self):
        self.users = {
            d['contact_user_id']: self.user_info(d) for d in
            self.sql_table_as_dict('contact')
        }

    def process_stickers(self):
        for k, v in self.sql_table_rows(
                'stickers',
                columns=['sticker_id', 'preview_image_url']):
            self.stickers[k] = v

    def process_parts(self):
        for k, v in self.sql_table_rows(
                'thread_participant',
                columns=['participant_thread_key', 'participant_id']):
            self.parts[k].append(v)

    def main(self):
        self.process_users()
        self.process_parts()
        self.process_stickers()

        table = 'messages'
        for i in self.sql_table_as_dict(table, order_by='timestamp'):
            i['sender_info'] = self.users.get(i['user_id'], {})
            i['text'] = i['snippet']
            i['recipients'] = self.get_recipients(i)
            i['timestamp'] = self.unix_to_time_ms(i['timestamp'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class SkypeMessagesLegacyDecoder(AndroidDecoder):
    TARGET = 'main.db'
    NAMESPACE = 'files/*'  # * = <account_name>
    PACKAGE = 'com.skype.raider'

    def __init__(self, work_dir, input_file, **kwargs):
        self.convos = {}
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'skype_messages_legacy.html'
        self.title = 'Skype Messages (Legacy)'
        self.Titles = {
            'id': 'Index',
            'identity': 'Skype ID',
            'from_dispname': 'Name',
            'body_xml': 'Message',
            'chatmsg_status': 'Status',
            'type': 'Type',
            'timestamp': 'Time',
        }

    def process_convos(self):
        for c in self.sql_table_as_dict('Conversations'):
            self.convos[c['id']] = c['identity']

    def main(self):
        self.process_convos()

        table = 'Messages'
        kw = {'order_by': 'timestamp', 'where': {'chatmsg_type': 3}}
        for i in self.sql_table_as_dict(table, **kw):
            i['identity'] = self.convos.get(i['convo_id'], '')
            i['chatmsg_status'] = self.skype_msg_type(i['chatmsg_status'])
            i['type'] = 'Inbox' if i['author'] == i['identity'] else 'Sentbox'
            i['timestamp'] = self.unix_to_time(i['timestamp'])
            # i['timestamp__ms'] = self.unix_to_time_ms(i['timestamp__ms'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class SkypeMessagesDecoder(AndroidDecoder):
    RETARGET = '*.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.skype.raider'
    exclude_from_decoding = True

    def __init__(self, work_dir, input_file, **kwargs):
        self.owner = None
        self.owners = {}
        self.users = {}
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'skype_messages.html'
        self.title = 'Skype Messages'
        self.Titles = {
            '_id': 'Index',
            'x_sender': 'Sender',
            'x_conversation': 'Conversation',
            'content': 'Content',
            'direction': 'Direction',
            'time': 'Time',
        }

    def set_owner(self):
        users = list(self.sql_table_as_dict('user'))
        if users:
            self.owners = {u['entry_id']: u for u in users}
            self.owner = users[0].get('entry_id')

    def populate_users(self):
        for u in self.sql_table_as_dict('person'):
            self.users[u['entry_id']] = u

    def get_sender(self, item):
        if item['is_sender_me']:
            return self.owners.get(item['person_id'])
        else:
            return self.users.get(item['person_id'])

    @staticmethod
    def skype_name(s):
        return f"{s.get('first_name','')} {s.get('last_name','')} ({s.get('skype_name','')})"

    def get_convo(self, item):
        return self.users.get(item['conversation_link'])

    def main(self):
        self.set_owner()
        self.populate_users()

        table = 'chatItem'
        kw = {'where': {'message_type': [10, 11, 17]}, 'order_by': 'time'}
        for i in self.sql_table_as_dict(table, **kw):
            i['sender'] = self.get_sender(i)
            i['x_sender'] = self.skype_name(i['sender'])
            i['conversation'] = self.get_convo(i)
            i['x_conversation'] = self.skype_name(i['conversation'])
            # TODO: add skype_media.html snip
            i['direction'] = 'Outgoing' if i['is_sender_me'] else 'Incoming'
            i['time'] = self.unix_to_time_ms(i['time'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class SkypeCallsDecoder(SkypeMessagesDecoder):

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'skype_calls.html'
        self.title = 'Skype Calls'
        self.Titles = {
            '_id': 'Index',
            'type': 'Type',
            'x_sender': 'Caller',
            'x_conversation': 'Conversation',
            'time': 'Time',
            'duration': 'Duration',
        }

    def main(self):
        self.set_owner()
        self.populate_users()

        table = 'chatItem'
        kw = {'where': {'message_type': 3}, 'order_by': 'time'}
        for i in self.sql_table_as_dict(table, **kw):
            i['type'] = self.skype_call_type(i['type'])
            i['sender'] = self.get_sender(i)
            i['x_sender'] = self.skype_name(i['sender'])
            i['conversation'] = self.get_convo(i)
            i['x_conversation'] = self.skype_name(i['conversation'])
            time_ = i['time'] - i['duration']
            i['time'] = self.unix_to_time_ms(time_)
            i['duration'] = self.duration(i['duration'] // 1000)
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class ViberMessagesDecoder(AndroidDecoder):
    TARGET = 'viber_messages'
    NAMESPACE = 'db'
    PACKAGE = 'com.viber.voip'
    target_is_db = True

    def __init__(self, work_dir, input_file, **kwargs):
        self.parts = {}
        self.convo = collections.defaultdict(list)
        # self.tables = []
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'viber_messages.html'
        self.title = 'Viber Messages'
        self.Titles = {
            '_id': 'Index',
            'x_sender': 'Sender',
            'x_recipients': 'Recipient(s)',
            'body': 'Message',
            'send_type': 'Type',
            'msg_date': 'Time'
        }

    def populate_parts(self):
        parts_info = {d['_id']: d for d in self.sql_table_as_dict('participants_info')}
        for p in self.sql_table_as_dict('participants'):
            p_obj = parts_info.get(p['participant_info_id'], {})
            participant = {
                'number': p_obj.get('number') or '',
                'name': p_obj.get('display_name') or '',
            }
            self.convo[p['conversation_id']].append(participant)
            self.parts[p['_id']] = participant

    def get_part(self, item):
        return self.parts.get(item['participant_id'], {})

    def get_convo(self, item):
        sender = item['sender']
        recipients = self.convo.get(item['conversation_id'], [])[:]
        if sender in recipients:
            recipients.remove(sender)
        return recipients

    def main(self):
        self.populate_parts()

        artefacts_of_interest = ['Text', 'title', 'url', 'thumbnail', 'alt_text',
            'FileName', 'Title', 'URL', 'ThumbnailURL', 'ActionBody', 'Image']

        table = 'messages'
        kw = {'where': {'!token': 1}, 'order_by': 'msg_date'}
        for i in self.sql_table_as_dict(table, **kw):
            i['sender'] = self.get_part(i)
            i['x_sender'] = f"{i['sender'].get('number','')} ({i['sender'].get('name','')})"
            i['recipients'] = self.get_convo(i)
            i['x_recipients'] = '\n'.join(f"{r.get('number','')} ({r.get('name','')})" for r in i['recipients'])
            i['msg_info'] = json.loads(i['msg_info'])
            if i['msg_info']:
                i['media'] = utils.get_koi(i['msg_info'], artefacts_of_interest)
            i['send_type'] = 'Outgoing' if i['send_type'] else 'Incoming'
            i['msg_date'] = self.unix_to_time_ms(i['msg_date'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class ViberContactsDecoder(AndroidDecoder):
    TARGET = 'viber_data'
    NAMESPACE = 'db'
    PACKAGE = 'com.viber.voip'
    target_is_db = True

    def __init__(self, work_dir, input_file, **kwargs):
        self.pbook = {}
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'viber_contacts.html'
        self.title = 'Viber Contacts'
        self.Titles = {
            '_id': 'Index',
            'display_name': 'Name',
            'number': 'Number',
            'starred': 'Starred',
        }

    def populate_pbook(self):
        for p in self.sql_table_as_dict('phonebookdata'):
            self.pbook[p['contact_id']] = p

    def get_number(self, item):
        return self.pbook.get(item['_id'], {}).get('data1', '')

    def main(self):
        self.populate_pbook()

        table = 'phonebookcontact'
        kw = {'where': {'viber': 1}, 'order_by': 'display_name', 'order': 'ASC'}
        for i in self.sql_table_as_dict(table, **kw):
            i['number'] = self.get_number(i)
            i['starred'] = bool(i['starred'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class ViberCallsDecoder(GenericCallsDecoder):
    TARGET = 'viber_data'
    NAMESPACE = 'db'
    PACKAGE = 'com.viber.voip'
    target_is_db = True

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.title = 'Viber Calls'

    def main(self):
        table = 'calls'
        kw = {'order_by': 'date'}
        for i in self.sql_table_as_dict(table, **kw):
            i['type'] = self.call_type(i['type'])
            if i['viber_call_type'] == 4:
                i['type'] += ' (Video)'
            i['date'] = self.unix_to_time_ms(i['date'])
            i['duration'] = self.duration(i['duration'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class DownloadsDecoder(AndroidDecoder):
    TARGET = 'downloads.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.android.providers.downloads'

    def __init__(self, work_dir, input_file, **kwargs):
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'downloads.html'
        self.title = 'Download History'
        self.Titles = {
            '_id': 'Index',
            'uri': 'URL',
            '_data': 'Saved Data',
            'notificationpackage': 'Requesting App',
            'total_size': 'Size',
            'status': 'Status',
            'lastmod': 'Time',
        }

    def main(self):
        table = 'downloads'
        kw = {'order_by': 'lastmod'}
        for i in self.sql_table_as_dict(table, **kw):
            i['total_size'] = utils.human_bytes(i['total_bytes'])
            i['status'] = self.http_status(i['status'])
            i['lastmod'] = self.unix_to_time_ms(i['lastmod'])
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class AndroidCalendarDecoder(AndroidDecoder):
    TARGET = 'calendar.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.android.providers.calendar'

    def __init__(self, work_dir, input_file, **kwargs):
        self.accounts = {}
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'calendar.html'
        self.title = 'Android Calendar'
        self.Titles = {
            '_id': 'Index',
            'title': 'Title',
            'eventLocation': 'Location',
            'description': 'Description',
            'lastDate': 'Time',
            'dtstart': 'Start',
            'dtend': 'End',
            'account': 'Account'
        }

    def populate_accounts(self):
        for a in self.sql_table_as_dict('Calendars'):
            self.accounts[a['_id']] = f"{a['account_name']} ({a['name']})"

    def get_acc(self, item):
        return self.accounts.get(item['calendar_id'], 'Other')

    def main(self):
        self.populate_accounts()

        table = 'Events'
        kw = {'order_by': 'lastDate'}
        for i in self.sql_table_as_dict(table, **kw):
            for dobj in ['lastDate', 'dtstart', 'dtend']:
                if i.get(dobj):
                    i[dobj] = self.unix_to_time_ms(i[dobj])
            i['account'] = self.get_acc(i)
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class GooglePhotosDecoder(AndroidDecoder):
    TARGET = 'gphotos0.db'
    RETARGET = 'gphotos*.db'
    NAMESPACE = 'db'
    PACKAGE = 'com.google.android.apps.photos'

    def __init__(self, work_dir, input_file, **kwargs):
        self.local = {}
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'google_photos.html'
        self.title = 'Google Photos'
        self.Titles = {
            '_id': 'Index',
            'filename': 'File Name',
            'capture_timestamp': 'Capture Time',
            'lat_lon': 'GPS Coordinates',
            'camera': 'Camera',
            'local': 'Local Storage',
            'remote_url': 'Remote Link'
        }

    def populate_local(self):
        for x in self.sql_table_as_dict('local_media'):
            self.local[x['dedup_key']] = x

    def get_local(self, item):
        dup = item['dedup_key']
        return self.local.get(dup, {}).get('filepath', '')

    @staticmethod
    def get_gps(item):
        if item.get('latitude'):
            return '{latitude},{longitude}'.format(**item)

    @staticmethod
    def get_map(item):
        if item.get('lat_lon'):
            return f"https://maps.google.com/maps?q={item['lat_lon']}"

    @staticmethod
    def get_camera(item):
        if item.get('camera_make'):
            return '{camera_make} {camera_model}'.format(**item)

    def main(self):
        self.populate_local()

        table = 'remote_media'
        kw = {'order_by': 'capture_timestamp'}
        for i in self.sql_table_as_dict(table, **kw):
            i['capture_timestamp'] = self.unix_to_time_ms(i['capture_timestamp'])
            i['lat_lon'] = self.get_gps(i)
            i['map_uri'] = self.get_map(i)
            i['camera'] = self.get_camera(i)
            i['local'] = self.get_local(i)
            self.DATA.append(i)


# -----------------------------------------------------------------------------
# class TestDecoder(AndroidDecoder):
#     TARGET = 'my.db'
#     NAMESPACE = 'db'
#     PACKAGE = 'com.myapp'

#     def __init__(self, work_dir, input_file, **kwargs):
#         super().__init__(work_dir, input_file, **kwargs)
#         self.template_name = ''
#         self.title = ''
#         self.Titles = {}
#         self.add_extra('f', 'some.xml')

#     def main(self):
#         table = ''
#         kw = {}
#         for i in self.sql_table_as_dict(table, **kw):
#             i[''] = i['']
#             self.DATA.append(i)


# -----------------------------------------------------------------------------
class SharedFilesystemDecoder(AndroidDecoder):
    RETARGET = '*.ab'
    # TARGET = 'shared.ab'
    exclude_from_menus = True
    exclude_from_registry = True
    exp_match = r'^shared/\d/'

    def __init__(self, work_dir, input_file, **kwargs):
        self.tools = utils.DrillerTools()
        self.match = kwargs.get('match', self.exp_match)
        super().__init__(work_dir, input_file, **kwargs)
        self.template_name = 'shared_storage.html'
        self.title = 'Shared Storage'
        self.Titles = {
            '_id': 'Index',
            'directory': 'Directory',
            'fname': 'Filename',
            'size': 'Size',
            'mtime': 'Modified',
        }

    def process_ab(self):
        self.tar_file = self.tools.ab_to_tar(self.input_file)

    def main(self):
        self.process_ab()
        args = (self.tar_file, self.work_dir)
        for member in self.tools.extract_tar_members(*args, match=self.match):
            if not member.isfile() or not member.size:
                continue
            i = {}
            p = pathlib.PurePosixPath(member.path)
            i['full_path'] = p
            i['directory'] = p.parents[0]
            i['fname'] = p.name
            i['size'] = utils.human_bytes(member.size)
            i['mtime'] = self.unix_to_time(member.mtime)
            self.DATA.append(i)


# -----------------------------------------------------------------------------
class Registry:
    def __init__(self):
        self.decoders = {}
        self.populate()

    def populate(self):
        for obj in globals().values():
            if type(obj) == type and issubclass(obj, AndroidDecoder) and obj != AndroidDecoder:
                if obj.exclude_from_registry:
                    continue
                self.decoders[obj] = pathlib.PurePosixPath(obj.RETARGET or obj.TARGET)

    def has_target(self, target_file):
        target = pathlib.PurePosixPath(target_file)
        for x in self.decoders.values():
            if target.match(x.as_posix()):
                return True
        return False

    def decoders_target(self, target_file):
        decoders = []
        target = pathlib.PurePosixPath(target_file)
        for deco, x in self.decoders.items():
            if deco.exclude_from_decoding:
                continue
            if target.match(x.as_posix()):
                decoders.append(deco)
        return decoders

    # def decoders_package(self, package):
    #     return list(filter(lambda x: x.PACKAGE == package, self.decoders))

    @property
    def get_root_links(self):
        root_links = []
        for dec in self.decoders:
            dec = dec.staged()
            if dec.target_path_root:
                root_links.append(dec.get_artifact(dec.target_path_root))
                if dec.EXTRAS:
                    root_links.append(dec.get_extras())
        return sorted(set(itertools.chain(*root_links)))

    @property
    def get_ab_links(self):
        ab_links = []
        for dec in self.decoders:
            dec = dec.staged()
            if dec.target_path_ab:
                ab_links.append(dec.get_artifact(dec.target_path_ab))
                if dec.EXTRAS:
                    ab_links.append(dec.get_extras(is_ab=True))
        return sorted(set(itertools.chain(*ab_links)))

    @property
    def get_posix_links(self):
        posix_links = []
        for dec in self.decoders:
            dec = dec.staged()
            if dec.target_path_root:
                posix_links.append(dec.get_artifact(dec.target_path_posix))
                if dec.EXTRAS:
                    posix_links.append(dec.get_extras(is_posix=True))
        return sorted(set(itertools.chain(*posix_links)))

    @property
    def get_all_links(self):
        all_links = self.get_root_links
        all_links.extend(self.get_ab_links)
        return all_links


# -----------------------------------------------------------------------------
def parse_lockscreen_wal(file_path) -> tuple:
    with open(file_path, 'rb') as R:
        re_res = re.findall(b'_salt(\-?\d+)', R.read(), re.DOTALL)  # noqa: W605
        return tuple(set(map(int, re_res)))
    return tuple()
