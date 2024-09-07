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


def filter_issues_by_milestone(issues, milestone_title):
    """
    Filtra los issues que pertenecen a un milestone específico.

    :param issues: Lista de issues (devueltos por get_all_issues o get_open_issues)
    :param milestone_title: El título del milestone a filtrar
    :return: Lista de issues que pertenecen al milestone especificado
    """
    filtered_issues = []

    for issue in issues:
        milestone = issue['content'].get('milestone')
        if milestone and milestone.get('title') == milestone_title:
            filtered_issues.append(issue)

    return filtered_issues



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