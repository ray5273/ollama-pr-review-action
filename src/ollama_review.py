import requests
import os
import json

system_prompt = """
You are an expert Golang developer, your task is to review a set of pull requests.
You are given a list of filenames and their partial contents, but note that you might not have the full context of the code.

Only review lines of code which have been changed (added or removed) in the pull request. The code looks similar to the output of a git diff command. Lines which have been removed are prefixed with a minus (-) and lines which have been added are prefixed with a plus (+). Other lines are added to provide context but should be ignored in the review.

Do not praise or complement anything. Only focus on the negative aspects of the code.

Begin your review by evaluating the changed code using a risk score similar to a LOGAF score but measured from 1 to 5, where 1 is the lowest risk to the code base if the code is merged and 5 is the highest risk which would likely break something or be unsafe.

In your feedback, focus on highlighting potential bugs, improving readability if it is a problem, making code cleaner, and maximising the performance of the programming language. Flag any API keys or secrets present in the code in plain text immediately as highest risk. Rate the changes based on SOLID principles if applicable.

Do not comment on breaking functions down into smaller, more manageable functions unless it is a huge problem. Also be aware that there will be libraries and techniques used which you are not familiar with, so do not comment on those unless you are confident that there is a problem.

Use markdown formatting for the feedback details. Also do not include the filename or risk level in the feedback details.

Ensure the feedback details are brief, concise, accurate, and in {ReviewLanguage}. If there are multiple similar issues, only comment on the most critical.

Include brief example code snippets in the feedback details for your suggested changes when you're confident your suggestions are improvements. Use the same programming language as the file under review.
If there are multiple improvements you suggest in the feedback details, use an ordered list to indicate the priority of the changes.

Respond in valid json making sure that all special characters are escaped properly:
- Code blocks should be escaped like this: \`\`\`typescript\\ncode here\\n\`\`\`
- Regular backticks should be escaped as \`
- Newlines should be escaped as \\n
- Double quotes should be escaped as \\
"""

user_prompt = """
Focus on functionality, readability, potential bugs, performance, and security. Also, include any suggestions for refactoring or improvements.

"""

def post_review_to_github(github_token, owner, repo, pr_number, review_body):
    """
    Post a review comment to a GitHub PR.
    :param github_token: GitHub token for authentication
    :param repo: repo name
    :param pr_number: PR number
    :param review_body: review body text
    :return:
    """
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    review_url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews'
    review_data = {
        'body': review_body,
        'event': 'COMMENT'
    }
    
    response = requests.post(review_url, headers=headers, json=review_data)
    response.raise_for_status()
    return response.json()

def request_code_review(api_url, github_token, owner, repo, pr_number, model, custom_prompt=None, response_language="english"):
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # Complete system prompt with response language
    complete_system_prompt = f'{system_prompt}\nYou must provide your review in {response_language}.'
    print("Complete System Prompt given to Ollama:", complete_system_prompt)
    # Get the PR files
    pr_url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files'
    response = requests.get(pr_url, headers=headers)
    response.raise_for_status()
    files = response.json()

    print("Number of files in PR:", len(files))
    
    # Collect all changed code
    changes = []
    for file in files:
        changes.append({
            'filename': file['filename'],
            'patch': file.get('patch', ''),
            'status': file['status']
        })

    # Convert changes to a JSON-formatted string (using indent for readability)
    changes_str = json.dumps(changes, indent=2, ensure_ascii=False)

    # Create complete prompt using the global user_prompt
    complete_user_prompt = user_prompt + (custom_prompt or '') + f"\nYou must provide your review in {response_language} \nChanges:\n" + changes_str
    print("Complete User Prompt given to Ollama:", complete_user_prompt)

    # Request code review from Ollama
    review_request = {
        'model': model,  # You might want to make this configurable
        'system': complete_system_prompt,
        'prompt': complete_user_prompt,
        'stream': False,
        'keep_alive': '0m'
    }
    
    review_response = requests.post(f'{api_url}/api/generate', json=review_request)
    review_response.raise_for_status()
    review = review_response.json()
    
    return review['response'] if 'response' in review else review

if __name__ == "__main__":
    # Get input arguments from environment variables
    api_url = os.getenv('OLLAMA_API_URL')
    github_token = os.getenv('MY_GITHUB_TOKEN')
    owner = os.getenv('OWNER')
    repo = os.getenv('REPO')
    pr_number = os.getenv('PR_NUMBER')
    custom_prompt = os.getenv('CUSTOM_PROMPT')
    response_language = os.getenv('RESPONSE_LANGUAGE')
    model = os.getenv('MODEL')

    print(f"API URL: {api_url}")
    print(f"GitHub Token: {github_token}")
    print(f"Owner: {owner}")
    print(f"Repo: {repo}")
    print(f"PR Number: {pr_number}")
    print(f"Custom Prompt: {custom_prompt}")
    print(f"Response Language: {response_language}")
    print(f"Model: {model}")

    # Get review from Ollama
    review = request_code_review(api_url, github_token, owner, repo, pr_number, model, custom_prompt, response_language)
    
    # Post review back to GitHub PR
    post_review_to_github(github_token, owner, repo, pr_number, review)
