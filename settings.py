from telegram import InlineKeyboardButton

vote_emojis = {
    "heart": "♥️",
    "like": "👍🏼",
    "dislike": "👎🏼",
    "poop": "💩"
}

vote_keyboard = [
    [
        InlineKeyboardButton('♥️', callback_data='heart'),
        InlineKeyboardButton('👍🏼', callback_data='like'),
        InlineKeyboardButton('👎🏼', callback_data='dislike'),
        InlineKeyboardButton('💩', callback_data='poop')
    ]
]

confirm_keyboard = [
    [
        InlineKeyboardButton('send', callback_data='send'),
        InlineKeyboardButton('cancel', callback_data='cancel')
    ]
]

token = '1876415562:AAEsX_c9k3Fot2IT0BYRqkCCQ5vFEHQDLDQ'
channel_id = '1187146727'
channel_username = '@BeatsDx'
member = '@TioDexty'
another_channel_username = '@DextyLixo'
another_channel_url = 'https://t.me/DextyLixo'

name, name_url, album, album_url, credit, statement, file_id, caption = [''] * 8
artists = []
genres = []
released = 0
admins = []
