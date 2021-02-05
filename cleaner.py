from time import sleep
from os import getenv

from pyrogram import Client
from pyrogram.raw.functions.messages import Search
from pyrogram.raw.types import InputPeerSelf, InputMessagesFilterEmpty
from pyrogram.raw.types.messages import ChannelMessages
from pyrogram.errors import FloodWait, UnknownError


API_ID = getenv('API_ID', None) or int(input('Enter your Telegram API id: '))
API_HASH = getenv('API_HASH', None) or input('Enter your Telegram API hash: ')

app = Client("client", api_id=API_ID, api_hash=API_HASH)
app.start()


class Cleaner:
    def __init__(self, chats=None, search_limit=1000):
        self.chats = chats or []
        self.search_limit = search_limit

    @staticmethod
    def chunks(l, n):
        """Yield successive n-sized chunks from l.
        https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks#answer-312464"""
        for i in range(0, len(l), n):
            yield l[i:i + n]

    @staticmethod
    def get_all_chats():
        dialogs = app.get_dialogs(pinned_only=True)

        dialog_chunk = app.get_dialogs()
        while len(dialog_chunk) > 0:
            dialogs.extend(dialog_chunk)
            dialog_chunk = app.get_dialogs(offset_date=dialogs[-1].top_message.date)

        return [d.chat for d in dialogs]

    def select_groups(self):
        chats = self.get_all_chats()
        groups = [c for c in chats if c.type in ('group', 'supergroup')]

        print('Delete all your messages in')
        for i, group in enumerate(groups):
            print(f'  {i+1}. {group.title}')
        print(f'  {len(groups) + 1}. (!) ALL OF THE ABOVE (!)\n')

        n = int(input('Insert option number: '))
        if not 1 <= n <= len(groups) + 1:
            print('Invalid option selected. Exiting...')
            exit(-1)

        self.chats = groups if n == len(groups) + 1 else [groups[n - 1]]
 
        print(f'\nSelected {", ".join(c.title for c in self.chats)}.\n')

    def run(self):
        for chat in self.chats:
            peer = app.resolve_peer(chat.id)
            message_ids = []
            add_offset = 0

            while True:
                q = self.search_messages(peer, add_offset)
                message_ids.extend(msg.id for msg in q['messages'])
                messages_count = len(q['messages'])
                print(f'Found {messages_count} of your messages in "{chat.title}"')
                if messages_count < self.search_limit:
                    break
                add_offset += self.search_limit

            self.delete_messages(chat.id, message_ids)

    def delete_messages(self, chat_id, message_ids):
        print(f'Deleting {len(message_ids)} messages with message IDs:')
        print(message_ids)
        for message_ids_chunk in self.chunks(message_ids, 100):
            try:
                app.delete_messages(
                    chat_id=chat_id,
                    message_ids=message_ids_chunk)
            except FloodWait as flood_exception:
                sleep(flood_exception.x)

    def search_messages(self, peer, add_offset):
        print(f'Searching messages. OFFSET: {add_offset}')
        return app.send(
            Search(
                peer=peer,
                q='',
                filter=InputMessagesFilterEmpty(),
                min_date=0,
                max_date=0,
                offset_id=0,
                add_offset=add_offset,
                limit=self.search_limit,
                max_id=0,
                min_id=0,
                hash=0,
                from_id=InputPeerSelf()
            )
        )


if __name__ == '__main__':
    try:
        deleter = Cleaner()
        deleter.select_groups()
        deleter.run()
    except UnknownError as e:
        print(f'UnknownError occured: {e}')
        print('Probably API has changed, ask developers to update this utility')
    finally:
        app.stop()
