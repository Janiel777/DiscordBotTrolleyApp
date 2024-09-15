import os
from dotenv import load_dotenv

# Cargar el archivo .env
env_path = os.path.join(os.path.dirname(__file__), '../.env')
load_dotenv(dotenv_path=env_path)

# Variables globales
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GITHUB_SECRET = os.getenv('GITHUB_SECRET')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')