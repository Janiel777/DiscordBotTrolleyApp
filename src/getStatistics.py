import requests


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



def get_project_items_with_details(GITHUB_API_TOKEN):
    # Definir la query GraphQL para obtener los elementos de un proyecto específico con detalles adicionales
    query = """
    {
      organization(login: "uprm-inso4116-2024-2025-s1") {
        projectV2(number: 3) {
          title
          items(first: 10) {
            nodes {
              content {
                ... on Issue {
                  title
                  url
                  state
                  assignees(first: 5) {
                    nodes {
                      login
                    }
                  }
                  fields(first: 10) {
                    nodes {
                      ... on ProjectV2ItemFieldSingleSelectValue {
                        name
                        option {
                          name
                        }
                      }
                      ... on ProjectV2ItemFieldNumberValue {
                        name
                        number
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    # Hacer la solicitud POST a la API de GitHub GraphQL
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {GITHUB_API_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json={"query": query}, headers=headers)

    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        return response.json()  # Devolver los detalles de los elementos del proyecto en formato JSON
    else:
        return f"Error: {response.status_code}, {response.text}"