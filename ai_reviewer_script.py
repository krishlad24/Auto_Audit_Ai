import subprocess
from google import genai
import os

def get_git_dif():
    try:

        commit_count = int(subprocess.check_output(['git', 'rev-list', '--count', 'HEAD']).decode().strip())
        if commit_count > 1:
            print("Detected regular update. Getting diff...")
            return subprocess.check_output(['git', 'diff', 'HEAD~1', 'HEAD']).decode('utf-8')

        else:
            print("Detected first push. Fetching all files")
            return subprocess.check_output(['git', 'diff', '4b825dc642cb6eb9a060e54bf8d69288fbee4904', 'HEAD']).decode('utf-8')

    except Exception as e:
        return f"Error retrieving code: {str(e)}"


client = genai.Client(api_key=os.getenv('API_KEY'))

def call_genai(code_diff):
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=f"Review this git diff for security issues and logic bugs: {code_diff}"
    )
    return response.text

if __name__ == "__main__":
    changes = get_git_dif()
    print(call_genai(changes))

