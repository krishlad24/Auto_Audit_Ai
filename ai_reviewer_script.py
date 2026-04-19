import subprocess
from google import genai
import os
import requests

def get_git_dif():
    try:
        subprocess.run(['git', 'fetch', '--unshallow'], capture_output=True)

        diff = subprocess.check_output(['git', 'diff', 'HEAD~1', 'HEAD']).decode('utf-8')

        return diff

    except Exception as e:
        # 3. Fallback: If it's literally the first commit in the repo history
        # just show the changes in the current commit
        print(f"Fallback mode active: {e}")
        return subprocess.check_output(['git', 'show', 'HEAD']).decode('utf-8')
        

client = genai.Client(api_key=os.getenv('API_KEY'))

def call_genai(code_diff):
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=f"Review this git diff for security issues and logic bugs: {code_diff}"
    )
    return response.text

def post_to_github(review_text):
    repo = "krishlad24/Auto_Audit_Ai"
    sha = os.getenv('COMMIT_SHA')
    token = os.getenv('GITHUB_TOKEN')
    url = f"https://api.github.com/repos/{repo}/commits/{sha}/comments"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    collapsible_body = f"""
    _____AI Code Review Summary_____
    <details>
    <summary>Click here to see the full detailed analysis</summary>

    {review_text}

    </details>
    """

    data = {"body": collapsible_body}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        print("Successfully posted comment to GitHub!")
    else:
        print(f"Failed to post comment: {response.text}")

if __name__ == "__main__":
    changes = get_git_dif()
    review = call_genai(changes)
    post_to_github(review)

