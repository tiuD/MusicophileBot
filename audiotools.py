from pydub import AudioSegment
import re, traceback, os


def sample(bot, update, args):
    try:
        regex = re.compile(r'(\d{2})(\d{2})(\d{2})(\d{2})')
        match = regex.match(args)
        if match:
            # start and end (in seconds)
            start = (int(match.group(1)) * 60) + int(match.group(2))
            end = (int(match.group(3)) * 60) + int(match.group(4))

            song_file = bot.get_file(update.message.audio.file_id)

            song_file.download('song.mp3')

            song = AudioSegment.from_mp3('song.mp3')
            sliced = song[start*1000:end*1000]
            sliced.export('song.ogg', format='ogg', parameters=["-acodec", "libopus"])
        else:
            update.message.reply_text('arguments are not valid!')
    except Exception as e:
        print(e)
        traceback.print_tb(e.__traceback__)
