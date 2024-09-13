import asyncio
import io
import os
import discord
from discord.ext import commands, tasks
from flask import Flask, request, json
from threading import Thread
from discord import File
import requests
from datetime import datetime, timedelta
import pymongo
import re
import pytz  # Para manejo de zona horaria
import subprocess
import traceback

from getStatistics import get_repo_issues, get_repo, get_project_items_with_custom_fields, get_all_issues, \
    get_open_issues, filter_issues_by_milestone, issues_total_points_without_dk, issues_total_points_with_dk, \
    get_closed_issues, get_closed_issues_by_milestone, get_milestone_perfect_total_points_without_dk, \
    get_milestone_perfect_total_points_with_dk, get_milestone_closed_total_points_with_dk, \
    get_milestone_average_with_dk, get_milestone_closed_average_with_dk, calculate_individual_grades, \
    group_issues_by_assignee, find_unassigned_members

app = Flask(__name__)

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GITHUB_SECRET = os.getenv('GITHUB_SECRET')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')

ORG_NAME = 'uprm-inso4116-2024-2025-s1'  # Propietario del repositorio
REPO_NAME = 'semester-project-trolley-tracker-app'  # Nombre del repositorio

# Diccionario que mapea los ID de canales de Discord con los ID de discusiones de GitHub
channel_to_discussion = {
    1277350203330007108: 'D_kwDOMoKp284AbRww',  # chat general
    1278505988579659806: 'D_kwDOMoKp284AbRwv',  # chat blue-team-trolley-metrics
    1278506143089688586: 'D_kwDOMoKp284AbRwu'   # chat green-team-notifications
}

bot = commands.Bot(command_prefix="!")
client = pymongo.MongoClient(MONGO_URI)
db = client['trolleyAppDB']
collection = db['documents']

# Diccionario para almacenar el tiempo de entrada de cada usuario en un canal de voz
voice_channel_data = {}
# Diccionario para almacenar las duraciones de tiempo que cada usuario estuvo en el canal
durations = {}

# Cadena para registrar los eventos de la reunión
event_log = ""
# Variable para controlar si la reunión está activa
reunion_activa = False

# Zona horaria de Puerto Rico
LOCAL_TZ = pytz.timezone('America/Puerto_Rico')


@app.route('/')
def list_commands():
    commands_list = {
        "!help": "Muestra la URL del servidor donde se puede acceder a más información.",
        "!newdocument [nombre] [url]": "Añade un nuevo documento con un nombre y una URL a la base de datos.",
        "!listdocuments": "Lista todos los documentos almacenados en la base de datos.",
        "!deletedocument [nombre]": "Elimina un documento de la base de datos por su nombre.",
    }

    # Lista de URLs adicionales del servidor
    urls_list = {
        "/notificaciones": "Muestra la página que lista las notificaciones manejadas por el bot con GitHub.",
        "/github-webhook": "Recibe eventos de GitHub y los procesa.",
        "/documentos": "Muestra los documentos del proyecto"
    }

    # Generar un HTML con la lista de comandos y agregar la etiqueta de verificación
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="google-site-verification" content="1gsxA927OIgR5IaXavEH3eXGksbzkSMRjBF5NvXP0Mk" /> <!-- Tu meta verificación aquí -->
        <title>Comandos del bot</title>
    </head>
    <body>
    <h1>Comandos del bot</h1>
    <ul>
    """

    for command, description in commands_list.items():
        html += f"<li><b>{command}</b>: {description}</li>"
    html += "</ul>"

    # Generar una sección para las URLs adicionales del servidor
    html += "<h2>Otras URLs del servidor</h2><ul>"
    for url, description in urls_list.items():
        html += f'<li><b><a href="{url}">{url}</a></b>: {description}</li>'
    html += "</ul>"

    html += """
    </body>
    </html>
    """

    return html
@app.route('/notificaciones')
def index():
    # Lista de todas las notificaciones que maneja el bot
    notifications = [
        "push",
        "issues",
        "issue_comment",
        "pull_request",
        "pull_request_review",
        "pull_request_review_comment",
        "release",
        "fork",
        "star",
        "repository",
        "branch_protection_rule",
        "milestone",
        "commit_comment",
        "collaborator",
        "deploy_key",
        "deployment",
        "deployment_status",
        "check_run",
        "check_suite",
        "discussion",
        "discussion_comment",
        "merge_group",
        "package",
        "page_build",
        "project",
        "project_card",
        "project_column",
        "registry_package",
        "repository_advisory",
        "repository_import",
        "repository_ruleset",
        "repository_vulnerability_alert",
        "secret_scanning_alert",
        "secret_scanning_alert_location",
        "security_and_analyses",
        "status",
        "team_add",
        "visibility_change",
        "watch",
        "wiki",
        "workflow_job",
        "workflow_run",
        "branch_or_tag_creation",
        "branch_or_tag_deletion",
        "branch_protection_configurations",
        "bypass_push_rulesets",
        "bypass_secret_scanning",
        "label"
    ]
    return "<h1>Notificaciones que maneja el bot</h1>" + "<ul>" + "".join(f"<li>{notification}</li>" for notification in notifications) + "</ul>"


@app.route('/documentos')
def lista_documentos():
    # Consulta a la base de datos para obtener todos los documentos
    documentos = collection.find()

    # Si no hay documentos, mostrar un mensaje
    if collection.count_documents({}) == 0:
        return "<h1>No hay documentos almacenados.</h1>"

    # Generar un HTML con la lista de documentos
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Lista de Documentos</title>
    </head>
    <body>
        <h1>Documentos Almacenados</h1>
        <ul>
    """

    # Agregar los documentos al HTML en forma de lista
    for doc in documentos:
        nombre = doc.get('nombre', 'Sin Nombre')
        url = doc.get('url', '#')
        html += f"<li><b>{nombre}</b>: <a href='{url}'>{url}</a></li>"

    # Cerrar la lista y el cuerpo del HTML
    html += """
        </ul>
    </body>
    </html>
    """

    return html



