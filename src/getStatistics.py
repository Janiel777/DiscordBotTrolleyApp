import requests
from datetime import datetime

def get_repo_issues(GITHUB_API_TOKEN):
    # Datos del repositorio
    repo_owner = "uprm-inso4116-2024-2025-s1"
    repo_name = "semester-project-trolley-tracker-app"

    # URL para obtener los issues del repositorio
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"

    headers = {
        "Authorization": f"token {GITHUB_API_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Hacer la solicitud GET
    response = requests.get(url, headers=headers)

    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        return response.json()  # Devolver los issues en formato JSON
    else:
        return f"Error: {response.status_code}, {response.text}"



def get_repo(GITHUB_API_TOKEN):
    # Datos del repositorio
    repo_owner = "uprm-inso4116-2024-2025-s1"
    repo_name = "semester-project-trolley-tracker-app"

    # URL para obtener los issues del repositorio
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"

    headers = {
        "Authorization": f"token {GITHUB_API_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Hacer la solicitud GET
    response = requests.get(url, headers=headers)

    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        return response.json()  # Devolver los issues en formato JSON
    else:
        return f"Error: {response.status_code}, {response.text}"


def get_project_items_with_custom_fields(GITHUB_API_TOKEN):
    query = """
    query QueryProjectItemsForTeam(
      $owner: String!
      $team: String!
      $nextPage: String
    ) {
      organization(login: $owner) {
        projectsV2(
          query: $team
          first: 1
          orderBy: { field: TITLE, direction: ASC }
        ) {
          nodes {
            title
            items(first: 100, after: $nextPage) {
              pageInfo {
                endCursor
                hasNextPage
              }
              nodes {
                content {
                  ... on Issue {
                    url
                    number
                    title
                    author {
                        login
                    }
                    createdAt
                    closed
                    closedAt
                    milestone {
                      title
                    }
                    assignees(first: 20) {
                      nodes {
                        login
                      }
                    }
                  }
                }
                taskType: fieldValueByName(name: "Task Type") {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                  }
                }
                priority: fieldValueByName(name: "Priority") {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                  }
                }
                difficulty: fieldValueByName(name: "Difficulty") {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                  }
                }
                estimate: fieldValueByName(name: "Estimate") {
                  ... on ProjectV2ItemFieldNumberValue {
                    number
                  }
                }
                difficultyPoints: fieldValueByName(name: "Difficulty Points") {
                  ... on ProjectV2ItemFieldNumberValue {
                    number
                  }
                }
                priorityPoints: fieldValueByName(name: "Priority Points") {
                  ... on ProjectV2ItemFieldNumberValue {
                    number
                  }
                }
                iteration: fieldValueByName(name: "Iteration") {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {GITHUB_API_TOKEN}",
        "Content-Type": "application/json"
    }
    # Combinar la consulta y las variables en un solo diccionario
    data = {
        "query": query,
        "variables": {
            "owner": "uprm-inso4116-2024-2025-s1",
            "team": "Trolley Tracker App",
            "nextPage": None
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        return response.json()  # Devolver los detalles de los elementos del proyecto en formato JSON
    else:
        return f"Error: {response.status_code}, {response.text}"


def dk_penalty(milestone_start, milestone_end, issue_created):
    """
    Calcula la penalización de puntos (dk) basado en el retraso en la creación del issue.

    :param milestone_start: Fecha de inicio del milestone (datetime).
    :param milestone_end: Fecha de fin del milestone (datetime).
    :param issue_created: Fecha en que se creó el issue (datetime).
    :return: Penalización en puntos (float).
    """
    # Duración total del milestone en días
    duration = (milestone_end - milestone_start).days

    # Si el issue se creó después del final del milestone, considera que se creó el último día del milestone
    if issue_created > milestone_end:
        issue_created = milestone_end

    # Días de retraso en la creación del issue desde el inicio del milestone
    issue_lateness = max(0, (issue_created - milestone_start).days)

    # Base de decay, ajustada para reflejar un efecto de penalización progresiva
    decay_base = 1 + 1 / duration

    # Cálculo de la diferencia para normalizar el decay
    difference = pow(decay_base, 3 * duration) - pow(decay_base, 0)
    final_decrease = 0.7  # Porcentaje de penalización máximo

    # Cálculo de la penalización final (cuanto más tarde se crea el issue, mayor es la penalización)
    translate = 1 + final_decrease / difference
    penalty = max(0, translate - final_decrease * pow(decay_base, 3 * issue_lateness) / difference)

    return penalty


# Función para calcular el puntaje total con y sin dk
def calculate_total_points_with_dk(issues):
    total_points_without_dk = 0
    total_points_with_dk = 0

    # Iterar sobre todos los issues
    for issue in issues:
        estimate = issue['estimate']['number']
        created_at = datetime.strptime(issue['content']['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
        milestone = issue['content'].get('milestone', None)

        # Si el issue no tiene un milestone o si faltan fechas, ignorar el issue
        if not milestone or 'title' not in milestone:
            continue

        # Obtener las fechas de inicio y final del milestone
        milestone_title = milestone['title']

        # En este caso, obtenemos las fechas específicas de cada milestone (ajústalo según cómo las almacenes)
        if milestone_title == "Milestone #1":
            milestone_start = datetime(2024, 8, 29)
            milestone_end = datetime(2024, 9, 20)
        elif milestone_title == "Milestone #2":
            milestone_start = datetime(2024, 9, 21)
            milestone_end = datetime(2024, 10, 20)
        else:
            continue

        # Calcular puntaje sin aplicar dk
        total_points_without_dk += estimate

        # Calcular dk y aplicar al puntaje
        dk = dk_penalty(milestone_start, milestone_end, created_at)
        total_points_with_dk += estimate * dk

    # Calcular el promedio del dk
    dk_average = total_points_with_dk / total_points_without_dk if total_points_without_dk > 0 else 0

    return total_points_with_dk, total_points_without_dk, dk_average


# Llamada a la función get_project_items_with_custom_fields
def issuesDK(GITHUB_API_TOKEN):
    issues = get_project_items_with_custom_fields(GITHUB_API_TOKEN)

    # Calcular los puntos totales con y sin dk
    total_with_dk, total_without_dk, average_dk = calculate_total_points_with_dk(issues)

    # Imprimir los resultados
    print(f"Total con DK: {total_with_dk}")
    print(f"Total sin DK: {total_without_dk}")
    print(f"Promedio de DK: {average_dk}")

    return total_with_dk, total_without_dk, average_dk

