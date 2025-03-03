import requests
import os
import json
import time
from review import CodeReviewResponse, generate_review_response

system_prompt = """
Role: You are an expert developer whose sole responsibility is to review pull requests by analyzing only the changed code. 
The changed code is provided in a diff-like format, where lines prefixed with '-' indicate removals and lines with '+' indicate additions. 
Context lines are present for reference but must be ignored in your review.
Audience: Your feedback is aimed at developers responsible for merging code changes. 
The review should help them identify risks and potential issues before integration.
Knowledge/Information: You are provided with a list of filenames and partial file contents. 
You may not have full context of the entire codebase, and libraries or techniques you are unfamiliar with should only be commented on if you are certain of a problem.
Task/Goal: Your objective is to evaluate the changed code and assign a risk score from 1 to 5, where 1 represents minimal risk and 5 indicates changes that are likely to break functionality or compromise safety. 
Your review must focus solely on the negative aspects of the changes, highlighting potential bugs, readability issues, performance problems, and any breaches of SOLID principles. 
Immediately flag any plain-text API keys or secrets as the highest risk.
Policy/Rule: 
1. Only review lines that have been changed (prefixed with '+' or '-'). Ignore context lines.
2. Do not include filenames or the risk score in your detailed feedback.
3. If multiple similar issues are present, only address the most critical one.
4. Provide brief code snippet examples in your feedback using the same programming language as the file under review. For instance, if suggesting a change, use escaped code blocks like: \\`\\`\\`typescript\\n// improved code here\\n\\`\\`\\`.\\n
5. Do not offer praise or compliments; focus strictly on areas of improvement.
Style: Ensure your feedback is concise, clear, and professional. Use markdown formatting with ordered lists for multiple suggestions. Escape all special characters properly: code blocks as \\`\\`\\`typescript\\\\ncode here\\\\n\\`\\`\\`, regular backticks as \\`, newlines as \\n, and double quotes as
Constraints: Do not comment on breaking functions into smaller parts unless it poses a major issue. Avoid critiquing unfamiliar libraries or techniques unless you are certain they cause a problem. 
Your output must be valid JSON with all special characters escaped as required.
"""

user_prompt = """
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
Well-known terms can be left untranslated:
- Mocking, API, Database, Cache, Error handling,
- Unit test, Integration test, System test, End-to-end test, etc.
You must not translate the code snippets or filenames in the review and should keep them in English. 
You must not add or remove any information from the review.
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
            'format': CodeReviewResponse.model_json_schema()
        }

        review_response = requests.post(f'{api_url}/api/generate', json=review_request)
        review_response.raise_for_status()
        review_json = review_response.json()

        # Parse structured response
        review_content = review_json['response'] if 'response' in review_json else review_json
        review_data = CodeReviewResponse.model_validate_json(review_content)

        # Format the review into Markdown
        formatted_review = generate_review_response(review_data.reviews)

        return formatted_review
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
