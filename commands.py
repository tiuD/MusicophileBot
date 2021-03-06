import random, re, settings, traceback, audiotools
from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient
from config import config
from collections import Counter
from functools import wraps

def restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        try:
            user_id = update.effective_user.id
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
        if user_id not in settings.admins:
            print(f'Aunthorized access denied for {user_id}')
            return
        return func(bot, update, *args, **kwargs)
    return wrapped


def start(bot, update):
    statement = 'Hey! Welcome to *MusicophileBot*!\n'
    statement += "You can use bot to listen to random songs, see the songs you've voted, and more.\n"
    statement += 'To see the commands, simply type /commands.\n'
    statement += '\n'
    statement += 'This bot is developed and maintained by [Amir A. Shabani](https://twitter.com/amirashabani).\n'
    statement += 'You can find the source code on my [GitHub page](https://github.com/amirashabani/MusicophileBot).'
    update.message.reply_text(
        text=statement,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


def stats(bot, update):
    distinct_genres = set()
    distinct_users = set()
    stats_statement = ''

    try:
        client = MongoClient('localhost', 27017)
        db = client[config('database.ini', 'mongodb')['db_name']]
        songs = db['Songs'].find({})
        votes = db['Votes'].find({})

        for song in songs:
            distinct_genres.update(song['genres'])

        for vote in votes:
            distinct_users.update([vote['user_id']])

        stats_statement += f'Number of songs: {songs.count()}\n'
        stats_statement += f'Number of genres: {len(distinct_genres)}\n'
        stats_statement += f'Number of votes: {votes.count()}\n'
        stats_statement += f'Number of users: {len(distinct_users)}\n'
        update.message.reply_text(stats_statement)
    except Exception as e:
        print(e)
    finally:
        client.close()


def top(bot, update, args):
    result = ''
    client = MongoClient('localhost', 27017)
    db = client[config('database.ini', 'mongodb')['db_name']]
    if (args[0] == 'genres'):
        hashtags = []

        count = int(args[1]) if(len(args) > 1) else 10

        songs = db['Songs'].find({})

        for song in songs:
            hashtags.extend(song['genres'])

        freq = Counter(hashtags)

        i = 1
        for item in freq.most_common(count):
            result += f'{i}. {item[0]}: {item[1]} time{"s" if (item[1] > 1) else ""}\n'
            i += 1

        update.message.reply_text(result)
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

        count = len(top_songs) if(len(top_songs) < 10) else 10
        if(len(args) >= 2):
            try:
                if(int(args[1]) < len(top_songs)):
                    count = int(args[1])
                else:
                    count = len(top_songs)
            except Exception:
                pass

        i = 0
        while i < count:
            song = top_songs[i]
            heart = song[1][2]['heart']
            like = song[1][2]['like']
            dislike = song[1][2]['dislike']
            poop = song[1][2]['poop']

            result += '{}. [{}](https://t.me/{}/{}): {}{}{}{}{}{}{}{}{}\n'.format(
                i+1,
                song[0],
                settings.channel_username,
                song[1][0],
                settings.vote_emojis['heart'] if (heart > 0) else '',
                f'{heart} ' if(heart > 0) else '',
                settings.vote_emojis['like'] if (like > 0) else '',
                f'{like} ' if(like > 0) else '',
                settings.vote_emojis['dislike'] if (dislike > 0) else '',
                f'{dislike} ' if(dislike > 0) else '',
                settings.vote_emojis['poop'] if (poop > 0) else '',
                f'{poop} ' if(poop > 0) else '',
                'no votes yet' if((heart + like + dislike + poop) == 0) else ''
            )
            i += 1

        update.message.reply_text(
            result,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )


def rand(bot, update, args):
    try:
        client = MongoClient('localhost', 27017)
        db = client[config('database.ini', 'mongodb')['db_name']]
        user_id = update.message.chat.id
        if (len(args) > 0):
            user_genres = [f'#{x.replace(",", "").replace("#, ")}' for x in args]
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

        bot.send_audio(
            chat_id=update.message.chat.id,
            audio=f'https://t.me/{settings.channel_username}/{rand_song["song_id"]}',
            caption=(f'\nYour vote: {settings.vote_emojis[user_vote["vote"]]}' if user_vote else '')
        )
    except Exception as e:
        print(e)
        traceback.print_tb(e.__traceback__)


@restricted
def post(bot, update):
    try:
        caption = update.message.caption

        settings.artists = []
        settings.genres = []
        settings.statement = ''
        settings.member = ''
        settings.another_channel_url = ''
        settings.another_channel_username = ''
        artists_str = ''
        song_caption = ''

        scr = re.compile(r'.*\"(.*)\".*', re.MULTILINE | re.DOTALL) # song_caption_regex
        match = scr.match(caption)
        if match:
            settings.caption = match.group(1)

            settings.file_id = update.message.audio.file_id

            for entity in update.message.caption_entities:
                offset = entity['offset']
                length = entity['length']
                text = caption[offset:(offset+length)]

                if entity['type'] == 'text_link':
                    url = entity['url']
                    if text[0] == '!':
                        settings.name = text[1:]
                        settings.name_url = url
                    elif text[0] == '@':
                        artist = {
                            "name": text[1:],
                            "url": url
                        }
                        settings.artists.append(artist)
                    elif text[0] == '$':
                        settings.album = text[1:]
                        settings.album_url = url
                    elif text[0] == '#':
                        settings.another_channel_username = text[1:]
                        settings.another_channel_url = url
                elif entity['type'] == 'hashtag':
                    if text[1] == 'r':
                        settings.released = int(text[2:])
                    elif text[1] == 's':
                        audiotools.sample(bot, update, text[2:])
                    elif text[1] == 'm':
                        settings.member = f'#{text[2:]}'
                    else:
                        settings.genres.append(text)

            caption_words = song_caption.split(' ')
            random_word = random.choice(caption_words)
            offset = song_caption.find(random_word)
            length = len(random_word)

            settings.statement += '*Song*: [{}]({})\n'.format(
                settings.name,
                settings.name_url
            )

            for a in settings.artists:
                artists_str += '[{}]({}) & '.format(a['name'], a['url'])
            settings.statement += '*Artist{}*: {}\n'.format('s' if (len(settings.artists) > 1) else '', artists_str[:-3])
            settings.statement += '*Album*: [{}]({})\n'.format(settings.album, settings.album_url)
            settings.statement += '*Genre{}*: {}\n'.format(('' if (len(settings.genres) == 1) else 's'), ', '.join(settings.genres))
            settings.statement += '*Released*: {}\n'.format(settings.released)
            
            update.message.reply_text(
                settings.statement,
                parse_mode=ParseMode.MARKDOWN
            )
            bot.send_voice(
                chat_id=update.message.chat.id,
                voice=open('song.ogg', 'rb'),
                caption=settings.caption,
                parse_mode=ParseMode.MARKDOWN,
                timeout=1000
            )

            audio_caption = ''
            if settings.another_channel_username != '':
                audio_caption = '???? [@{}]({})\n???? [@{}]({})'.format(
                    settings.another_channel_username,
                    settings.another_channel_url,
                    settings.channel_username,
                    f'https://t.me/{settings.channel_username}'
                )
            elif settings.member != '':
                audio_caption = '???? Sent by {}\n???? [@{}]({})'.format(
                    settings.member,
                    settings.channel_username,
                    f'https://t.me/{settings.channel_username}'
                )
            else:
                audio_caption = '???? [@{}]({}) ????'.format(
                    settings.channel_username,
                    f'https://t.me/{settings.channel_username}'
                )
            update.message.reply_audio(
                audio=settings.file_id,
                caption=audio_caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(settings.vote_keyboard)
            )
            update.message.reply_text(
                'Is this good?',
                reply_markup=InlineKeyboardMarkup(settings.confirm_keyboard)
            )
        else:
            update.message.reply_text("I don't see no caption ????")
    except Exception as e:
        print(e)
        traceback.print_tb(e.__traceback__)


def genres(bot, update):
    try:
        genre_report = ""
        genre_rates = {}
        vote_weight = {
            "heart": 2,
            "like": 1,
            "dislike": -1,
            "poop": -2
        }
        user_id = update.message.chat.id
        client = MongoClient("localhost", 27017)
        db = client[config("database.ini", "mongodb")["db_name"]]
        votes = db["Votes"].find({"user_id": user_id})

        for vote in votes:
            song_id = vote["song_id"]
            song = db["Songs"].find_one({"song_id": song_id})
            for genre in song["genres"]:
                if genre in genre_rates:
                    genre_rates[genre] += vote_weight[vote["vote"]]
                else:
                    genre_rates[genre] = vote_weight[vote["vote"]]
        
        top_genres = sorted(genre_rates.items(), key=lambda x: x[1], reverse=True)

        length = len(top_genres)
        i = 0
        count = 10 if length >= 10 else length
        while i < count:
            genre_report += f"{i+1}. {top_genres[i][0]}\n"
            i += 1
        
        update.message.reply_text(genre_report)


    except Exception as e:
        print(e)
        traceback.print_tb(e.__traceback__)