@app.route('/github-webhook', methods=['POST'])
def github_webhook():
    data = request.json
    event = request.headers.get('X-GitHub-Event')

    if event == "push":
        handle_push_event(data)
    elif event == "issues":
        handle_issue_event(data)
    elif event == "issue_comment":
        handle_issue_comment_event(data)
    elif event == "pull_request":
        handle_pull_request_event(data)
    elif event == "pull_request_review":
        handle_pull_request_review_event(data)
    elif event == "pull_request_review_comment":
        handle_pull_request_review_comment_event(data)
    elif event == "release":
        handle_release_event(data)
    elif event == "fork":
        handle_fork_event(data)
    elif event == "star":
        handle_star_event(data)
    elif event == "repository":
        handle_repository_event(data)
    elif event == "branch_protection_rule":
        handle_branch_protection_rules_event(data)
    elif event == "milestone":
        handle_milestone_event(data)
    elif event == "commit_comment":
        handle_commit_comment_event(data)
    elif event == "collaborator":
        handle_collaborator_event(data)
    elif event == "deploy_key":
        handle_deploy_key_event(data)
    elif event == "deployment":
        handle_deployment_event(data)
    elif event == "deployment_status":
        handle_deployment_status_event(data)
    elif event == "check_run":
        handle_check_run_event(data)
    elif event == "check_suite":
        handle_check_suite_event(data)
    elif event == "discussion":
        handle_discussion_event(data)
    elif event == "discussion_comment":
        # handle_discussion_comment_event(data)
        # asyncio.run(handle_discussion_comment_event(data))  # Cambiar esta línea
        bot.loop.create_task(handle_discussion_comment_event(data))
    elif event == "merge_group":
        handle_merge_group_event(data)
    elif event == "package":
        handle_package_event(data)
    elif event == "page_build":
        handle_page_build_event(data)
    elif event == "project":
        handle_project_event(data)
    elif event == "project_card":
        handle_project_card_event(data)
    elif event == "project_column":
        handle_project_column_event(data)
    elif event == "registry_package":
        handle_registry_package_event(data)
    elif event == "repository_advisory":
        handle_repository_advisory_event(data)
    elif event == "repository_import":
        handle_repository_import_event(data)
    elif event == "repository_ruleset":
        handle_repository_ruleset_event(data)
    elif event == "repository_vulnerability_alert":
        handle_repository_vulnerability_alert_event(data)
    elif event == "secret_scanning_alert":
        handle_secret_scanning_alert_event(data)
    elif event == "secret_scanning_alert_location":
        handle_secret_scanning_alert_location_event(data)
    elif event == "security_and_analyses":
        handle_security_and_analyses_event(data)
    elif event == "status":
        handle_status_event(data)
    elif event == "team_add":
        handle_team_add_event(data)
    elif event == "visibility_change":
        handle_visibility_change_event(data)
    elif event == "watch":
        handle_watch_event(data)
    elif event == "wiki":
        handle_wiki_event(data)
    elif event == "workflow_job":
        handle_workflow_job_event(data)
    elif event == "workflow_run":
        handle_workflow_run_event(data)
    elif event == "branch_or_tag_creation":
        handle_branch_or_tag_creation_event(data)
    elif event == "branch_or_tag_deletion":
        handle_branch_or_tag_deletion_event(data)
    elif event == "branch_protection_configurations":
        handle_branch_protection_configurations_event(data)
    elif event == "bypass_push_rulesets":
        handle_bypass_push_rulesets_event(data)
    elif event == "bypass_secret_scanning":
        handle_bypass_secret_scanning_event(data)
    elif event == "label":
        handle_label_event(data)

    return 'OK', 200


def send_to_discord(message, data=None):
    channel = bot.get_channel(1278770255711309906)  # Reemplaza con el ID de tu canal
    # if data:
    #     # Convertir el diccionario a un string JSON
    #     json_bytes = json.dumps(data, indent=4, ensure_ascii=False).encode('utf-8')
    #     json_file = File(io.BytesIO(json_bytes), filename="data.json")
    #     # Enviar mensaje personalizado con el archivo adjunto
    #     message = f"{message}\nEl JSON completo está adjunto."
    #     bot.loop.create_task(channel.send(message, file=json_file))
    # else:
    bot.loop.create_task(channel.send(message))


# Aquí están todos los manejadores de eventos
def handle_push_event(data):
    pusher = data['pusher']['name']
    branch = data['ref'].split('/')[-1]
    commit_message = data['head_commit']['message']
    commit_url = data['head_commit']['url']
    repo_name = data['repository']['full_name']
    message = f"🚀 @everyone ¡Nuevo push en **{repo_name}**! \n🔧 **{pusher}** ha realizado un commit en la rama '**{branch}**'.\n\n**Mensaje del commit:** [{commit_message}]({commit_url})"
    send_to_discord(message, data)



def handle_issue_event(data):
    action = data['action']
    issue_title = data['issue']['title']
    issue_url = data['issue']['html_url']
    repo_name = data['repository']['full_name']
    message = f"🐛 **Issue** '{issue_title}' fue **{action}** en **{repo_name}**.\n🔗 [Ver issue]({issue_url})"
    send_to_discord(message, data)


def handle_issue_comment_event(data):
    action = data['action']
    comment_url = data['comment']['html_url']
    issue_title = data['issue']['title']
    repo_name = data['repository']['full_name']
    message = f"💬 ¡Nuevo comentario en el issue '**{issue_title}**' en **{repo_name}**!\n🔗 **Acción:** {action} | [Ver comentario]({comment_url})"
    send_to_discord(message, data)


def handle_pull_request_event(data):
    action = data['action']
    pr_title = data['pull_request']['title']
    pr_url = data['pull_request']['html_url']
    repo_name = data['repository']['full_name']
    message = f"🔄 @everyone **Pull request** '**{pr_title}**' en **{repo_name}** fue {action}.\n🔗 [Ver pull request]({pr_url})"
    send_to_discord(message, data)


def handle_pull_request_review_event(data):
    action = data['action']
    pr_title = data['pull_request']['title']
    repo_name = data['repository']['full_name']
    message = f"🔍 **Revisión del PR** '{pr_title}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_pull_request_review_comment_event(data):
    action = data['action']
    comment_url = data['comment']['html_url']
    pr_title = data['pull_request']['title']
    repo_name = data['repository']['full_name']
    message = f"💬 **Comentario en revisión del PR** '{pr_title}' fue **{action}** en **{repo_name}**.\n🔗 [Ver comentario]({comment_url})"
    send_to_discord(message, data)


def handle_release_event(data):
    action = data['action']
    release_name = data['release']['name']
    release_url = data['release']['html_url']
    repo_name = data['repository']['full_name']
    message = f"🚀 **Release** '{release_name}' fue **{action}** en **{repo_name}**.\n🔗 [Ver release]({release_url})"
    send_to_discord(message, data)


def handle_fork_event(data):
    forkee_full_name = data['forkee']['full_name']
    forkee_url = data['forkee']['html_url']
    repo_name = data['repository']['full_name']
    message = f"🍴 **Repositorio** {repo_name} fue **forked**.\n🔗 [{forkee_full_name}]({forkee_url})"
    send_to_discord(message, data)


