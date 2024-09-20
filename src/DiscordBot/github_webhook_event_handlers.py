import requests

from DiscordBot.bot import send_to_discord, bot
from environment_variables import GITHUB_TOKEN

# Lista de usuarios permitidos para cerrar issues
USUARIOS_PERMITIDOS = ['gabrielpadilla7', 'Yahid1']
# URL de la API de GitHub GraphQL
GITHUB_GRAPHQL_API_URL = 'https://api.github.com/graphql'


# Función para hacer una solicitud GraphQL
def ejecutar_consulta_graphql(query, variables):
    headers = {
        'Authorization': f'bearer {GITHUB_TOKEN}',
        'Content-Type': 'application/json'
    }

    response = requests.post(
        GITHUB_GRAPHQL_API_URL,
        json={'query': query, 'variables': variables},
        headers=headers
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error en la solicitud GraphQL: {response.status_code}, {response.text}")


# Función para reabrir un issue usando GraphQL
def reabrir_issue_graphql(issue_id):
    mutation = """
    mutation($issueId: ID!) {
      updateIssue(input: {id: $issueId, state: OPEN}) {
        issue {
          id
          state
        }
      }
    }
    """
    variables = {'issueId': issue_id}

    resultado = ejecutar_consulta_graphql(mutation, variables)

    if 'errors' in resultado:
        print(f"Error al reabrir el issue: {resultado['errors']}")
    else:
        print("Issue reabierto exitosamente")


# Función para agregar un comentario en el issue
def agregar_comentario_issue(issue_id, comentario):
    mutation = """
    mutation($issueId: ID!, $body: String!) {
      addComment(input: {subjectId: $issueId, body: $body}) {
        comment {
          id
          body
        }
      }
    }
    """
    variables = {'issueId': issue_id, 'body': comentario}

    resultado = ejecutar_consulta_graphql(mutation, variables)

    if 'errors' in resultado:
        print(f"Error al agregar comentario en el issue: {resultado['errors']}")
    else:
        print("Comentario agregado exitosamente")

# Aquí están todos los manejadores de eventos
def handle_push_event(data):
    pusher = data['pusher']['name']
    branch = data['ref'].split('/')[-1]
    commit_message = data['head_commit']['message']
    commit_url = data['head_commit']['url']
    repo_name = data['repository']['full_name']
    message = f"🚀 @everyone ¡Nuevo push en **{repo_name}**! \n🔧 **{pusher}** ha realizado un commit en la rama '**{branch}**'.\n\n**Mensaje del commit:** [{commit_message}]({commit_url})"
    send_to_discord(message, data)


# Función para manejar eventos de issue
def handle_issue_event(data):
    action = data['action']
    issue_title = data['issue']['title']
    issue_url = data['issue']['html_url']
    issue_id = data['issue']['node_id']  # Obtener el ID del issue para GraphQL
    repo_name = data['repository']['full_name']

    if action == 'closed':
        closed_by = data['sender']['login']  # Usuario que cerró el issue

        if closed_by not in USUARIOS_PERMITIDOS:
            # Reabrir el issue si el usuario no tiene permisos
            reabrir_issue_graphql(issue_id)

            # Agregar un comentario en el issue indicando que el usuario no tiene permisos
            comentario = f"⚠️ **{closed_by}** intentó cerrar el issue, pero no tiene permisos para hacerlo. El issue ha sido reabierto."
            agregar_comentario_issue(issue_id, comentario)

            # Enviar mensaje a Discord indicando que no tiene permisos
            message = f"⚠️ **{closed_by}** intentó cerrar el issue '{issue_title}' en **{repo_name}**, pero no tiene permisos. El issue ha sido reabierto.\n🔗 [Ver issue]({issue_url})"
            send_to_discord(message, data)

    else:
        # Si el issue no fue cerrado, solo enviar un mensaje de evento normal
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

# Diccionario que mapea los ID de canales de Discord con los ID de discusiones de GitHub
channel_to_discussion = {
    1277350203330007108: 'D_kwDOMoKp284AbRww',  # chat general
    1278505988579659806: 'D_kwDOMoKp284AbRwv',  # chat blue-team-trolley-metrics
    1278506143089688586: 'D_kwDOMoKp284AbRwu'   # chat green-team-notifications
}

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