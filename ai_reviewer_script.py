import subprocess
from google import genai
import os

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
        model='gemini-2.5-flash',
        contents=f"Review this git diff for security issues and logic bugs: {code_diff}"
    )
    return response.text

if __name__ == "__main__":
    changes = get_git_dif()
    print(call_genai(changes))