def handle_star_event(data):
    action = data['action']
    repo_name = data['repository']['full_name']
    user = data['sender']['login']
    user_profile_url = data['sender']['html_url']

    if action == "created":
        message = f"⭐ ¡{user} ha marcado el repositorio [{repo_name}](https://github.com/{repo_name}) con una estrella! Puedes ver su perfil [aquí]({user_profile_url})."
    elif action == "deleted":
        message = f"⚠️ {user} ha eliminado la estrella del repositorio [{repo_name}](https://github.com/{repo_name}). Puedes ver su perfil [aquí]({user_profile_url})."

    send_to_discord(message, data)



def handle_repository_event(data):
    action = data['action']
    repo_name = data['repository']['full_name']
    message = f"🏗️ @everyone ¡Repositorio **{repo_name}** ha sido **{action}**!"
    send_to_discord(message, data)


def handle_branch_protection_rules_event(data):
    action = data['action']
    repo_name = data['repository']['full_name']
    message = f"Regla de protección de rama {action} en {repo_name}"
    send_to_discord(message, data)


def handle_milestone_event(data):
    action = data['action']
    milestone_title = data['milestone']['title']
    repo_name = data['repository']['full_name']
    message = f"🎯 @everyone ¡Milestone en **{repo_name}**! \n**Milestone:** '{milestone_title}' fue **{action}**."
    send_to_discord(message, data)


def handle_commit_comment_event(data):
    action = data['action']
    comment_url = data['comment']['html_url']
    commit_id = data['comment']['commit_id']
    repo_name = data['repository']['full_name']
    message = f"✏️ @everyone **Comentario en commit** en **{repo_name}**!\n🔗 **Acción:** {action} en el commit **{commit_id}**.\n[Ver comentario]({comment_url})"
    send_to_discord(message, data)


def handle_collaborator_event(data):
    action = data['action']
    collaborator = data['collaborator']['login']
    repo_name = data['repository']['full_name']
    message = f"👥 **Colaborador** '{collaborator}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_deploy_key_event(data):
    action = data['action']
    key_title = data['key']['title']
    repo_name = data['repository']['full_name']
    message = f"🔑 **Clave de despliegue** '{key_title}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_deployment_status_event(data):
    state = data['deployment_status']['state']
    deployment_url = data['deployment_status']['target_url']
    repo_name = data['repository']['full_name']
    message = f"🚦 **Estado de despliegue** cambió a **{state}** en **{repo_name}**.\n🔗 [Ver estado]({deployment_url})"
    send_to_discord(message, data)


def handle_deployment_event(data):
    action = data['action']
    deployment_id = data['deployment']['id']
    repo_name = data['repository']['full_name']
    message = f"🚀 **Despliegue** con ID **{deployment_id}** fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_check_run_event(data):
    action = data['action']
    check_name = data['check_run']['name']
    repo_name = data['repository']['full_name']
    message = f"✅ **Check run** '{check_name}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_check_suite_event(data):
    action = data['action']
    repo_name = data['repository']['full_name']
    message = f"✅ **Check suite** fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_discussion_event(data):
    action = data['action']
    discussion_title = data['discussion']['title']
    discussion_url = data['discussion']['html_url']
    repo_name = data['repository']['full_name']
    message = f"@everyone 🗣️ **Discusión** '{discussion_title}' fue **{action}** en **{repo_name}**.\n🔗 [Ver discusión]({discussion_url})"
    send_to_discord(message, data)


async def handle_discussion_comment_event(data):
    action = data['action']
    discussion_id = data['discussion']['node_id']  # Obtener el ID de la discusión
    comment_url = data['comment']['html_url']
    comment_body = data['comment']['body']
    discussion_title = data['discussion']['title']
    repo_name = data['repository']['full_name']
    author = data['comment']['user']['login']  # Obtener el nombre del autor del comentario en GitHub

    message = f"💬 **Comentario en discusión** '{discussion_title}' fue **{action}** en **{repo_name}**.\n🔗 [Ver comentario]({comment_url})"
    send_to_discord(message, data)

    if "[Discord message]" in comment_body:
        return  # No procesar el comentario, ya que viene de Discord

    github_message = f"[GitHub message] **{author}**:\n\n{comment_body}"

    # Verificar si el comentario proviene de una de las discusiones específicas
    if discussion_id in [
        'D_kwDOMoKp284AbRwu',  # green-team-notifications
        'D_kwDOMoKp284AbRww',  # general
        'D_kwDOMoKp284AbRwv'  # blue-team-trolley-metrics
    ]:
        # Obtener el canal de Discord correspondiente usando el diccionario
        discord_channel_id = None
        for channel, d_id in channel_to_discussion.items():
            if d_id == discussion_id:
                discord_channel_id = channel
                break

        # Verificar si se encontró el canal correspondiente
        if discord_channel_id:
            # Obtener el canal de Discord usando el ID
            channel = bot.get_channel(discord_channel_id)

            # Si se encontró el canal, enviar el mensaje
            if channel:
                print(f"Enviando mensaje al canal: {discord_channel_id}")  # Mensaje para depuración
                await channel.send(github_message)
            else:
                print(f"Error: No se pudo obtener el canal con ID {discord_channel_id}")
        else:
            print(f"Error: No se encontró un canal para la discusión con ID {discussion_id}")


def handle_merge_group_event(data):
    action = data['action']
    merge_group_url = data['merge_group']['html_url']
    repo_name = data['repository']['full_name']
    message = f"🔀 **Merge group** fue **{action}** en **{repo_name}**.\n🔗 [Ver merge group]({merge_group_url})"
    send_to_discord(message, data)


def handle_package_event(data):
    action = data['action']
    package_name = data['package']['name']
    repo_name = data['repository']['full_name']
    message = f"📦 **Paquete** '{package_name}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_page_build_event(data):
    build_status = data['build']['status']
    build_url = data['build']['html_url']
    repo_name = data['repository']['full_name']
    message = f"🛠️ **Page build** status: **{build_status}** en **{repo_name}**.\n🔗 [Ver build]({build_url})"
    send_to_discord(message, data)


def handle_project_event(data):
    action = data['action']
    project_name = data['project']['name']
    repo_name = data['repository']['full_name']
    message = f"📈 **Proyecto** '{project_name}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_project_card_event(data):
    action = data['action']
    card_note = data['project_card']['note']
    repo_name = data['repository']['full_name']
    message = f"🃏 **Tarjeta de proyecto** fue **{action}** en **{repo_name}**.\n📋 Nota: '{card_note}'"
    send_to_discord(message, data)


