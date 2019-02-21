from telegram import ParseMode

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
