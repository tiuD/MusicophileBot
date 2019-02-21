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