import subprocess
from google import genai
from google.genai import errors
import os
import requests
import time

def get_git_dif():
    try:
        subprocess.run(['git', 'fetch', '--unshallow'], capture_output=True)

        diff = subprocess.check_output(['git', 'diff', 'HEAD~1', 'HEAD']).decode('utf-8')

        return diff

    except Exception as e:
        
        print(f"Fallback mode active: {e}")
        return subprocess.check_output(['git', 'show', 'HEAD']).decode('utf-8')
        

client = genai.Client(api_key=os.getenv('API_KEY'))

def call_genai(code_diff):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"Review this git diff for security issues and logic bugs: {code_diff}"
            )
            return response.text
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                print(f"Server busy (503). Retrying in {2**attempt}s...")
                time.sleep(2**attempt) # Exponential backoff (1s, 2s, 4s)
                continue
            return f"AI Analysis failed after {max_retries} attempts: {e}"

def post_to_github(review_text):
    repo = "krishlad24/Auto_Audit_Ai"
    sha = os.getenv('COMMIT_SHA')
    token = os.getenv('GITHUB_TOKEN')
    url = f"https://api.github.com/repos/{repo}/commits/{sha}/comments"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    collapsible_body = (
        "____AI code review____\n\n"
        "<details>\n"
        "<summary><b>Click here to see the full detailed analysis</b></summary>\n\n"
        f"{review_text}\n\n"
        "</details>"
    )


    data = {"body": collapsible_body}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        print("Successfully posted comment to GitHub!")
    else:
        print(f"Failed to post comment: Status: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    changes = get_git_dif()
    review = call_genai(changes)
    post_to_github(review)

