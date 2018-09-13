import sys, config
from pymongo import MongoClient
from uuid import uuid4
from functools import wraps
from telegram.ext import (Updater, Filters, 
CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, InlineQueryHandler)
from telegram import (ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, 
InlineQueryResultAudio, InlineQueryResultArticle, InputTextMessageContent)

TOKEN = ''
CHANNEL_ID = ''
ADMINS = [config.ADMIN_1, config.ADMIN_2]

SONG_S, ARTIST_S, ALBUM_S, GENRES_S, RELEASED_S, FILE_S = range(6)
SONG, SONG_URL, ARTIST, ARTIST_URL, ALBUM, ALBUM_URL, FILE_ID, CAPTION, CAPTION_URL = [''] * 9
CAPTION_READY = ''
GENRES = []
RELEASED = 0
STATEMENT = ''
VOTE_EMOJIS = {
    "heart": "♥️",
    "like": "👍🏼",
    "dislike": "👎🏼",
    "poop": "💩"
}
CONFIRM_KEYBOARD = [
    [
        InlineKeyboardButton('send', callback_data='send'),
        InlineKeyboardButton('cancel', callback_data='cancel')
    ]
]
VOTE_KEYBOARD = [
    [
        InlineKeyboardButton('♥️', callback_data='heart'),
        InlineKeyboardButton('👍🏼', callback_data='like'),
        InlineKeyboardButton('👎🏼', callback_data='dislike'),
        InlineKeyboardButton('💩', callback_data='poop')
    ]
]


def restricted(func): 
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMINS:
            print('Aunthorized access denied for {}'.format(user_id))
            return
        return func(bot, update, *args, **kwargs)
    return wrapped


def start(bot, update):
    update.message.reply_text(text='hey')


def button(bot, update):
    query = update.callback_query

    if (query.data == 'send'):
        try: 
            bot.send_message(chat_id=CHANNEL_ID, text=STATEMENT, parse_mode=ParseMode.MARKDOWN)
            sent = bot.send_audio(chat_id=CHANNEL_ID, 
                        audio=FILE_ID, 
                        caption=CAPTION_READY,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup(VOTE_KEYBOARD))

            song_json = {
                "song_id": sent.message_id,
                "name": SONG,
                "name_url": SONG_URL,
                "artist": ARTIST,
                "artist_url": ARTIST_URL,
                "album": ALBUM,
                "album_url": ALBUM_URL,
                "genres": GENRES,
                "released": RELEASED,
                "votes": {
                    "heart": 0,
                    "like": 0,
                    "dislike": 0,
                    "poop": 0
                }
            }
            
            client = MongoClient('localhost', 27017)
            db = client[config.DB_NAME]
            db['Songs'].insert_one(song_json)

            bot.edit_message_text(text="Done 😌",
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id)
        except Exception as e:
            print(e)
    elif (query.data == 'cancel'):
        bot.edit_message_text(text="Oh 😮 OK then 😬 I'll try to forget about it.",
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id)
    elif (query.data in list(VOTE_EMOJIS.keys())):
        vote = query.data
        inc_query = {}
        inc_query["$inc"] = {"votes.{}".format(vote): 1}
        try: 
            client = MongoClient('localhost', 27017)
            db = client[config.DB_NAME]
            res = db['Votes'].find_one({
                "song_id": query.message.message_id,
                "user_id": update._effective_user.id
            })
            if res is None:
                db['Songs'].update_one(
                    {"song_id": query.message.message_id},
                    inc_query
                )
                db['Votes'].insert_one({
                    "song_id": query.message.message_id,
                    "user_id": update._effective_user.id,
                    "vote": vote
                })
                bot.answer_callback_query(query.id, text='You {} this.'.format(VOTE_EMOJIS.get(vote)))
            else:
                dec_query = {}
                dec_query["$inc"] = {"votes.{}".format(res['vote']): -1}
                db['Songs'].update_one(
                    {"song_id": query.message.message_id},
                    dec_query
                )
                db['Votes'].delete_one({
                    "song_id": query.message.message_id,
                    "user_id": update._effective_user.id,
                    "vote": res['vote']
                })
                if (res['vote'] != vote):
                    db['Songs'].update_one(
                    {"song_id": query.message.message_id},
                    inc_query
                    )
                    db['Votes'].insert_one({
                        "song_id": query.message.message_id,
                        "user_id": update._effective_user.id,
                        "vote": vote
                    })
                    bot.answer_callback_query(query.id, text='You {} this.'.format(VOTE_EMOJIS.get(vote)))
                else:
                    bot.answer_callback_query(query.id, text='You no longer {} this.'.format(VOTE_EMOJIS.get(vote)))
            res = db['Songs'].find_one({
                "song_id": query.message.message_id
            })

            heart = res['votes']['heart']
            like = res['votes']['like']
            dislike = res['votes']['dislike']
            poop = res['votes']['poop']

            NEW_KEYBOARD = [
                [
                    InlineKeyboardButton('♥️ {}'.format((heart if (heart > 0) else '')), callback_data='heart'),
                    InlineKeyboardButton('👍🏼 {}'.format((like if (like > 0) else '')), callback_data='like'),
                    InlineKeyboardButton('👎🏼 {}'.format((dislike if (dislike > 0) else '')), callback_data='dislike'),
                    InlineKeyboardButton('💩 {}'.format((poop if (poop > 0) else '')), callback_data='poop')
                ]
            ]

            bot.edit_message_reply_markup(chat_id=query.message.chat_id,
                                          message_id=query.message.message_id,
                                          reply_markup=InlineKeyboardMarkup(NEW_KEYBOARD))

        except Exception as e:
            print(e)
        finally: 
            client.close()

    bot.answer_callback_query(query.id, text='')


