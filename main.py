import random, traceback, urllib.parse, re, calendar, commands, settings
import os, sys
from config import config
from pymongo import MongoClient
from uuid import uuid4
from functools import wraps
from collections import Counter
from datetime import datetime
from telegram.ext import (Updater, Filters, 
CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler)
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, 
InlineQueryResultAudio, InlineQueryResultArticle, InputTextMessageContent, ParseMode)

PUBLISH_TEXT = ''

CONFIRM_KEYBOARD = [
    [
        InlineKeyboardButton('send', callback_data='send'),
        InlineKeyboardButton('cancel', callback_data='cancel')
    ]
]


def restricted(func): 
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        user_id = update.message.chat.id
        if user_id not in settings.admins:
            print('Aunthorized access denied for {}'.format(user_id))
            return
        return func(bot, update, *args, **kwargs)
    return wrapped


def button(bot, update):
    query = update.callback_query

    if (query.data == 'send'):
        try:
            keyboard = [
                [
                    InlineKeyboardButton('♥️', callback_data='heart'),
                    InlineKeyboardButton('👍🏼', callback_data='like'),
                    InlineKeyboardButton('👎🏼', callback_data='dislike'),
                    InlineKeyboardButton('💩', callback_data='poop')
                ]
            ] 
            sent_text = bot.send_message(
                chat_id=settings.channel_id,
                text=settings.statement,
                parse_mode=ParseMode.MARKDOWN
            )
            bot.send_voice(
                chat_id=settings.channel_id,
                voice=open('song.ogg', 'rb'),
                caption=settings.caption,
                parse_mode=ParseMode.MARKDOWN,
                timeout=1000
            )
            sent_song = bot.send_audio(
                chat_id=settings.channel_id,
                audio=settings.file_id,
                caption='🎧 [@{}]({}) 🦉'.format(
                    settings.channel_username,
                    f'https://t.me/{settings.channel_username}/{sent_text.message_id}'
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            os.remove('song.mp3')
            os.remove('song.ogg')
            song_json = {
                "song_id": sent_song.message_id,
                "name": settings.name,
                "name_url": settings.name_url,
                "artists": settings.artists,
                "album": settings.album,
                "album_url": settings.album_url,
                "genres": settings.genres,
                "released": settings.released,
                "votes": {
                    "heart": 0,
                    "like": 0,
                    "dislike": 0,
                    "poop": 0
                }
            }

            song_json['date'] = '{}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            client = MongoClient('localhost', 27017)
            db = client[config('database.ini', 'mongodb')['db_name']]
            db['Songs'].insert_one(song_json)

            bot.edit_message_text(
                text="Done 😌",
                chat_id=query.message.chat_id,
                message_id=query.message.message_id
            )
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            # print(e)
    elif (query.data == 'publish'):
        bot.send_message(
            chat_id=settings.channel_id,
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
    elif (query.data in list(settings.vote_emojis.keys())):
        vote = query.data
        inc_query = {}
        inc_query["$inc"] = {"votes.{}".format(vote): 1}
        try: 
            client = MongoClient('localhost', 27017)
            db = client[config('database.ini', 'mongodb')['db_name']]
            res = db['Votes'].find_one({
                "song_id": query.message.message_id,
                "user_id": update.callback_query.from_user.id
            })
            if res is None:
                db['Songs'].update_one(
                    {"song_id": query.message.message_id},
                    inc_query
                )
                db['Votes'].insert_one({
                    "song_id": query.message.message_id,
                    "user_id": update.callback_query.from_user.id,
                    "vote": vote
                })
                bot.answer_callback_query(query.id, text='You {} this.'.format(settings.vote_emojis.get(vote)))
            else:
                dec_query = {}
                dec_query["$inc"] = {"votes.{}".format(res['vote']): -1}
                db['Songs'].update_one(
                    {"song_id": query.message.message_id},
                    dec_query
                )
                db['Votes'].delete_one({
                    "song_id": query.message.message_id,
                    "user_id": update.callback_query.from_user.id,
                    "vote": res['vote']
                })
                if (res['vote'] != vote):
                    db['Songs'].update_one(
                    {"song_id": query.message.message_id},
                    inc_query
                    )
                    db['Votes'].insert_one({
                        "song_id": query.message.message_id,
                        "user_id": update.callback_query.from_user.id,
                        "vote": vote
                    })
                    bot.answer_callback_query(query.id, text='You {} this.'.format(settings.vote_emojis.get(vote)))
                else:
                    bot.answer_callback_query(query.id, text='You no longer {} this.'.format(settings.vote_emojis.get(vote)))
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

            bot.edit_message_reply_markup(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                reply_markup=InlineKeyboardMarkup(NEW_KEYBOARD)
            )

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
        db = client[config('database.ini', 'mongodb')['db_name']]
        votes = db['Votes'].find({"user_id": user_id})

        index = 1
        for vote in votes:
            msg += '{}. [{}]({}): {}\n'.format(index, 
                db['Songs'].find_one({"song_id": vote['song_id']})['name'],
                'https://t.me/{}/{}'.format(
                    settings.channel_username,
                    vote['song_id']
                ),
                settings.vote_emojis[vote['vote']])
            index += 1
        
        update.message.reply_text(msg, 
                disable_web_page_preview=True,
                parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print(e)


@restricted
def publish(bot, update, args):
    global PUBLISH_TEXT
    try:
        client = MongoClient('localhost', 27017)
        db = client[config('database.ini', 'mongodb')['db_name']]
        argument = ' '.join(args)
        if(argument == 'top songs last_month'):
            now = datetime.now()
            year = now.year
            month = now.month

            PUBLISH_TEXT = 'Top Songs posted in _{}_\n'.format(calendar.month_name[month])
            regx = re.compile("^{}-{:02d}-(.*)$".format(year, month))

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
            length = len(top_songs)

            i = 0
            count = 10 if length >= 10 else length
            while i < count:
                song = top_songs[i] 
                heart = song[1][2]['heart']
                like = song[1][2]['like']
                dislike = song[1][2]['dislike']
                poop = song[1][2]['poop']

                PUBLISH_TEXT += '{}. [{}](https://t.me/{}/{}): {}{}{}{}{}{}{}{}{}\n'.format(
                    i+1,
                    song[0],
                    settings.channel_username,
                    song[1][0],
                    settings.vote_emojis['heart'] if (heart > 0) else '', '{} '.format(heart) if(heart > 0) else '',
                    settings.vote_emojis['like'] if (like > 0) else '', '{} '.format(like) if(like > 0) else '',
                    settings.vote_emojis['dislike'] if (dislike > 0) else '', '{} '.format(dislike) if(dislike > 0) else '',
                    settings.vote_emojis['poop'] if (poop > 0) else '', '{} '.format(poop) if(poop > 0) else '',
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
        elif(argument == 'top songs last_year'):
            now = datetime.now()
            year = now.year

            PUBLISH_TEXT = 'Top Songs posted in _{}_\n'.format(year)
            regx = re.compile("^{}-(.*)-(.*)$".format(year))

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
            length = len(top_songs)

            i = 0
            count = 10 if length >= 10 else length
            while i < count:
                song = top_songs[i] 
                heart = song[1][2]['heart']
                like = song[1][2]['like']
                dislike = song[1][2]['dislike']
                poop = song[1][2]['poop']

                PUBLISH_TEXT += '{}. [{}](https://t.me/{}/{}): {}{}{}{}{}{}{}{}{}\n'.format(
                    i+1,
                    song[0],
                    settings.channel_username,
                    song[1][0],
                    settings.vote_emojis['heart'] if (heart > 0) else '', '{} '.format(heart) if(heart > 0) else '',
                    settings.vote_emojis['like'] if (like > 0) else '', '{} '.format(like) if(like > 0) else '',
                    settings.vote_emojis['dislike'] if (dislike > 0) else '', '{} '.format(dislike) if(dislike > 0) else '',
                    settings.vote_emojis['poop'] if (poop > 0) else '', '{} '.format(poop) if(poop > 0) else '',
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


def main():
    updater = Updater(token=settings.token)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', commands.start))
    dispatcher.add_handler(MessageHandler(Filters.audio, commands.post))
    dispatcher.add_handler(CommandHandler('stats', commands.stats))
    dispatcher.add_handler(CommandHandler('myvotes', myvotes))
    dispatcher.add_handler(CommandHandler('random', commands.rand, pass_args=True))
    dispatcher.add_handler(CommandHandler('publish', publish, pass_args=True))
    dispatcher.add_handler(CommandHandler('top', commands.top, pass_args=True))
    dispatcher.add_handler(CallbackQueryHandler(button))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    mode = sys.argv[1] if(len(sys.argv) >= 2) else 'debug'

    settings.admins = list(map(int, config('privileges.ini', 'admins').values()))

    if(mode == 'production'):
        settings.token = config('bot.ini', 'tokens')['main']
        settings.channel_id = int(config('bot.ini', 'channel')['main'])
        settings.channel_username = config('bot.ini', 'channel')['main_username']
    else:
        settings.token = config('bot.ini', 'tokens')['dev']
        settings.channel_id = int(config('bot.ini', 'channel')['dev'])
        settings.channel_username = config('bot.ini', 'channel')['dev_username']

    main()