def handle_project_column_event(data):
    action = data['action']
    column_name = data['project_column']['name']
    repo_name = data['repository']['full_name']
    message = f"📊 **Columna de proyecto** '{column_name}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_registry_package_event(data):
    action = data['action']
    package_name = data['package']['name']
    repo_name = data['repository']['full_name']
    message = f"📦 **Paquete de registro** '{package_name}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_repository_advisory_event(data):
    action = data['action']
    advisory_title = data['advisory']['title']
    repo_name = data['repository']['full_name']
    message = f"📢 **Asesoría** '{advisory_title}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_repository_import_event(data):
    action = data['action']
    repo_name = data['repository']['full_name']
    message = f"🔄 **Importación de repositorio** fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_repository_ruleset_event(data):
    action = data['action']
    ruleset_name = data['ruleset']['name']
    repo_name = data['repository']['full_name']
    message = f"⚙️ **Conjunto de reglas** '{ruleset_name}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_repository_vulnerability_alert_event(data):
    action = data['action']
    alert_title = data['alert']['security_advisory']['summary']
    repo_name = data['repository']['full_name']
    message = f"🚨 **Alerta de vulnerabilidad** '{alert_title}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_secret_scanning_alert_event(data):
    action = data['action']
    alert_title = data['alert']['secret_type']
    repo_name = data['repository']['full_name']
    message = f"🔍 **Alerta de escaneo de secretos** '{alert_title}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_secret_scanning_alert_location_event(data):
    action = data['action']
    alert_location = data['location']['path']
    repo_name = data['repository']['full_name']
    message = f"🔍 **Alerta de escaneo de secretos** en la ubicación '{alert_location}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_security_and_analyses_event(data):
    action = data['action']
    repo_name = data['repository']['full_name']
    message = f"🔐 **Seguridad y análisis** fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_status_event(data):
    state = data['state']
    commit_sha = data['sha']
    target_url = data['target_url']
    repo_name = data['repository']['full_name']
    message = f"📊 **Estado del commit** {commit_sha} cambió a **{state}** en **{repo_name}**.\n🔗 [Ver estado]({target_url})"
    send_to_discord(message, data)



def handle_team_add_event(data):
    action = data['action']
    team_name = data['team']['name']
    repo_name = data['repository']['full_name']
    message = f"👥 **Equipo** '{team_name}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_visibility_change_event(data):
    action = data['action']
    repo_name = data['repository']['full_name']
    message = f"👁️ **Visibilidad** del repositorio **{repo_name}** fue **{action}**."
    send_to_discord(message, data)


def handle_watch_event(data):
    action = data['action']
    repo_name = data['repository']['full_name']
    user = data['sender']['login']
    repo_url = data['repository']['html_url']
    user_url = data['sender']['html_url']

    if action == "started":
        message = f"👀 **{user}** ha comenzado a seguir el repositorio [{repo_name}]({repo_url}). ¡Descubre qué hay de interesante [aquí]({user_url})!"
    elif action == "deleted":
        message = f"❌ **{user}** ha dejado de seguir el repositorio [{repo_name}]({repo_url}). ¡Visita su perfil [aquí]({user_url}) para más detalles!"

    send_to_discord(message, data)


def handle_wiki_event(data):
    action = data['action']
    page_title = data['page']['title']
    page_url = data['page']['html_url']
    repo_name = data['repository']['full_name']
    message = f"📚 **Página wiki** '{page_title}' fue **{action}** en **{repo_name}**.\n🔗 [Ver página]({page_url})"
    send_to_discord(message, data)


def handle_workflow_job_event(data):
    action = data['action']
    workflow_job_name = data['workflow_job']['name']
    repo_name = data['repository']['full_name']
    message = f"🛠️ **Trabajo del workflow** '{workflow_job_name}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_workflow_run_event(data):
    action = data['action']
    workflow_name = data['workflow_run']['name']
    repo_name = data['repository']['full_name']
    message = f"🚀 **Ejecución de workflow** '{workflow_name}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_branch_or_tag_creation_event(data):
    ref_type = data['ref_type']
    ref_name = data['ref']
    repo_name = data['repository']['full_name']
    message = f"🌱 **Nuevo {ref_type}** creado: {ref_name} en **{repo_name}**."
    send_to_discord(message, data)


def handle_branch_or_tag_deletion_event(data):
    ref_type = data['ref_type']
    ref_name = data['ref']
    repo_name = data['repository']['full_name']
    message = f"🗑️ **{ref_type.capitalize()} eliminado**: {ref_name} en **{repo_name}**."
    send_to_discord(message, data)


def handle_branch_protection_configurations_event(data):
    action = data['action']
    repo_name = data['repository']['full_name']
    message = f"🛡️ **Configuraciones de protección de rama** {action} en **{repo_name}**."
    send_to_discord(message, data)


def handle_bypass_push_rulesets_event(data):
    action = data['action']
    rule_name = data.get('rule_name', 'desconocida')
    repo_name = data['repository']['full_name']
    message = f"🚧 **Solicitud de bypass** para la regla de push '{rule_name}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_bypass_secret_scanning_event(data):
    action = data['action']
    rule_name = data.get('rule_name', 'desconocida')
    repo_name = data['repository']['full_name']
    message = f"🚧 **Solicitud de bypass** para la protección de escaneo de secretos '{rule_name}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def handle_label_event(data):
    action = data['action']
    label_name = data['label']['name']
    repo_name = data['repository']['full_name']
    message = f"🏷️ **Etiqueta** '{label_name}' fue **{action}** en **{repo_name}**."
    send_to_discord(message, data)


def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))


@bot.command(name='ayuda')
async def help(ctx):
    # Aquí defines la URL de tu servidor donde estarán listadas las notificaciones
    server_url = "https://discord-bot-trolley-app-7cf3be57fb8b.herokuapp.com/"  # Reemplaza con la URL real de tu servidor
    message = f"Puedes ver la lista de comandos y detalles adicionales en la siguiente URL: {server_url}"
    await ctx.send(message)

@bot.command(name='notificaciones')
async def notificaciones(ctx):
    # Aquí defines la URL de tu servidor donde estarán listadas las notificaciones
    server_url = "https://discord-bot-trolley-app-7cf3be57fb8b.herokuapp.com/notificaciones"  # Reemplaza con la URL real de tu servidor
    message = f"Puedes ver la lista de notificaciones en la siguiente URL: {server_url}"
    await ctx.send(message)


