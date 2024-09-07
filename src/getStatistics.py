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


# Función para calcular la penalización (dk)
def dk_penalty(milestone_start, milestone_end, issue_created):
    duration = (milestone_end - milestone_start).days
    if issue_created > milestone_end:
        issue_created = milestone_end
    issue_lateness = max(0, (issue_created - milestone_start).days)
    decay_base = 1 + 1 / duration
    difference = pow(decay_base, 3 * duration) - pow(decay_base, 0)
    final_decrease = 0.7  # Penalty max 70%
    translate = 1 + final_decrease / difference
    penalty = max(0, translate - final_decrease * pow(decay_base, 3 * issue_lateness) / difference)
    return penalty


def get_all_issues(GITHUB_API_TOKEN):
    """
    Llama a get_project_items_with_custom_fields y devuelve todos los issues (cerrados o abiertos).

    :param GITHUB_API_TOKEN: El token de autenticación para la API de GitHub
    :return: Lista de todos los issues (cerrados y abiertos)
    """
    # Obtener los datos de los items del proyecto
    issues_data = get_project_items_with_custom_fields(GITHUB_API_TOKEN)

    # Extraer todos los issues desde el campo 'nodes'
    all_issues = issues_data['data']['organization']['projectsV2']['nodes'][0]['items']['nodes']

    return all_issues


def get_open_issues(GITHUB_API_TOKEN):
    """
    Llama a get_project_items_with_custom_fields y devuelve solo los issues abiertos.

    :param GITHUB_API_TOKEN: El token de autenticación para la API de GitHub
    :return: Lista de issues abiertos
    """
    # Obtener todos los issues del proyecto
    all_issues = get_all_issues(GITHUB_API_TOKEN)

    # Filtrar los issues abiertos (que no estén cerrados)
    open_issues = [issue for issue in all_issues if not issue['content'].get('closed', False)]

    return open_issues


def get_closed_issues(GITHUB_API_TOKEN):
    """
    Llama a get_project_items_with_custom_fields y devuelve solo los issues cerrados.

    :param GITHUB_API_TOKEN: El token de autenticación para la API de GitHub
    :return: Lista de issues cerrados
    """
    # Obtener todos los issues del proyecto
    all_issues = get_all_issues(GITHUB_API_TOKEN)

    # Filtrar los issues cerrados
    closed_issues = [issue for issue in all_issues if issue['content'].get('closed', False)]

    return closed_issues


def filter_issues_by_milestone(issues, milestone_name):
    """
    Filtra los issues por el título del milestone.

    :param issues: Lista de issues (abiertos o cerrados)
    :param milestone_name: Nombre del milestone a filtrar
    :return: Lista de issues que pertenecen al milestone especificado
    """
    return [issue for issue in issues if issue['content'].get('milestone') and
            issue['content']['milestone'].get('title') == milestone_name]


def get_closed_issues_by_milestone(GITHUB_API_TOKEN, milestone_title):
    """
    Filtra los issues cerrados que pertenecen a un milestone específico.

    :param GITHUB_API_TOKEN: El token de autenticación para la API de GitHub
    :param milestone_title: El título del milestone a filtrar
    :return: Lista de issues cerrados que pertenecen al milestone especificado
    """
    # Obtener todos los issues cerrados
    closed_issues = get_closed_issues(GITHUB_API_TOKEN)

    # Filtrar los issues cerrados por el milestone especificado
    filtered_closed_issues = filter_issues_by_milestone(closed_issues, milestone_title)

    return filtered_closed_issues



def issues_total_points_without_dk(issues):
    """
    Calcula la suma total de los puntos (Estimate) para una lista de issues sin aplicar DK.

    :param issues: Lista de issues (abiertos, cerrados o ambos)
    :return: La suma total de los puntos Estimate
    """
    total_points = 0

    # Iterar sobre los issues y sumar los puntos del campo 'Estimate'
    for issue in issues:
        estimate = issue.get('estimate', {}).get('number', 0)
        total_points += estimate

    return total_points


