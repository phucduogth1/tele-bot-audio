import os
from pytube import YouTube
import logging
import vlc
from telegram import Update
from telegram.ext import ApplicationBuilder, filters, CommandHandler, MessageHandler, ContextTypes
from dotenv import load_dotenv

# Initialize services
load_dotenv()
media_player = vlc.MediaListPlayer()
vlc_instance = vlc.Instance()
media_list = vlc_instance.media_list_new()
current_last_song_index = 0

# Initialize vars
TELE_BOT_TOKEN = os.getenv('TELE_BOT_TOKEN')
playlist_info = []

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def get_audio_stream_url(video_url):
    yt = YouTube(video_url)
    yt.check_availability()
    video_title = yt.title
    video_author = yt.author
    audio_stream = yt.streams.filter(only_audio=True).first()
    print(audio_stream.url)
    return video_title, video_author, audio_stream.url

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

# Function to add audio stream URL to the queue
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_url = update.message.text
    try:
        video_title, video_author, audio_stream_url = get_audio_stream_url(video_url=video_url)

        if len(audio_stream_url) > 1:
            media = vlc_instance.media_new(audio_stream_url)
    
            # adding media to media list
            media_list.add_media(media)
            
            # setting media list to the media player
            media_player.set_media_list(media_list)
            playlist_info.append(
                {
                    "video_title": video_title,
                    "video_author": video_author
                }
            )
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Added *{video_title}* to queue.", parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid URL. Provide a valid audio stream URL.")
    except Exception as e:
        print(f"Error processing URL: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid URL. Provide a valid audio stream URL.")

# Function to play the current audio stream
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    specific_song_index = update.message.text
    if len(specific_song_index.split()) == 2:
        if specific_song_index.split()[1].isnumeric():
            index_query = int(specific_song_index.split()[1])
            if index_query >= 0 and index_query <= len(playlist_info):
                media_player.play_item_at_index(index_query)
                current_song = get_current_track()
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Now playing: *{current_song}*", parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Media index out of range between {0} - {len(playlist_info)}")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Wrong argument type number.")
    elif current_last_song_index < len(playlist_info) and current_last_song_index != 0 and not media_player.is_playing():
        media_player.play_item_at_index(current_last_song_index + 1)
        current_song = get_current_track()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Now playing: *{current_song}*", parse_mode="Markdown")
    elif current_last_song_index == 0:
        media_player.play()
        current_song = get_current_track()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Now playing: *{current_song}*", parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Queue is empty. Add audio stream URLs using /add command.")

# Function to pause audio playback
async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if media_player.is_playing():
        media_player.set_pause(1)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Audio paused.")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No current now playing.")

# Function to resume audio playback
async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    media_player.set_pause(0)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Audio resumed.")

# Function to skip to the next track
async def next_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    canNext = media_player.next()
    if canNext == 0:
        current_track = get_current_track()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Playing *{current_track}*", parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No more tracks in queue.")

# Function to play the previous track
async def prev_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    canBack = media_player.previous()
    if canBack == 0:
        current_track = get_current_track()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Playing *{current_track}*", parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No more tracks in queue.")

# async def loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     media_player.set_playback_mode(vlc.PlaybackMode(1))
    # media_player.set_playback_mode(vlc.PlaybackMode().loop)

async def current(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if media_player.is_playing():
        current_song = get_current_track()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Current now playing: *{current_song}*", parse_mode="Markdown")

async def is_playing(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Is playing: *{media_player.is_playing()}*", parse_mode="Markdown")

async def playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global playlist_info

    playlist_text = "Playlist:\n"
    current_song_index = get_current_track_index()
    
    for idx, song_info in enumerate(playlist_info, start=0):
        song_text = f"{idx}. {song_info['video_title']}. Channel: {song_info['video_author']}"
        if current_song_index and idx == current_song_index:
            song_text += "  *<<<<Now playing*"
        playlist_text += song_text + "\n"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=playlist_text, parse_mode="Markdown")

async def volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(update.message.text.split(" ")) != 2:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid input. Please provide a number between 0 and 100.")
            return
        volume = int(update.message.text.split(" ")[1])
        if 0 <= volume <= 100:
            set_volume(volume)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Volume set to {volume}%.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Volume must be between 0 and 100.")
    except ValueError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid input. Please provide a number between 0 and 100.")


def set_volume(volume):
        media_player_controller = media_player.get_media_player()
        if 0 <= volume <= 100:
            media_player_controller.audio_set_volume(volume)

def get_current_track():
    if not len(playlist_info) == 0:
        index = get_current_track_index()
        return playlist_info[index]["video_title"]

def get_current_track_index():
    if not len(playlist_info) == 0:
        current_index = media_player.get_media_player().get_media()
        return media_list.index_of_item(current_index)

# def assign_last_index():
def on_end_reached(event):
    global current_last_song_index
    current_last_song_index += 1
    

# Initialize the Telegram bot
def main() -> None:
    application = ApplicationBuilder().token(TELE_BOT_TOKEN).build()
    event_manager = media_player.get_media_player().event_manager()
    event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, on_end_reached)
    # Command handlers
    start_handler = CommandHandler("start", start)
    add_handler = CommandHandler("add", add)
    play_handler = CommandHandler("play", play)
    pause_handler = CommandHandler("pause", pause)
    resume_handler = CommandHandler("resume", resume)
    next_handler = CommandHandler("next", next_track)
    prev_handler = CommandHandler("prev", prev_track)
    playlist_handler = CommandHandler("playlist", playlist)
    current_handler = CommandHandler("current", current)
    volume_handler = CommandHandler("volume", volume)
    is_playing_handler = CommandHandler("is_playing", is_playing)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    
    application.add_handler(echo_handler)
    application.add_handler(start_handler)
    application.add_handler(add_handler)
    application.add_handler(play_handler)
    application.add_handler(pause_handler)
    application.add_handler(resume_handler)
    application.add_handler(next_handler)
    application.add_handler(prev_handler)
    application.add_handler(playlist_handler)
    application.add_handler(current_handler)
    application.add_handler(volume_handler)
    application.add_handler(is_playing_handler)
    application.add_handler(unknown_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