# Comando para añadir un nuevo documento
@bot.command(name='newdocument')
async def newdocument(ctx, nombre: str, url: str):
    # Insertar el documento en la base de datos
    collection.insert_one({"nombre": nombre, "url": url})
    await ctx.send(f"Documento '{nombre}' añadido con éxito.")

# Comando para listar todos los documentos
@bot.command(name='listdocuments')
async def listdocuments(ctx):
    documentos = collection.find()
    if collection.count_documents({}) == 0:
        await ctx.send("No hay documentos almacenados.")
    else:
        mensaje = "Documentos almacenados:\n"
        for doc in documentos:
            mensaje += f"**{doc['nombre']}**: {doc['url']}\n"
        await ctx.send(mensaje)

# Comando para eliminar un documento por su nombre
@bot.command(name='deletedocument')
async def deletedocument(ctx, nombre: str):
    resultado = collection.delete_one({"nombre": nombre})
    if resultado.deleted_count > 0:
        await ctx.send(f"Documento '{nombre}' eliminado con éxito.")
    else:
        await ctx.send(f"No se encontró un documento con el nombre '{nombre}'.")


# Este patrón captura el formato esperado: nombre del documento seguido por la URL
document_pattern = re.compile(r"(.+):\s*(https?://\S+)")


@bot.event
async def on_message(message):
    # Evitar que el bot responda a sus propios mensajes
    if message.author == bot.user:
        return

    if message.channel.name == 'resources':  # Verifica si el mensaje es del canal correcto
        match = document_pattern.match(message.content)
        if match:
            document_name = match.group(1)
            document_url = match.group(2)

            # Pregunta al usuario si quiere agregar el documento
            response = await message.channel.send(
                f"@{message.author} ¿Quieres añadir el documento '{document_name}' con la URL {document_url} a la lista de documentos? Responde con 'y' para sí o 'n' para no.")

            def check(m):
                return m.author == message.author and m.channel == message.channel and m.content.lower() in ['y', 'n']

            # Espera la respuesta del usuario
            try:
                reply = await bot.wait_for('message', check=check, timeout=30.0)
                if reply.content.lower() == 'y':
                    # Aquí se agrega el documento con el nombre y la URL completos
                    collection.insert_one({"nombre": document_name, "url": document_url})
                    confirmation = await message.channel.send(f"Documento '{document_name}' añadido con éxito.")
                else:
                    confirmation = await message.channel.send("Operación cancelada.")

                # Eliminar solo los mensajes generados por la interacción
                await asyncio.sleep(5)  # Esperar 5 segundos antes de borrar los mensajes
                await response.delete()
                await reply.delete()
                await confirmation.delete()

            except asyncio.TimeoutError:
                timeout_message = await message.channel.send("Se agotó el tiempo de espera para la respuesta.")
                await asyncio.sleep(5)
                await response.delete()
                await timeout_message.delete()

    # Asegúrate de procesar otros comandos del bot
    await bot.process_commands(message)


def get_current_time():
    return datetime.now(LOCAL_TZ)

# Variable global para almacenar el canal donde se inició la reunión
reunion_channel = None

@bot.command(name="iniciar_reunion")
async def iniciar_reunion(ctx):
    global reunion_activa, event_log, voice_channel_data, durations, reunion_channel

    # Verificar si el autor está en un canal de voz
    if ctx.author.voice and ctx.author.voice.channel:

        if not reunion_activa:
            reunion_activa = True
            event_log = "Reunión iniciada:\n"
            voice_channel_data = {}
            durations = {}
            reunion_channel = ctx.channel  # Guardar el canal donde se inició la reunión
        else:
            await ctx.send("La reunión ya está activa.")
            return

        voice_channel = ctx.author.voice.channel
        members_in_channel = voice_channel.members

        # Si el autor no está en la lista de miembros (edge case), lo añadimos manualmente
        if ctx.author not in members_in_channel:
            members_in_channel.append(ctx.author)

        for member in members_in_channel:  # Registrar a todos los miembros presentes
            if member.bot:
                continue  # Ignorar los bots
            current_time = get_current_time().strftime('%H:%M:%S')
            event_log += f"{member.name} ya estaba en el canal de voz a las {current_time}\n"
            voice_channel_data[member.id] = get_current_time()  # Registrar la hora actual como su tiempo de entrada

    else:
        await ctx.send("No estás en un canal de voz.")
        return

    await ctx.send("¡La reunión ha comenzado! Se empezarán a registrar los eventos.")


# Evento para registrar cuando un usuario entra o sale de un canal de voz
@bot.event
async def on_voice_state_update(member, before, after):
    global event_log, voice_channel_data, durations, reunion_activa

    if not reunion_activa:
        return  # No hacer nada si la reunión no está activa

    current_time = get_current_time().strftime('%H:%M:%S')

    # Si el usuario se une a un canal de voz
    if before.channel is None and after.channel is not None:
        event_log += f"{member.name} entró al canal de voz a las {current_time}\n"
        # Registrar el tiempo de entrada del usuario
        voice_channel_data[member.id] = get_current_time()

    # Si el usuario sale de un canal de voz
    elif before.channel is not None and after.channel is None:
        event_log += f"{member.name} salió del canal de voz a las {current_time}\n"
        # Calcular el tiempo que el usuario estuvo en el canal
        if member.id in voice_channel_data:
            time_spent = get_current_time() - voice_channel_data.pop(member.id)
            durations[member.id] = durations.get(member.id, timedelta()) + time_spent


# Comando para finalizar la reunión y generar el archivo de texto con el resumen
@bot.command(name="finalizar_reunion")
async def finalizar_reunion(ctx):
    global event_log, durations, reunion_activa, voice_channel_data

    if reunion_activa:
        # Registrar la salida de los usuarios que aún están en el canal de voz
        for member_id in list(voice_channel_data.keys()):
            member = await ctx.guild.fetch_member(member_id)
            current_time = get_current_time().strftime('%H:%M:%S')
            event_log += f"{member.name} salió del canal de voz a las {current_time} (fin de la reunión)\n"
            # Calcular el tiempo que el usuario estuvo en el canal
            time_spent = get_current_time() - voice_channel_data.pop(member_id)
            durations[member_id] = durations.get(member_id, timedelta()) + time_spent

        # Generar el resumen del tiempo que cada usuario estuvo en la reunión
        event_log += "\nResumen de la reunión:\n"
        for user_id, total_time in durations.items():
            member = await ctx.guild.fetch_member(user_id)
            event_log += f"{member.name} estuvo en el canal por {str(total_time)}\n"

        # Guardar los eventos en un archivo de texto
        with open("registro_reunion.txt", "w", encoding="utf-8") as f:
            f.write(event_log)

        # Enviar el archivo al canal donde se ejecutó el comando
        await ctx.send("La reunión ha terminado. Aquí está el registro de eventos:",
                       file=discord.File("registro_reunion.txt"))

        # Reiniciar los registros para futuras reuniones
        event_log = ""
        voice_channel_data = {}
        durations = {}
        reunion_activa = False
        reunion_channel = None  # Resetear el canal de la reunión
    else:
        await ctx.send("No hay ninguna reunión activa.")


