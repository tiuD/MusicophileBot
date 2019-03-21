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

token = ''
channel_id = ''
channel_username = ''

name, name_url, album, album_url, credit, statement, file_id, caption = [''] * 8
artists = []
genres = []
released = 0
admins = []