def issues_total_points_with_dk(issues, milestone_start, milestone_end):
    """
    Calcula la suma total de los puntos (Estimate) para una lista de issues aplicando DK individualmente.

    :param issues: Lista de issues (abiertos, cerrados o ambos)
    :param milestone_start: Fecha de inicio del milestone (datetime)
    :param milestone_end: Fecha de fin del milestone (datetime)
    :return: La suma total de los puntos Estimate con DK aplicado
    """
    total_points_with_dk = 0

    # Iterar sobre los issues y sumar los puntos del campo 'Estimate' aplicando DK
    for issue in issues:
        # Obtener el valor de Estimate
        estimate = issue.get('estimate', {}).get('number', 0)

        # Obtener la fecha de creación del issue
        created_at = issue['content'].get('createdAt')
        if created_at:
            created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")

            # Calcular DK para este issue
            dk = dk_penalty(milestone_start, milestone_end, created_at)

            # Sumar los puntos con DK aplicado
            total_points_with_dk += estimate * dk

    return total_points_with_dk


def get_milestone_perfect_total_points_without_dk(GITHUB_API_TOKEN, milestone_name):
    """
    Calcula el total de puntos sin DK para todos los issues (abiertos y cerrados) de un milestone específico.

    :param GITHUB_API_TOKEN: El token de autenticación para la API de GitHub.
    :param milestone_name: El nombre del milestone a filtrar.
    :return: Total de puntos sin DK para los issues del milestone.
    """
    # Obtener todos los issues (abiertos y cerrados)
    all_issues = get_all_issues(GITHUB_API_TOKEN)

    # Filtrar los issues por el milestone
    milestone_issues = filter_issues_by_milestone(all_issues, milestone_name)

    # Calcular los puntos sin DK
    total_points_without_dk = issues_total_points_without_dk(milestone_issues)

    return total_points_without_dk


def get_milestone_perfect_total_points_with_dk(GITHUB_API_TOKEN, milestone_name, milestone_start, milestone_end):
    """
    Calcula el total de puntos con DK para todos los issues (abiertos y cerrados) de un milestone específico.

    :param GITHUB_API_TOKEN: El token de autenticación para la API de GitHub.
    :param milestone_name: El nombre del milestone a filtrar.
    :param milestone_start: La fecha de inicio del milestone.
    :param milestone_end: La fecha de fin del milestone.
    :return: Total de puntos con DK para los issues del milestone.
    """
    # Obtener todos los issues (abiertos y cerrados)
    all_issues = get_all_issues(GITHUB_API_TOKEN)

    # Filtrar los issues por el milestone
    milestone_issues = filter_issues_by_milestone(all_issues, milestone_name)

    # Calcular los puntos con DK
    total_points_with_dk = issues_total_points_with_dk(milestone_issues, milestone_start, milestone_end)

    return total_points_with_dk


def filter_closed_issues_before_date(issues, target_date):
    """
    Filtra los issues cerrados que fueron cerrados antes de una fecha específica.

    :param issues: Lista de issues cerrados.
    :param target_date: Fecha límite para el filtro (datetime).
    :return: Lista de issues cerrados antes de la fecha especificada.
    """
    # Filtrar los issues que fueron cerrados antes de la fecha especificada
    filtered_issues = [issue for issue in issues if
                       datetime.strptime(issue['content']['closedAt'], "%Y-%m-%dT%H:%M:%SZ") < target_date]

    return filtered_issues


def get_milestone_closed_total_points_with_dk(GITHUB_API_TOKEN, milestone_name, milestone_end):
    """
    Calcula el total de puntos con DK para todos los issues cerrados antes de la fecha de fin del milestone.

    :param GITHUB_API_TOKEN: El token de autenticación para la API de GitHub.
    :param milestone_name: El nombre del milestone a filtrar.
    :param milestone_end: La fecha de fin del milestone.
    :return: Total de puntos con DK para los issues cerrados antes de la fecha límite del milestone.
    """
    # Obtener todos los issues cerrados
    closed_issues = get_closed_issues(GITHUB_API_TOKEN)

    # Filtrar los issues por el milestone
    milestone_issues = filter_issues_by_milestone(closed_issues, milestone_name)

    # Filtrar los issues cerrados que fueron cerrados antes de la fecha de fin del milestone
    closed_issues_before_end = filter_closed_issues_before_date(milestone_issues, milestone_end)

    # Calcular los puntos con DK para esos issues cerrados
    total_points_with_dk = issues_total_points_with_dk(closed_issues_before_end, milestone_end, milestone_end)

    return total_points_with_dk