import os
import requests
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from github import Github
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetching secrets from environment variables
GITLAB_USER_ID = os.getenv('GITLAB_USER_ID')
GITLAB_ACCESS_TOKEN = os.getenv('GITLAB_ACCESS_TOKEN')
GITHUB_REPO = 'remireci/gitlab_activity'
GITHUB_ACCESS_TOKEN = os.getenv('IMPORT_GITLAB_GITHUB_TOKEN')
GRAPH_IMAGE_PATH = 'remireci/gitlab_activity.png'

# Configuration
GITLAB_API_URL = 'https://gitlab.com/api/v4/'

def fetch_gitlab_activity():
    headers = {'PRIVATE-TOKEN': GITLAB_ACCESS_TOKEN}
    activity = []
    page = 1
    per_page = 100

    while True:
        params = {
            'per_page': per_page,
            'page': page,
            'after': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        }
        response = requests.get(f'{GITLAB_API_URL}users/{GITLAB_USER_ID}/events', headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        activity.extend(data)
        page += 1

    return activity

def generate_activity_heatmap(activity):
    # Initialize a dictionary to count events per day for the past year
    start_date = datetime.now() - timedelta(days=365)
    dates = {datetime.strftime(start_date + timedelta(days=i), '%Y-%m-%d'): 0 for i in range(366)}

    for event in activity:
        date_str = event['created_at'].split('T')[0]
        if date_str in dates:
            dates[date_str] += 1

    date_keys = sorted(dates.keys())
    date_values = [dates[date] for date in date_keys]

    # Create a 2D array for the heatmap (53 weeks x 7 days)
    heatmap_data = [[0 for _ in range(7)] for _ in range(53)]

    for idx, date in enumerate(date_keys):
        year, week, day = datetime.strptime(date, '%Y-%m-%d').isocalendar()
        if week == 53:
            week = 0
        heatmap_data[week][day - 1] = dates[date]

    # Generate the heatmap
    plt.figure(figsize=(15, 5))
    plt.imshow(heatmap_data, cmap='YlGn', aspect='auto', norm=mcolors.PowerNorm(0.5))
    plt.colorbar(label='Activity Count')
    plt.title('GitLab Activity Heatmap')
    plt.xlabel('Day of Week')
    plt.ylabel('Week of Year')
    plt.xticks(ticks=range(7), labels=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
    plt.yticks(ticks=range(0, 53, 4), labels=[f'Week {i}' for i in range(0, 53, 4)])
    plt.tight_layout()
    plt.savefig(GRAPH_IMAGE_PATH)
    plt.close()  # Close the plot to avoid memory issues

def upload_image_to_github():
    with open(GRAPH_IMAGE_PATH, 'rb') as image_file:
        image_content = image_file.read()
    image_base64 = base64.b64encode(image_content).decode()

    g = Github(GITHUB_ACCESS_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    
    try:
        contents = repo.get_contents(GRAPH_IMAGE_PATH)
        repo.update_file(contents.path, "Update GitLab activity graph", image_base64, contents.sha, branch="main")
    except Exception as e:
        print(f"Creating new file: {e}")
        repo.create_file(GRAPH_IMAGE_PATH, "Add GitLab activity graph", image_base64, branch="main")

# def update_readme_with_image():
#     print("Starting update_readme_with_image function")
#     g = Github(GITHUB_ACCESS_TOKEN)
#     repo = g.get_repo(GITHUB_REPO)
#     print(f"Fetched repository: {GITHUB_REPO}")

#     try:
#         readme = repo.get_readme()
#         print("Fetched README file")
#     except Exception as e:
#         print(f"Error fetching README: {e}")
#         return

#     # Read the base64 encoded image content
#     try:
#         with open(GRAPH_IMAGE_PATH, 'rb') as image_file:
#             image_content = image_file.read()
#         image_base64 = base64.b64encode(image_content).decode()
#         print("Encoded image to base64")
#     except Exception as e:
#         print(f"Error reading or encoding image: {e}")
#         return

#     # Create the Markdown image syntax with the embedded image content
#     image_markdown = f"![GitLab Activity](data:image/png;base64,{image_base64})"
#     print("Created markdown for image")

#     # Update the README file in the repository
#     try:
#         repo.update_file(readme.path, "Update README with GitLab activity graph", image_markdown, readme.sha, branch="main")
#         print("Updated README file")
#     except Exception as e:
#         print(f"Error updating README: {e}")

if __name__ == "__main__":
    try:
        activity = fetch_gitlab_activity()
        generate_activity_heatmap(activity)
        upload_image_to_github()
        # update_readme_with_image()
    except Exception as e:
        print(f"An error occurred: {e}")
