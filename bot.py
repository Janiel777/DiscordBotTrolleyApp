import io
import os
import discord
from discord.ext import commands
from flask import Flask, request, json
from threading import Thread
from discord import File
import requests

app = Flask(__name__)

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GITHUB_SECRET = os.getenv('GITHUB_SECRET')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

ORG_NAME = 'uprm-inso4116-2024-2025-s1'  # Propietario del repositorio
REPO_NAME = 'semester-project-trolley-tracker-app'  # Nombre del repositorio
DISCUSSION_NUMBER = 5  # Número de la discusión


TEAM1_DISCORD_CHANNEL_ID = 1278505988579659806

bot = commands.Bot(command_prefix="!")


@app.route('/')
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
        handle_discussion_comment_event(data)
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
    channel = bot.get_channel(1279109004353605703)  # Reemplaza con el ID de tu canal
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


def handle_discussion_comment_event(data):
    action = data['action']
    comment_url = data['comment']['html_url']
    discussion_title = data['discussion']['title']
    repo_name = data['repository']['full_name']
    message = f"💬 **Comentario en discusión** '{discussion_title}' fue **{action}** en **{repo_name}**.\n🔗 [Ver comentario]({comment_url})"
    send_to_discord(message, data)


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


@bot.command(name='notificaciones')
async def notificaciones(ctx):
    # Aquí defines la URL de tu servidor donde estarán listadas las notificaciones
    server_url = "https://discord-bot-trolley-app-7cf3be57fb8b.herokuapp.com/"  # Reemplaza con la URL real de tu servidor
    message = f"Puedes ver todas las notificaciones que manejo en la siguiente URL: {server_url}"
    await ctx.send(message)


# Escuchar mensajes en el canal de Discord
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Evita que el bot responda a sí mismo

    # Publicar el mensaje en la discusión de GitHub
    if message.channel.id == TEAM1_DISCORD_CHANNEL_ID:
        # send_to_github_discussion(message.content, message.author)
        pass

    # Procesar otros comandos del bot si es necesario
    await bot.process_commands(message)


def send_to_github_discussion(content, author):
    url = f"https://api.github.com/orgs/{ORG_NAME}/teams"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Incluye el nombre del autor en el mensaje
    message_body = f"**{author}** dijo:\n\n{content}"

    data = {
        "body": message_body
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("Equipos en la organización obtenidos con éxito.")
        print(response.json())
    else:
        print(f"Error al intentar obtener equipos: {response.status_code} - {response.text}")

@bot.event
async def on_ready():
    print(f'{bot.user} está conectado a Discord!')
    send_to_github_discussion("Prueba de mensaje", "TestUser")


if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(DISCORD_TOKEN)
