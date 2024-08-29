import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from flask import Flask, request
from threading import Thread

load_dotenv()

app = Flask(__name__)

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GITHUB_SECRET = os.getenv('GITHUB_SECRET')

bot = commands.Bot(command_prefix="!")

@app.route('/github-webhook', methods=['POST'])
def github_webhook():
    data = request.json
    if "issue" in data:
        handle_issue_event(data)
    elif "pusher" in data:
        handle_push_event(data)
    return 'OK', 200

def handle_issue_event(data):
    issue_title = data['issue']['title']
    issue_url = data['issue']['html_url']
    message = f"Nuevo issue creado: [{issue_title}]({issue_url})"
    send_to_discord(message)

def handle_push_event(data):
    pusher = data['pusher']['name']
    commit_message = data['head_commit']['message']
    commit_url = data['head_commit']['url']
    message = f"Nuevo push por {pusher}: [{commit_message}]({commit_url})"
    send_to_discord(message)

def send_to_discord(message):
    channel = bot.get_channel(1278517612292210789)  # Reemplaza con el ID de tu canal
    bot.loop.create_task(channel.send(message))

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

@bot.event
async def on_ready():
    print(f'{bot.user} está conectado a Discord!')

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(DISCORD_TOKEN)
