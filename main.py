import sys, config, random, traceback, urllib.parse, re, calendar
from pymongo import MongoClient
from uuid import uuid4
from functools import wraps
from collections import Counter
from datetime import datetime
from telegram.ext import (Updater, Filters, 
CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, InlineQueryHandler)
from telegram import (ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, 
InlineQueryResultAudio, InlineQueryResultArticle, InputTextMessageContent)

TOKEN = ''
CHANNEL_ID = ''
ADMINS = [config.ADMIN_1, config.ADMIN_2]
PUBLISH_TEXT = ''

SONG_S, ARTIST_S, ALBUM_S, GENRES_S, RELEASED_S, FILE_S = range(6)
SONG, SONG_URL, ALBUM, ALBUM_URL, FILE_ID, CAPTION, CAPTION_URL = [''] * 7
CAPTION_READY = ''
ARTISTS = []
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
            sent_msg = bot.send_message(chat_id=CHANNEL_ID, text=STATEMENT, parse_mode=ParseMode.MARKDOWN)
            tweet = 'https://twitter.com/intent/tweet?text=🎧 {}\n{}'.format(
                urllib.parse.quote(CAPTION.encode('utf-8')),
                'https://t.me/musicophileowl/{}'.format(sent_msg.message_id)
            )
            keyboard = [
                [
                    InlineKeyboardButton('♥️', callback_data='heart'),
                    InlineKeyboardButton('👍🏼', callback_data='like'),
                    InlineKeyboardButton('👎🏼', callback_data='dislike'),
                    InlineKeyboardButton('💩', callback_data='poop')
                ],
                [
                    InlineKeyboardButton('Tweet 🐦', url=tweet)
                ]
            ]
            sent_song = bot.send_audio(chat_id=CHANNEL_ID, 
                        audio=FILE_ID, 
                        caption=CAPTION_READY,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup(keyboard))

            song_json = {
                "song_id": sent_song.message_id,
                "name": SONG,
                "name_url": SONG_URL,
                "artists": ARTISTS,
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

            song_json['date'] = '{}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            client = MongoClient('localhost', 27017)
            db = client[config.DB_NAME]
            db['Songs'].insert_one(song_json)

            bot.edit_message_text(text="Done 😌",
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id)
            return ConversationHandler.END                      
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            # print(e)
    elif (query.data == 'publish'):
        bot.send_message(
            chat_id=CHANNEL_ID, 
            text=PUBLISH_TEXT, 
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        bot.edit_message_text(
            text="Done 😌",
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )

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
            song_id = query.message.message_id - 1 # for tweet button
            caption = query.message.caption
            tweet = 'https://twitter.com/intent/tweet?text=🎧 {}\n{}'.format(
                urllib.parse.quote(caption.encode('utf-8')),
                'https://t.me/musicophileowl/{}'.format(song_id)
            )

            NEW_KEYBOARD = [
                [
                    InlineKeyboardButton('♥️ {}'.format((heart if (heart > 0) else '')), callback_data='heart'),
                    InlineKeyboardButton('👍🏼 {}'.format((like if (like > 0) else '')), callback_data='like'),
                    InlineKeyboardButton('👎🏼 {}'.format((dislike if (dislike > 0) else '')), callback_data='dislike'),
                    InlineKeyboardButton('💩 {}'.format((poop if (poop > 0) else '')), callback_data='poop')
                ], 
                [
                    InlineKeyboardButton('Tweet 🐦', url=tweet)   
                ]
            ]

            bot.edit_message_reply_markup(chat_id=query.message.chat_id,
                                          message_id=query.message.message_id,
                                          reply_markup=InlineKeyboardMarkup(NEW_KEYBOARD))

        except Exception as e:
            traceback.print_tb(e.__traceback__)
        finally: 
            client.close()

    bot.answer_callback_query(query.id, text='')


def myvotes(bot, update):
    try:
        msg = ''
        user_id = update.message.chat.id
        client = MongoClient('localhost', 27017)
        db = client[config.DB_NAME]
        votes = db['Votes'].find({"user_id": user_id})

        index = 1
        for vote in votes:
            msg += '{}. [{}]({}): {}\n'.format(index, 
                db['Songs'].find_one({"song_id": vote['song_id']})['name'],
                'https://t.me/musicophileowl/{}'.format(vote['song_id']),
                VOTE_EMOJIS[vote['vote']])
            index += 1
        
        update.message.reply_text(msg, 
                disable_web_page_preview=True,
                parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        

def rand(bot, update, args):
    client = MongoClient('localhost', 27017)
    db = client[config.DB_NAME]
    user_id = update.message.chat.id
    if (len(args) > 0):
        user_genres = ['#{}'.format(x.replace(',', '').replace('#', '')) for x in args]
        songs = db['Songs'].find({"genres": {"$all": user_genres}})
    else:
        songs = db['Songs'].find({})
    
    rand_song = songs[random.randint(0, songs.count()-1)]
    user_vote = db['Votes'].find_one(
        {
            "user_id": user_id,
            "song_id": rand_song['song_id']
        }
    )
    update.message.reply_text('[{}]({}){}'.format(
        rand_song['name'],
        'https://t.me/musicophileowl/{}'.format(rand_song['song_id']),
        ('\nYour vote: {}'.format(VOTE_EMOJIS[user_vote['vote']]) if user_vote else '')
    ), ParseMode.MARKDOWN)

@restricted
def publish(bot, update, args):
    global PUBLISH_TEXT
    try:
        client = MongoClient('localhost', 27017)
        db = client[config.DB_NAME]
        argument = ' '.join(args)
        if(argument == 'top songs last_month'):
            now = datetime.now()
            year = now.year
            month = now.month

            PUBLISH_TEXT = 'Top Songs posted in _{}_\n'.format(calendar.month_name[month])
            regx = re.compile("^{}-{}-(.*)$".format(year, month))

            scores = {}

            songs = db['Songs'].find({"date": regx})

            for song in songs:
                score = (
                        (song['votes']['heart'] * 2) + 
                        (song['votes']['like']) + 
                        (song['votes']['dislike'] * (-1)) + 
                        (song['votes']['poop'] * (-2))
                        )
                scores[song['name']] = (song['song_id'], score, song['votes'])
            
            top_songs = sorted(scores.items(), key=lambda x:x[1][1], reverse=True)

            i = 0
            while i < 10:
                song = top_songs[i] 
                heart = song[1][2]['heart']
                like = song[1][2]['like']
                dislike = song[1][2]['dislike']
                poop = song[1][2]['poop']

                PUBLISH_TEXT += '{}. [{}](https://t.me/musicophileowl/{}): {}{}{}{}{}{}{}{}{}\n'.format(
                        i+1, song[0], song[1][0],
                        VOTE_EMOJIS['heart'] if (heart > 0) else '', '{} '.format(heart) if(heart > 0) else '',
                        VOTE_EMOJIS['like'] if (like > 0) else '', '{} '.format(like) if(like > 0) else '',
                        VOTE_EMOJIS['dislike'] if (dislike > 0) else '', '{} '.format(dislike) if(dislike > 0) else '',
                        VOTE_EMOJIS['poop'] if (poop > 0) else '', '{} '.format(poop) if(poop > 0) else '',
                        'no votes yet' if((heart + like + dislike + poop) == 0) else ''
                    )
                i += 1
            
            keyboard = [
                [
                    InlineKeyboardButton('publish', callback_data='publish'),
                    InlineKeyboardButton('cancel', callback_data='cancel')
                ]
            ]
            
            update.message.reply_text(PUBLISH_TEXT, 
                                    parse_mode=ParseMode.MARKDOWN, 
                                    disable_web_page_preview=True,
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        traceback.print_tb(e.__traceback__)


def top(bot, update, args):
    text = ''
    client = MongoClient('localhost', 27017)
    db = client[config.DB_NAME]
    if (args[0] == 'genres'):
        hashtags = []

        count = int(args[1]) if(len(args) > 1) else 10
        
        songs = db['Songs'].find({})

        for song in songs:
            hashtags.extend(song['genres'])
        
        freq = Counter(hashtags)
        
        i = 1
        for item in freq.most_common(count):
            text += '{}. {}: {} time{}\n'.format(i, item[0], item[1], ('s' if (item[1] > 1) else ''))
            i += 1
        
        update.message.reply_text(text)
    elif (args[0] == 'songs'):
        scores = {}

        songs = db['Songs'].find({})

        for song in songs:
            score = (
                     (song['votes']['heart'] * 2) + 
                     (song['votes']['like']) + 
                     (song['votes']['dislike'] * (-1)) + 
                     (song['votes']['poop'] * (-2))
                    )
            scores[song['name']] = (song['song_id'], score, song['votes'])
        
        top_songs = sorted(scores.items(), key=lambda x:x[1][1], reverse=True)

        try:
            count = (int(args[1]) if(int(args[1]) < len(top_songs)) else len(top_songs)) if(len(args) > 1) else 10
        except Exception as e:
            print(e)

        i = 0
        while i < count:
            song = top_songs[i] 
            heart = song[1][2]['heart']
            like = song[1][2]['like']
            dislike = song[1][2]['dislike']
            poop = song[1][2]['poop']

            text += '{}. [{}](https://t.me/musicophileowl/{}): {}{}{}{}{}{}{}{}{}\n'.format(
                    i+1, song[0], song[1][0],
                    VOTE_EMOJIS['heart'] if (heart > 0) else '', '{} '.format(heart) if(heart > 0) else '',
                    VOTE_EMOJIS['like'] if (like > 0) else '', '{} '.format(like) if(like > 0) else '',
                    VOTE_EMOJIS['dislike'] if (dislike > 0) else '', '{} '.format(dislike) if(dislike > 0) else '',
                    VOTE_EMOJIS['poop'] if (poop > 0) else '', '{} '.format(poop) if(poop > 0) else '',
                    'no votes yet' if((heart + like + dislike + poop) == 0) else ''
                )
            i += 1
        
        update.message.reply_text(text, 
                                  parse_mode=ParseMode.MARKDOWN, 
                                  disable_web_page_preview=True)



def stats(bot, update):
    try:
        hashtags_count = 0
        distinct_genres = set()
        distinct_users = set()
        stats_statement = ''
        client = MongoClient('localhost', 27017)
        db = client[config.DB_NAME]
        songs = db['Songs'].find({})
        votes = db['Votes'].find({})
        
        for song in songs: 
            hashtags_count += len(song['genres'])
            distinct_genres.update(song['genres'])
        
        for v in votes:
            distinct_users.update([v['user_id']])
        
        stats_statement += 'Number of songs: {}\n'.format(songs.count())
        stats_statement += 'Number of hashtags: {}\n'.format(hashtags_count)
        stats_statement += 'Number of genres: {}\n'.format(len(distinct_genres))
        stats_statement += 'Number of votes: {}\n'.format(votes.count())
        stats_statement += 'Number of users: {}\n'.format(len(distinct_users)) 
        update.message.reply_text(stats_statement)
    except Exception as e:
        print(e)
    finally:
        client.close()


@restricted
def new(bot, update):
    global STATEMENT, ARTISTS
    STATEMENT = ''
    ARTISTS = []
    update.message.reply_text(text='Song?')

    return SONG_S


def song(bot, update):
    global SONG, SONG_URL, STATEMENT
    SONG = update.message.text
    SONG_URL = update.message.entities[0]['url']
    STATEMENT += '*Song*: [{}]({})\n'.format(SONG, SONG_URL)
    update.message.reply_text('{}Artist?'.format(STATEMENT), parse_mode=ParseMode.MARKDOWN)

    return ARTIST_S


def artist(bot, update):
    global ARTISTS, STATEMENT
    msg = update.message
    text = msg.text
    for entity in msg.entities:
            if entity['type'] == 'text_link':
                offset = entity['offset']
                length = entity['length']
                artist = {
                    "name": text[offset:offset+length],
                    "url": entity['url']
                }
                ARTISTS.append(artist)
    artists_str = ''
    for a in ARTISTS:
        artists_str += '[{}]({}) & '.format(a['name'], a['url'])
    STATEMENT += '*Artist{}*: {}\n'.format('s' if (len(ARTISTS) > 1) else '', artists_str[:-3])
    update.message.reply_text('{}Album?'.format(STATEMENT), parse_mode=ParseMode.MARKDOWN)

    return ALBUM_S


def album(bot, update):
    global ALBUM, ALBUM_URL, STATEMENT
    ALBUM = update.message.text
    ALBUM_URL = update.message.entities[0]['url']
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
        try:
            keyboard = [
                [
                    InlineKeyboardButton('♥️', callback_data='heart'),
                    InlineKeyboardButton('👍🏼', callback_data='like'),
                    InlineKeyboardButton('👎🏼', callback_data='dislike'),
                    InlineKeyboardButton('💩', callback_data='poop')
                ]
            ]
            FILE_ID = update.message.audio.file_id
            CAPTION = update.message.caption
            caption_words = CAPTION.split(' ')
            random_word = random.choice(caption_words)
            offset = CAPTION.find(random_word)
            length = len(random_word)
            CAPTION_READY = '{}[{}]({}){}'.format(
                            CAPTION[: offset], 
                            CAPTION[offset: (offset+length)],
                            'https://t.me/musicophileowl',
                            CAPTION[(offset+length):])
            update.message.reply_text(STATEMENT, 
                                    parse_mode=ParseMode.MARKDOWN)

            update.message.reply_audio(audio=FILE_ID, 
                        caption=CAPTION_READY,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup(keyboard))
            update.message.reply_text('Is this good?', 
                                    reply_markup=InlineKeyboardMarkup(CONFIRM_KEYBOARD))
        except Exception as e:
            traceback.print_tb(e.__traceback__)
    
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
    dispatcher.add_handler(CommandHandler('myvotes', myvotes))
    dispatcher.add_handler(CommandHandler('random', rand, pass_args=True))
    dispatcher.add_handler(CommandHandler('publish', publish, pass_args=True))
    dispatcher.add_handler(CommandHandler('top', top, pass_args=True))
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