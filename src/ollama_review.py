import requests
import os
import json
import time

system_prompt = """
You are an expert developer, your task is to review a set of pull requests.
You are given a list of filenames and their partial contents, but note that you might not have the full context of the code.
Only review lines of code which have been changed (added or removed) in the pull request. The code looks similar to the output of a git diff command. 
Lines which have been removed are prefixed with a minus (-) and lines which have been added are prefixed with a plus (+). 
Other lines are added to provide context but should be ignored in the review.
Do not praise or complement anything. Only focus on the negative aspects of the code.
Begin your review by evaluating the changed code using a risk score similar to a LOGAF score but measured from 1 to 5, where 1 is the lowest risk to the code base if the code is merged and 5 is the highest risk which would likely break something or be unsafe.
In your feedback, focus on highlighting potential bugs, improving readability if it is a problem, making code cleaner, and maximising the performance of the programming language. Flag any API keys or secrets present in the code in plain text immediately as highest risk. Rate the changes based on SOLID principles if applicable.
Do not comment on breaking functions down into smaller, more manageable functions unless it is a huge problem. Also be aware that there will be libraries and techniques used which you are not familiar with, so do not comment on those unless you are confident that there is a problem.
Use markdown formatting for the feedback details. Also do not include the filename or risk level in the feedback details.
Ensure the feedback details are brief, concise, accurate. If there are multiple similar issues, only comment on the most critical.
Include brief example code snippets in the feedback details for your suggested changes when you're confident your suggestions are improvements. Use the same programming language as the file under review.
If there are multiple improvements you suggest in the feedback details, use an ordered list to indicate the priority of the changes.
Respond in valid json making sure that all special characters are escaped properly:
- Code blocks should be escaped like this: \`\`\`typescript\\ncode here\\n\`\`\`
- Regular backticks should be escaped as \`
- Newlines should be escaped as \\n
- Double quotes should be escaped as \\
"""

user_prompt = """
Please add logger.info() and logger.debug() to the code.
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

def manage_ollama_model(api_url, model_name, action):
    """
    Manage Ollama model (pull, load, unload)
    """
    endpoint = f'{api_url}/api/generate'
    
    if action == 'load':
        request_data = {'model': model_name}
    elif action == 'unload':
        request_data = {'model': model_name, 'keep_alive': 0}
    else:  # pull
        endpoint = f'{api_url}/api/pull'
        request_data = {'name': model_name}

    print(f"Attempting to {action} model {model_name}...")
    try:
        response = requests.post(endpoint, json=request_data, stream=(action == 'pull'))
        response.raise_for_status()
        
        if action == 'pull':
            for line in response.iter_lines():
                if line:
                    status = json.loads(line)
                    if 'status' in status:
                        print(f"Model {model_name}: {status['status']}")
                    if 'error' in status:
                        raise Exception(f"Error pulling model: {status['error']}")
        else:
            result = response.json()
            if result.get('error'):
                raise Exception(f"Error during model {action}: {result['error']}")
        
        print(f"Successfully {action}ed model {model_name}")
        return True
    except Exception as e:
        print(f"Error during model {action}: {str(e)}")
        return False

def prepare_model(api_url, model_name):
    """
    Prepare model for use (pull and load)
    """
    if not manage_ollama_model(api_url, model_name, 'pull'):
        raise Exception(f"Failed to pull model: {model_name}")
    time.sleep(2)
    
    if not manage_ollama_model(api_url, model_name, 'load'):
        raise Exception(f"Failed to load model: {model_name}")
    time.sleep(3)

def cleanup_model(api_url, model_name):
    """
    Cleanup model after use (unload)
    """
    manage_ollama_model(api_url, model_name, 'unload')
    time.sleep(1)

def translate_review(api_url, review_text, target_language, translation_model):
    """
    Translate the review text using specified model
    """
    try:
        # Prepare translation model
        prepare_model(api_url, translation_model)
        
        translation_prompt = f"""
Please translate the following code review into {target_language}. 
Maintain the technical terminology in English where appropriate.

Review to translate:
{review_text}
"""
        print("Translation Prompt given to Ollama:", translation_prompt)
        translation_request = {
            'model': translation_model,
            'prompt': translation_prompt,
            'stream': False,
        }
    
        translation_response = requests.post(f'{api_url}/api/generate', json=translation_request)
        translation_response.raise_for_status()
        translation = translation_response.json()

        print("Translation Response:", translation)

        return translation['response'] if 'response' in translation else translation
    finally:
        # Cleanup translation model
        cleanup_model(api_url, translation_model)

def request_code_review(api_url, github_token, owner, repo, pr_number, model, custom_prompt=None):
    try:
        # Prepare review model
        prepare_model(api_url, model)
        
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        # Complete system prompt with response language
        complete_system_prompt = f'{system_prompt}.'
        print("Complete System Prompt given to Ollama:", complete_system_prompt)
        # Get the PR files
        pr_url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files'
        response = requests.get(pr_url, headers=headers)
        response.raise_for_status()
        files = response.json()
        
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
        complete_user_prompt = user_prompt + (custom_prompt or '') + "\n\nChanges:\n" + changes_str
        print("Complete User Prompt given to Ollama:", complete_user_prompt)

        # Request code review from Ollama
        review_request = {
            'model': model,  # You might want to make this configurable
            'system': complete_system_prompt,
            'prompt': complete_user_prompt,
            'stream': False,
        }
    
        review_response = requests.post(f'{api_url}/api/generate', json=review_request)
        review_response.raise_for_status()
        review = review_response.json()
        print("Review Response:", review)
        
        return review['response'] if 'response' in review else review
    finally:
        # Cleanup review model
        cleanup_model(api_url, model)

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
    translation_model = os.getenv('TRANSLATION_MODEL', 'exaone3.5:7.8b')  # Add translation model

    print(f"API URL: {api_url}")
    print(f"GitHub Token: {github_token}")
    print(f"Owner: {owner}")
    print(f"Repo: {repo}")
    print(f"PR Number: {pr_number}")
    print(f"Custom Prompt: {custom_prompt}")
    print(f"Response Language: {response_language}")
    print(f"Model: {model}")
    print(f"Translation Model: {translation_model}")
    
    try:
        # Get review from Ollama
        review = request_code_review(api_url, github_token, owner, repo, pr_number, model, custom_prompt)

        print(f"Review generated: {review}")

        # Translate if needed
        if response_language.lower() != "english":
            print(f"Translating review to {response_language} using {translation_model}...")
            review = translate_review(api_url, review, response_language, translation_model)
            print("Translation completed.")
        
        # Post review back to GitHub PR
        post_review_to_github(github_token, owner, repo, pr_number, review)
        
    except Exception as e:
        print(f"Error during review process: {str(e)}")
        raise e