@restricted
def stats(bot, update):
    try:
        hashtags_count = 0
        stats_statement = ''
        client = MongoClient('localhost', 27017)
        db = client[config.DB_NAME]
        songs = db['Songs'].find({})
        votes = db['Votes'].find({})
        
        for song in songs: 
            hashtags_count += len(song['genres'])
        
        stats_statement += 'Number of songs: {}\n'.format(songs.count())
        stats_statement += 'Number of hashtags: {}\n'.format(hashtags_count)
        stats_statement += 'Number of votes: {}\n'.format(votes.count())
        update.message.reply_text(stats_statement)
    except Exception as e:
        print(e)
    finally:
        client.close()


@restricted
def new(bot, update):
    global STATEMENT
    STATEMENT = ''
    update.message.reply_text(text='Song?')

    return SONG_S


def song(bot, update):
    global SONG, SONG_URL, STATEMENT
    [SONG, SONG_URL] = [x.strip() for x in update.message.text.split(',')]
    STATEMENT += '*Song*: [{}]({})\n'.format(SONG, SONG_URL)
    update.message.reply_text('{}Artist?'.format(STATEMENT), parse_mode=ParseMode.MARKDOWN)

    return ARTIST_S


def artist(bot, update):
    global ARTIST, ARTIST_URL, STATEMENT
    [ARTIST, ARTIST_URL] = [x.strip() for x in update.message.text.split(',')]
    STATEMENT += '*Artist*: [{}]({})\n'.format(ARTIST, ARTIST_URL)
    update.message.reply_text('{}Album?'.format(STATEMENT), parse_mode=ParseMode.MARKDOWN)

    return ALBUM_S


def album(bot, update):
    global ALBUM, ALBUM_URL, STATEMENT
    [ALBUM, ALBUM_URL] = [x.strip() for x in update.message.text.split(',')]
    STATEMENT += '*Album*: [{}]({})\n'.format(ALBUM, ALBUM_URL)
    update.message.reply_text('{}Genres?'.format(STATEMENT), parse_mode=ParseMode.MARKDOWN)

    return GENRES_S


def genres(bot, update):
    global GENRES, STATEMENT
    GENRES = [x.strip() for x in update.message.text.split(',')]
    STATEMENT += '*Genre{}*: {}\n'.format(('' if (len(GENRES) == 1) else 's'), ', '.join(GENRES))
    update.message.reply_text('{}Released?'.format(STATEMENT), parse_mode=ParseMode.MARKDOWN)

    return RELEASED_S


def released(bot, update):
    global RELEASED, STATEMENT
    RELEASED = update.message.text
    STATEMENT += '*Released*: {}'.format(RELEASED)
    update.message.reply_text(STATEMENT, parse_mode=ParseMode.MARKDOWN)

    return FILE_S


def file(bot, update):
    global FILE_ID, CAPTION, CAPTION_URL, CAPTION_READY
    if update.message.caption_entities is None:
        update.message.reply_text('You forgot to add caption url!')
    else:
        FILE_ID = update.message.audio.file_id
        CAPTION = update.message.caption
        CAPTION_URL = update.message.caption_entities[0].url
        offset = update.message.caption_entities[0].offset
        length = update.message.caption_entities[0].length
        CAPTION_READY = '{}[{}]({}){}'.format(
                           CAPTION[: offset], 
                           CAPTION[offset: (offset+length)],
                           CAPTION_URL,
                           CAPTION[(offset+length):])
        update.message.reply_text(STATEMENT, 
                                  parse_mode=ParseMode.MARKDOWN)

        update.message.reply_audio(audio=FILE_ID, 
                       caption=CAPTION_READY,
                       parse_mode=ParseMode.MARKDOWN,
                       reply_markup=InlineKeyboardMarkup(VOTE_KEYBOARD))
        update.message.reply_text('Is this good?', 
                                  reply_markup=InlineKeyboardMarkup(CONFIRM_KEYBOARD))
    
    return ConversationHandler.END


def cancel(bot, update):
    update.message.reply_text('Oh no!')

    return ConversationHandler.END


def main():
    updater = Updater(token=TOKEN)

    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('new', new)],
        states={
            SONG_S: [MessageHandler(Filters.text, song)],
            ARTIST_S: [MessageHandler(Filters.text, artist)],
            ALBUM_S: [MessageHandler(Filters.text, album)],
            GENRES_S: [MessageHandler(Filters.text, genres)],
            RELEASED_S: [MessageHandler(Filters.text, released)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('stats', stats))
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(MessageHandler(Filters.audio, file))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    mode = sys.argv[1] if(len(sys.argv) >= 2) else 'debug'

    if(mode == 'production'):
        TOKEN = config.BOT_TOKEN
        CHANNEL_ID = config.CHANNEL_ID
    else:
        TOKEN = config.DEV_TOKEN
        CHANNEL_ID = config.DUMP_CHANNEL_ID

    main()