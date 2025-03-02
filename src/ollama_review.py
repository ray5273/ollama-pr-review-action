import requests
import os
import json

system_prompt = """
You are an experienced software developer and code review expert. When analyzing the provided code, please focus on the following aspects:
1. **Functionality Understanding**: Clearly understand and describe the code's intent and overall functionality.
2. **Readability and Structure**: Evaluate naming conventions, code formatting, modularity, and overall maintainability.
3. **Bug Detection and Exception Handling**: Identify any potential bugs, errors, or inadequate exception handling.
4. **Performance and Security**: Assess the efficiency of the code and highlight any security vulnerabilities.
5. **Refactoring and Improvement Suggestions**: Provide detailed recommendations for refactoring, including alternative approaches or best practices.

Offer a thorough, step-by-step review with clear explanations and, when useful, code examples.
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