# Comando para obtener los issues del repositorio
@bot.command()
async def all_issues(ctx):
    """
    Comando de Discord para obtener y enviar todos los issues (abiertos y cerrados)
    """
    # Llamar a la función get_all_issues
    issues = get_all_issues(GITHUB_API_TOKEN=GITHUB_TOKEN)

    if issues:
        # Preparar el mensaje con los títulos de los issues
        message = "Issues del proyecto:\n"
        for issue in issues:
            title = issue['content']['title']
            url = issue['content']['url']
            message += f"- {title}: {url}\n"

        # Enviar el mensaje al canal de Discord
        await ctx.send(message)
    else:
        await ctx.send("No se encontraron issues.")


@bot.command()
async def open_issues(ctx):
    """
    Comando de Discord para obtener y enviar solo los issues abiertos
    """
    # Llamar a la función get_open_issues
    issues = get_open_issues(GITHUB_API_TOKEN=GITHUB_TOKEN)

    if issues:
        # Preparar el mensaje con los títulos de los issues abiertos
        message = "Issues abiertos del proyecto:\n"
        for issue in issues:
            title = issue['content']['title']
            url = issue['content']['url']
            message += f"- {title}: {url}\n"

        # Enviar el mensaje al canal de Discord
        await ctx.send(message)
    else:
        await ctx.send("No hay issues abiertos.")


@bot.command()
async def closed_issues(ctx):
    """
    Comando de Discord para obtener y enviar todos los issues cerrados del proyecto.
    """
    # Obtener todos los issues cerrados
    closed_issues = get_closed_issues(GITHUB_API_TOKEN=GITHUB_TOKEN)

    # Verificar si hay issues cerrados
    if closed_issues:
        # Preparar el mensaje con los títulos de los issues cerrados
        message = "Issues cerrados del proyecto:\n"
        for issue in closed_issues:
            title = issue['content']['title']
            url = issue['content']['url']
            message += f"- {title}: {url}\n"

        # Enviar el mensaje al canal de Discord
        await ctx.send(message)
    else:
        await ctx.send("No se encontraron issues cerrados.")

@bot.command()
async def closed_issues_by_milestone(ctx, milestone_title: str):
    """
    Comando de Discord para obtener y enviar los issues cerrados que pertenecen a un milestone específico.
    :param ctx: El contexto del comando de Discord.
    :param milestone_title: El título del milestone a filtrar.
    """
    # Obtener los issues cerrados filtrados por milestone
    closed_issues = get_closed_issues_by_milestone(GITHUB_API_TOKEN=GITHUB_TOKEN, milestone_title=milestone_title)

    # Verificar si hay issues filtrados
    if closed_issues:
        # Preparar el mensaje con los títulos de los issues filtrados
        message = f"Issues cerrados del milestone '{milestone_title}':\n"
        for issue in closed_issues:
            title = issue['content']['title']
            url = issue['content']['url']
            message += f"- {title}: {url}\n"

        # Enviar el mensaje al canal de Discord
        await ctx.send(message)
    else:
        await ctx.send(f"No se encontraron issues cerrados para el milestone '{milestone_title}'.")


@bot.command()
async def open_issues_by_milestone(ctx, milestone_title: str):
    """
    Comando de Discord para obtener y enviar los issues abiertos que pertenecen a un milestone específico.
    :param ctx: El contexto del comando de Discord.
    :param milestone_title: El título del milestone a filtrar.
    """
    # Obtener los issues abiertos
    open_issues = get_open_issues(GITHUB_API_TOKEN=GITHUB_TOKEN)

    # Filtrar los issues por el milestone especificado
    filtered_issues = filter_issues_by_milestone(open_issues, milestone_title)

    # Verificar si hay issues filtrados
    if filtered_issues:
        # Preparar el mensaje con los títulos de los issues filtrados
        message = f"Issues abiertos del milestone '{milestone_title}':\n"
        for issue in filtered_issues:
            title = issue['content']['title']
            url = issue['content']['url']
            message += f"- {title}: {url}\n"

        # Enviar el mensaje al canal de Discord
        await ctx.send(message)
    else:
        await ctx.send(f"No hay issues abiertos para el milestone '{milestone_title}'.")


@bot.command()
async def all_issues_by_milestone(ctx, milestone_title: str):
    """
    Comando de Discord para obtener y enviar todos los issues (abiertos y cerrados) que pertenecen a un milestone específico.
    :param ctx: El contexto del comando de Discord.
    :param milestone_title: El título del milestone a filtrar.
    """
    # Obtener todos los issues
    all_issues = get_all_issues(GITHUB_API_TOKEN=GITHUB_TOKEN)

    # Filtrar los issues por el milestone especificado
    filtered_issues = filter_issues_by_milestone(all_issues, milestone_title)

    # Verificar si hay issues filtrados
    if filtered_issues:
        # Preparar el mensaje con los títulos de los issues filtrados
        message = f"Todos los issues del milestone '{milestone_title}':\n"
        for issue in filtered_issues:
            title = issue['content']['title']
            url = issue['content']['url']
            message += f"- {title}: {url}\n"

        # Enviar el mensaje al canal de Discord
        await ctx.send(message)
    else:
        await ctx.send(f"No hay issues para el milestone '{milestone_title}'.")


# @bot.command()
# async def milestone_points_without_dk(ctx, milestone_title: str):
#     """
#     Comando de Discord para obtener y sumar todos los puntos (Estimate) de los issues de un milestone (cerrados y abiertos) sin aplicar DK.
#     :param ctx: El contexto del comando de Discord.
#     :param milestone_title: El título del milestone a filtrar.
#     """
#     # Obtener todos los issues (cerrados y abiertos)
#     all_issues = get_all_issues(GITHUB_API_TOKEN=GITHUB_TOKEN)
#
#     # Filtrar los issues por el milestone especificado
#     milestone_issues = filter_issues_by_milestone(all_issues, milestone_title)
#
#     # Verificar si hay issues filtrados
#     if milestone_issues:
#         # Calcular los puntos totales sin DK
#         total_points = issues_total_points_without_dk(milestone_issues)
#
#         # Enviar el resultado al canal de Discord
#         await ctx.send(f"Puntuación total sin DK para el milestone '{milestone_title}': {total_points}")
#     else:
#         await ctx.send(f"No se encontraron issues para el milestone '{milestone_title}'.")


