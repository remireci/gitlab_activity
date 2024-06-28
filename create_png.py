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
GRAPH_IMAGE_PATH = 'gitlab_activity.png'
TIMESTAMP_PATH = 'last_activity_timestamp.txt'

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
            'after': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        response = requests.get(f'{GITLAB_API_URL}users/{GITLAB_USER_ID}/events', headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        activity.extend(data)
        page += 1

    return activity

def get_latest_activity_timestamp(activity):
    if not activity:
        return None
    latest_event = max(activity, key=lambda x: x['created_at'])
    return latest_event['created_at']

def save_latest_timestamp(timestamp):
    with open(TIMESTAMP_PATH, 'w') as file:
        file.write(timestamp)

def load_latest_timestamp():
    if not os.path.exists(TIMESTAMP_PATH):
        return None
    with open(TIMESTAMP_PATH, 'r') as file:
        return file.read().strip()

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

    g = Github(GITHUB_ACCESS_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    
    try:
        contents = repo.get_contents(GRAPH_IMAGE_PATH)
        repo.update_file(contents.path, "Update GitLab activity graph", image_content, contents.sha, branch="main")
    except Exception as e:
        print(f"Creating new file: {e}")
        repo.create_file(GRAPH_IMAGE_PATH, "Add GitLab activity graph", image_content, branch="main")


if __name__ == "__main__":
    try:
        latest_timestamp = load_latest_timestamp()
        activity = fetch_gitlab_activity()

        if not activity:
            print("No activity found.")
            exit(1)

        latest_activity_timestamp = get_latest_activity_timestamp(activity)
        print(f"Latest activity timestamp: {latest_activity_timestamp}")
        print(f"Previous latest timestamp: {latest_timestamp}")

        if latest_timestamp is None or latest_activity_timestamp > latest_timestamp:
            generate_activity_heatmap(activity)
            upload_image_to_github()
            save_latest_timestamp(latest_activity_timestamp)
            print("New activity detected and graph updated.")
            exit(0)  # Indicate success
        else:
            print("No new activity since the last update.")
            exit(1)  # Indicate no new activity
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)  # Indicate an error
