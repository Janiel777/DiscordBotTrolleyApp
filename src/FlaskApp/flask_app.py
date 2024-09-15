from environment_variables import MONGO_URI, DISCORD_TOKEN
from flask import Flask, request
import pymongo
import os
from threading import Thread
from DiscordBot.bot import bot
from DiscordBot.github_webhook_event_handlers import (
                            handle_push_event, handle_issue_event, handle_issue_comment_event, handle_pull_request_event,
                            handle_pull_request_review_event, handle_pull_request_review_comment_event,
                            handle_release_event, handle_fork_event, handle_star_event, handle_repository_event,
                            handle_branch_protection_rules_event, handle_milestone_event, handle_commit_comment_event,
                            handle_collaborator_event, handle_deploy_key_event, handle_deployment_event,
                            handle_deployment_status_event, handle_check_run_event, handle_check_suite_event,
                            handle_discussion_event, handle_discussion_comment_event, handle_merge_group_event,
                            handle_package_event, handle_page_build_event, handle_project_event, handle_project_card_event,
                            handle_project_column_event, handle_registry_package_event, handle_repository_advisory_event,
                            handle_repository_import_event, handle_repository_ruleset_event, handle_repository_vulnerability_alert_event,
                            handle_secret_scanning_alert_event, handle_secret_scanning_alert_location_event, handle_security_and_analyses_event,
                            handle_status_event, handle_team_add_event, handle_visibility_change_event, handle_watch_event,
                            handle_wiki_event, handle_workflow_job_event, handle_workflow_run_event,
                            handle_branch_or_tag_creation_event, handle_branch_or_tag_deletion_event, handle_branch_protection_configurations_event,
                            handle_bypass_push_rulesets_event, handle_bypass_secret_scanning_event, handle_label_event)

# Configurar Flask
app = Flask(__name__)


client = pymongo.MongoClient(MONGO_URI)
db = client['trolleyAppDB']
collection = db['documents']

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

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))



if __name__ == "__main__":
    # Ejecutar Flask en un hilo separado
    Thread(target=run_flask).start()

    # Ejecutar el bot de Discord en el hilo principal
    bot.run(DISCORD_TOKEN)