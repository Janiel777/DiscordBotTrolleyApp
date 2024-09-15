from environment_variables import GITHUB_TOKEN, MONGO_URI
import asyncio
from INSOAPIQuery.generateTeamMetrics import getTeamMetricsForMilestone
from INSOAPIQuery.getTeamMembers import get_team_members
import logging
from io import StringIO
from datetime import datetime, timedelta
import pymongo
import re
import pytz  # Para manejo de zona horaria
import discord
from discord.ext import commands
from dateutil.parser import isoparse


client = pymongo.MongoClient(MONGO_URI)
db = client['trolleyAppDB']
collection = db['documents']

ORG_NAME = 'uprm-inso4116-2024-2025-s1'  # Propietario del repositorio
REPO_NAME = 'semester-project-trolley-tracker-app'  # Nombre del repositorio

from getStatistics import get_repo, get_project_items_with_custom_fields, get_all_issues, \
    get_open_issues, filter_issues_by_milestone, issues_total_points_without_dk, issues_total_points_with_dk, \
    get_closed_issues, get_closed_issues_by_milestone, get_milestone_perfect_total_points_without_dk, \
    get_milestone_perfect_total_points_with_dk, get_milestone_closed_total_points_with_dk, \
    get_milestone_average_with_dk, get_milestone_closed_average_with_dk, calculate_individual_grades, \
    group_issues_by_assignee, find_unassigned_members

bot = commands.Bot(command_prefix="!")


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


def send_to_discord(message, data=None):
    channel = bot.get_channel(1278770255711309906)  # Reemplaza con el ID de tu canal
    bot.loop.create_task(channel.send(message))

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

    # Crear un archivo de texto con el contenido del mensaje
    with StringIO() as output_file:
        output_file.write(grade_message)
        output_file.seek(0)

        # Enviar el archivo como adjunto en Discord
        await ctx.send("Aquí está el resumen de las notas individuales en el milestone:",
                       file=discord.File(fp=output_file, filename="resumen_milestone.txt"))



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


# Define el comando para obtener métricas del equipo
@bot.command(name='team_metrics')
async def team_metrics(ctx, milestone: str, opentasks: bool = False):
    # Parámetros de la organización y el equipo
    org = "uprm-inso4116-2024-2025-s1"
    team = "Trolley Tracker App"

    # Llama a la función para obtener los miembros del equipo (incluyendo managers)
    members = get_team_members(org, team)

    # Define manualmente los gerentes (que son parte de los miembros)
    managers = ["gabrielpadilla7", "Yahid1"]

    # Configuración del milestone
    startDate = datetime(2024, 8, 29)
    endDate = datetime(2024, 9, 20)
    sprints = 1
    minTasksPerSprint = 0
    useDecay = True
    milestoneGrade = 100.0
    shouldCountOpenIssues = opentasks

    # Crear un logger para registrar advertencias y errores
    logger = logging.getLogger("discord_bot")
    logging.basicConfig(level=logging.INFO)

    # Llama a la función getTeamMetricsForMilestone
    metrics = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,  # Todos los miembros
        managers=managers,  # Los managers definidos manualmente
        startDate=startDate,
        endDate=endDate,
        sprints=sprints,
        minTasksPerSprint=minTasksPerSprint,
        useDecay=useDecay,
        milestoneGrade=milestoneGrade,
        shouldCountOpenIssues=shouldCountOpenIssues,
        logger=logger
    )

    # Obteniendo los issues filtrados por milestone y asignado
    all_issues = get_all_issues(GITHUB_API_TOKEN=GITHUB_TOKEN)
    milestone_issues = filter_issues_by_milestone(all_issues, milestone)

    # Filtrar issues según el valor de shouldCountOpenIssues
    if not shouldCountOpenIssues:
        # Filtramos los issues que están cerrados, si no queremos contar los abiertos
        milestone_issues = [issue for issue in milestone_issues if issue.get('content', {}).get('closed', False)]

    # Agrupar los issues por asignado
    assignee_issues = group_issues_by_assignee(milestone_issues)

    # Iteramos sobre los desarrolladores y mostramos sus issues cerrados correctamente
    response_message = f"Total Points Closed: {metrics.totalPointsClosed}\n"
    for dev, data in metrics.devMetrics.items():
        # Obtener los issues de este desarrollador
        dev_issues = assignee_issues.get(dev, [])
        num_issues = len(dev_issues)
        issue_points = [issue.get('estimate', {}).get('number', 0) for issue in dev_issues]
        total_issue_points = sum(issue_points)

        # Crear la lista de fechas de creación de los issues
        issue_dates = [issue.get('content', {}).get('createdAt', 'Fecha no disponible') for issue in dev_issues]

        # Convertir las fechas de ISO8601 a un formato más legible
        issue_dates_formatted = [isoparse(date).strftime('%Y-%m-%d') if date != 'Fecha no disponible' else date
                                 for date in issue_dates]

        # Crear mensaje para cada desarrollador
        response_message += (
            f"Developer {dev} - Expected Grade: {data.expectedGrade:.2f}\n"
            f"  - Issues asignados: {num_issues}\n"
            f"  - Puntos por issue: {issue_points}\n"
            f"  - Puntos totales: {total_issue_points:.2f}\n"
            f"  - Fechas de creación de los issues: {issue_dates_formatted}\n\n"
        )
    # Crear un archivo de texto con el contenido del mensaje
    with StringIO() as output_file:
        output_file.write(response_message)
        output_file.seek(0)

        # Enviar el archivo como adjunto en Discord
        await ctx.send("Aquí está el resumen de las notas individuales en el milestone:",
                       file=discord.File(fp=output_file, filename="resumen_milestone.txt"))
    # await ctx.send(response_message)


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


