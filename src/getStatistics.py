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


# Función para calcular el puntaje total con y sin dk
def calculate_total_points_with_dk(issues):
    total_points_without_dk = 0
    total_points_with_dk = 0

    # Iterar sobre todos los issues
    for issue in issues:
        # Asegurarnos de que 'estimate' exista y sea un diccionario
        if 'estimate' in issue:
            estimate = issue['estimate']['number']
        else:
            # Si no hay estimado, continuamos al siguiente issue
            continue

        created_at = datetime.strptime(issue['content']['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
        milestone = issue['content'].get('milestone', None)

        # Verificar si tiene un milestone con un título
        if milestone and 'title' in milestone:
            milestone_title = milestone['title']

            # Obtener las fechas de inicio y fin del milestone basadas en su título
            if milestone_title == "Milestone #1":
                milestone_start = datetime(2024, 8, 29)
                milestone_end = datetime(2024, 9, 20)
            elif milestone_title == "Milestone #2":
                milestone_start = datetime(2024, 9, 21)
                milestone_end = datetime(2024, 10, 20)
            else:
                # Si el milestone no coincide con los que conocemos, saltamos este issue
                continue
        else:
            # Si no tiene un milestone válido, saltamos este issue
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
def perfect_milestone_grade(GITHUB_API_TOKEN):
    issues_data = get_project_items_with_custom_fields(GITHUB_API_TOKEN)
    # Extraer los issues desde el campo 'nodes'
    issues = issues_data['data']['organization']['projectsV2']['nodes'][0]['items']['nodes']

    # Calcular los puntos totales con y sin dk
    total_with_dk, total_without_dk, average_dk = calculate_total_points_with_dk(issues)

    # Imprimir los resultados
    print(f"Total con DK: {total_with_dk}")
    print(f"Total sin DK: {total_without_dk}")
    print(f"Promedio de DK: {average_dk}")

    return total_with_dk, total_without_dk, average_dk



def calculate_milestone_grade(issues):
    total_points_without_dk = 0
    total_points_with_dk = 0
    closed_issues_points_without_dk = 0
    closed_issues_points_with_dk = 0

    # Iterar sobre todos los issues
    for issue in issues:
        # Asegurarnos de que 'estimate' exista y sea un diccionario
        if 'estimate' in issue:
            estimate = issue['estimate']['number']
        else:
            # Si no hay estimado, continuamos al siguiente issue
            continue

        created_at = datetime.strptime(issue['content']['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
        closed = issue['content']['closed']  # Saber si el issue está cerrado
        milestone = issue['content'].get('milestone', None)

        # Verificar si tiene un milestone con un título
        if milestone and 'title' in milestone:
            milestone_title = milestone['title']

            # Obtener las fechas de inicio y fin del milestone basadas en su título
            if milestone_title == "Milestone #1":
                milestone_start = datetime(2024, 8, 29)
                milestone_end = datetime(2024, 9, 20)
            elif milestone_title == "Milestone #2":
                milestone_start = datetime(2024, 9, 21)
                milestone_end = datetime(2024, 10, 20)
            else:
                # Si el milestone no coincide con los que conocemos, saltamos este issue
                continue
        else:
            # Si no tiene un milestone válido, saltamos este issue
            continue

        # Calcular puntaje sin aplicar dk para todos los issues
        total_points_without_dk += estimate

        # Calcular dk y aplicar al puntaje
        dk = dk_penalty(milestone_start, milestone_end, created_at)
        total_points_with_dk += estimate * dk

        # Calcular puntaje solo para los issues cerrados
        if closed:
            closed_issues_points_without_dk += estimate
            closed_issues_points_with_dk += estimate * dk

    # Calcular la nota del milestone
    if closed_issues_points_without_dk > 0:
        milestone_grade = closed_issues_points_with_dk / closed_issues_points_without_dk
    else:
        milestone_grade = 0

    return milestone_grade, closed_issues_points_with_dk, total_points_without_dk

# Llamada a la función para calcular la nota del milestone
def milestone_grade(GITHUB_API_TOKEN):
    issues_data = get_project_items_with_custom_fields(GITHUB_API_TOKEN)
    issues = issues_data['data']['organization']['projectsV2']['nodes'][0]['items']['nodes']

    # Calcular la nota del milestone
    grade, closed_with_dk, total_without_dk = calculate_milestone_grade(issues)

    # Imprimir los resultados
    print(f"Nota del Milestone: {grade}")
    print(f"Puntos con DK (issues cerrados): {closed_with_dk}")
    print(f"Puntos sin DK (todos los issues): {total_without_dk}")

    return grade, closed_with_dk, total_without_dk