# @bot.command()
# async def milestone_points_with_dk(ctx, milestone_title: str):
#     """
#     Comando de Discord para obtener y sumar todos los puntos (Estimate) de los issues de un milestone (cerrados y abiertos) aplicando DK.
#     :param ctx: El contexto del comando de Discord.
#     :param milestone_title: El título del milestone a filtrar.
#     """
#     # Definir las fechas de inicio y fin del milestone (a ajustar manualmente según el milestone)
#     milestone_start = datetime(2024, 8, 29)  # Placeholder para la fecha de inicio
#     milestone_end = datetime(2024, 9, 20)  # Placeholder para la fecha de fin
#
#     # Obtener todos los issues (cerrados y abiertos)
#     all_issues = get_all_issues(GITHUB_API_TOKEN=GITHUB_TOKEN)
#
#     # Filtrar los issues por el milestone especificado
#     milestone_issues = filter_issues_by_milestone(all_issues, milestone_title)
#
#     # Verificar si hay issues filtrados
#     if milestone_issues:
#         # Calcular los puntos totales con DK aplicado
#         total_points_with_dk = issues_total_points_with_dk(milestone_issues, milestone_start, milestone_end)
#
#         # Enviar el resultado al canal de Discord
#         await ctx.send(f"Puntuación total con DK para el milestone '{milestone_title}': {total_points_with_dk}")
#     else:
#         await ctx.send(f"No se encontraron issues para el milestone '{milestone_title}'.")


@bot.command()
async def repo(ctx):
    # Llamar a la función de getStatistics.py
    repoData = get_repo(GITHUB_API_TOKEN=GITHUB_TOKEN)

    # Verificar si hubo un error
    if isinstance(repoData, str):
        await ctx.send(f"Error al obtener el repo: {repoData}")
    else:
        # Escribir los datos en un archivo de texto
        with open("repo_data.txt", "w", encoding="utf-8") as file:
            file.write(str(repoData))

        # Enviar el archivo al canal
        await ctx.send("Aquí están los datos del repositorio:", file=discord.File("repo_data.txt"))

@bot.command()
async def projects(ctx):
    # Llamar a la función de getStatistics.py
    repoProjects = get_project_items_with_custom_fields(GITHUB_API_TOKEN=GITHUB_TOKEN)

    # Verificar si hubo un error
    if isinstance(repoProjects, str):
        await ctx.send(f"Error al obtener el repo: {repoProjects}")
    else:
        # Escribir los datos en un archivo de texto
        with open("repo_data.txt", "w", encoding="utf-8") as file:
            file.write(str(repoProjects))

        # Enviar el archivo al canal
        await ctx.send("Aquí están los datos del repositorio:", file=discord.File("repo_data.txt"))


@bot.command()
async def milestone_points_without_dk(ctx, milestone_name: str):
    """
    Comando de Discord para calcular los puntos sin DK de todos los issues de un milestone específico.

    :param ctx: El contexto del comando en Discord.
    :param milestone_name: El nombre del milestone a filtrar.
    """

    # Llamar a la función para obtener los puntos sin DK
    total_points_without_dk = get_milestone_perfect_total_points_without_dk(GITHUB_API_TOKEN=GITHUB_TOKEN, milestone_name=milestone_name)

    # Responder en Discord con el resultado
    await ctx.send(f"Total de puntos sin DK para el milestone '{milestone_name}': {total_points_without_dk}")


@bot.command(name="milestone_points_with_dk")
async def milestone_points_with_dk(ctx, milestone_name: str):
    """
    Comando de Discord para obtener el total de puntos con DK para un milestone específico (abiertos y cerrados).
    """

    milestone_start = datetime(2024, 8, 29)  # Placeholder para la fecha de inicio
    milestone_end = datetime(2024, 9, 20)  # Placeholder para la fecha de fin
    if milestone_name == "Milestone #1":
        # Puedes ajustar estas fechas de inicio y fin de acuerdo con el milestone que estás utilizando
        milestone_start = datetime(2024, 8, 29)  # Placeholder para la fecha de inicio
        milestone_end = datetime(2024, 9, 20)  # Placeholder para la fecha de fin

    total_points_with_dk = get_milestone_perfect_total_points_with_dk(GITHUB_TOKEN, milestone_name, milestone_start,
                                                              milestone_end)

    await ctx.send(f"Total de puntos con DK para {milestone_name}: {total_points_with_dk}")


@bot.command(name="milestone_closed_points_with_dk")
async def milestone_closed_points_with_dk(ctx, milestone_name: str):
    """
    Comando de Discord para obtener el total de puntos con DK para todos los issues cerrados antes de la fecha de fin del milestone.

    :param ctx: El contexto del comando en Discord.
    :param milestone_name: El nombre del milestone a filtrar.
    """

    milestone_start = datetime(2024, 8, 29)  # Placeholder para la fecha de inicio
    milestone_end = datetime(2024, 9, 20)  # Placeholder para la fecha de fin
    if milestone_name == "Milestone #1":
        # Puedes ajustar estas fechas de inicio y fin de acuerdo con el milestone que estás utilizando
        milestone_start = datetime(2024, 8, 29)  # Placeholder para la fecha de inicio
        milestone_end = datetime(2024, 9, 20)  # Placeholder para la fecha de fin

    # Llamar a la función para obtener los puntos con DK para los issues cerrados antes de la fecha límite
    total_points_with_dk = get_milestone_closed_total_points_with_dk(GITHUB_TOKEN, milestone_name, milestone_start, milestone_end)

    # Responder en Discord con el resultado
    await ctx.send(f"Total de puntos con DK para los issues cerrados del milestone '{milestone_name}' antes de {milestone_end}: {total_points_with_dk}")


