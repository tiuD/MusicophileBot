from telegram import ParseMode
from pymongo import MongoClient
from config import config
from collections import Counter
from settings import VOTE_EMOJIS

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

        stats_statement += 'Number of songs: {}\n'.format(songs.count())
        stats_statement += 'Number of genres: {}\n'.format(len(distinct_genres))
        stats_statement += 'Number of votes: {}\n'.format(votes.count())
        stats_statement += 'Number of users: {}\n'.format(len(distinct_users))
        update.message.reply_text(stats_statement)
    except Exception as e:
        print(e)
    finally:
        client.close()


def top(bot, update, args):
    text = ''
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