@bot.command(name="milestone_grade")
async def milestone_grade(ctx, milestone_name: str):
    """
    Comando para calcular el promedio de puntos con DK sobre puntos sin DK para todos los issues (cerrados y abiertos) de un milestone.

    :param ctx: Contexto del comando en Discord.
    :param milestone_name: El nombre del milestone.
    """
    milestone_start = datetime(2024, 8, 29)  # Placeholder para la fecha de inicio del milestone
    milestone_end = datetime(2024, 9, 20)  # Placeholder para la fecha de fin del milestone

    # Llamar a la función para calcular el promedio con DK de todos los issues
    average_with_dk = get_milestone_average_with_dk(GITHUB_TOKEN, milestone_name, milestone_start, milestone_end)
    average_with_dk_closed = get_milestone_closed_average_with_dk(GITHUB_TOKEN, milestone_name, milestone_start,
                                                                  milestone_end)

    # Enviar el resultado en el canal de Discord
    await ctx.send(f"El promedio de puntos con DK si todos los issues se cierran antes de la fecha limite para el milestone '{milestone_name}' es: {average_with_dk}\n"
                   f"El promedio de puntos con DK con los issues cerrados actuales para el milestone '{milestone_name}' es: {average_with_dk_closed}")



@bot.command(name="individual_grades")
async def individual_grades(ctx, milestone_name: str):
    """
    Comando para calcular y mostrar las notas individuales de cada persona en un milestone específico,
    tanto antes como después de ser multiplicadas por la nota del milestone. También muestra la nota del milestone.

    Incluye la cantidad de issues por persona, los puntos de cada issue y el total de puntos.

    :param ctx: Contexto del comando en Discord.
    :param milestone_name: El nombre del milestone.
    """
    milestone_start = datetime(2024, 8, 29)  # Placeholder para la fecha de inicio del milestone
    milestone_end = datetime(2024, 9, 20)  # Placeholder para la fecha de fin del milestone

    # Llamar a la función para calcular las notas individuales
    grades = calculate_individual_grades(GITHUB_TOKEN, milestone_name, milestone_start, milestone_end)

    # Calcular el promedio del milestone (todos los issues cerrados y abiertos con DK)
    milestone_average = get_milestone_average_with_dk(GITHUB_TOKEN, milestone_name, milestone_start, milestone_end)

    # Obtener todos los issues filtrados por el milestone
    milestone_issues = filter_issues_by_milestone(get_all_issues(GITHUB_TOKEN), milestone_name)

    # Calcular el total de puntos de todos los issues
    total_points = issues_total_points_without_dk(milestone_issues)

    # Calcular el promedio de puntos esperado por persona (en base a los puntos totales)
    assignee_issues = group_issues_by_assignee(milestone_issues)  # Agrupamos issues por persona
    num_personas = len(assignee_issues)  # Número total de personas que contribuyeron
    puntos_esperados_por_persona = total_points / num_personas if num_personas > 0 else 0

    # Preparar el mensaje con las notas
    grade_message = f"Resumen del milestone '{milestone_name}':\n"
    grade_message += f"Total de puntos en todos los issues: {total_points:.2f}\n"
    grade_message += f"Promedio de puntos esperado por persona: {puntos_esperados_por_persona:.2f}\n"
    grade_message += f"Nota del milestone (todos los issues con DK): {milestone_average:.2f}\n\n"

    # Mostrar notas individuales antes y después de multiplicar por la nota del milestone
    for assignee, (individual_grade, final_grade) in grades.items():
        assignee_issues_list = assignee_issues.get(assignee, [])
        num_issues = len(assignee_issues_list)
        issue_points = [issue['estimate']['number'] for issue in assignee_issues_list if 'estimate' in issue]
        total_issue_points = sum(issue_points)

        grade_message += (f"{assignee}:\n"
                          f"  - Issues asignados: {num_issues}\n"
                          f"  - Puntos por issue: {issue_points}\n"
                          f"  - Puntos totales: {total_issue_points:.2f}\n"
                          f"  - Nota individual antes del milestone: {individual_grade:.2f}\n"
                          f"  - Nota final (después de multiplicar por la del milestone): {final_grade:.2f}\n\n")

    # Enviar el mensaje al canal de Discord
    await ctx.send(grade_message)



@bot.command(name="unassigned_members")
async def unassigned_members(ctx):
    """
    Comando para mostrar la lista de colaboradores que aún no tienen un issue abierto asignado.

    :param ctx: Contexto del comando en Discord.
    """
    # Obtener la lista de colaboradores sin issues abiertos asignados
    unassigned_members = find_unassigned_members(GITHUB_TOKEN)

    # Generar el mensaje para mostrar en Discord
    if unassigned_members:
        message = "Los siguientes colaboradores aún no tienen un issue abierto asignado:\n"
        for member in unassigned_members:
            message += f"- {member}\n"
    else:
        message = "Todos los colaboradores tienen al menos un issue abierto asignado."

    # Enviar el mensaje al canal de Discord
    await ctx.send(message)




#
# # Función para comentar en la discusión de GitHub
# def comment_on_discussion_graphql(GITHUB_API_TOKEN, discussion_id, comment_body):
#     url = "https://api.github.com/graphql"
#     headers = {
#         "Authorization": f"Bearer {GITHUB_API_TOKEN}",
#         "Content-Type": "application/json"
#     }
#     query = """
#     mutation($discussionId: ID!, $body: String!) {
#       addDiscussionComment(input: {discussionId: $discussionId, body: $body}) {
#         comment {
#           id
#           body
#         }
#       }
#     }
#     """
#     variables = {
#         "discussionId": discussion_id,
#         "body": comment_body
#     }
#     data = {
#         "query": query,
#         "variables": variables
#     }
#     response = requests.post(url, json=data, headers=headers)
#     if response.status_code == 200:
#         print("Comment added successfully to GitHub discussion!")
#     else:
#         print(f"Error: {response.status_code}, {response.text}")


# # Evento para capturar mensajes en varios canales y publicarlos en las discusiones correspondientes en GitHub
# @bot.event
# async def on_message(message):
#     if "[GitHub message]" in message.content:
#         return  # Ignorar los mensajes del bot para evitar bucles
#
#     # Verificar si el canal de Discord está en nuestro diccionario de mapeo
#     if message.channel.id in channel_to_discussion:
#         # Obtener el ID de la discusión correspondiente en GitHub
#         discussion_id = channel_to_discussion[message.channel.id]
#
#         author_name = message.author.nick if message.author.nick else message.author.display_name
#
#         # Crear el cuerpo del comentario con el nombre del usuario de Discord
#         comment_body = f"[Discord message]**{author_name}** wrote:\n\n{message.content}"
#
#         # Publicar el mensaje en la discusión de GitHub correspondiente
#         comment_on_discussion_graphql(GITHUB_TOKEN, discussion_id, comment_body)
#
#     await bot.process_commands(message)  # Asegura que otros comandos del bot aún funcionen


@bot.event
async def on_ready():
    print(f'{bot.user} está conectado a Discord!')
    pass



if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(DISCORD_TOKEN)
