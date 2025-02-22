import requests
import sys

def request_code_review(api_url, github_token, repo, pr_number):
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Get the PR diff
    pr_diff_url = f'https://api.github.com/repos/{repo}/pulls/{pr_number}'
    response = requests.get(pr_diff_url, headers=headers)
    response.raise_for_status()
    pr_diff = response.json()['diff_url']
    
    # Request code review from Ollama
    review_response = requests.post(api_url, json={'diff_url': pr_diff})
    review_response.raise_for_status()
    review = review_response.json()
    
    return review

if __name__ == "__main__":
    api_url = sys.argv[1]
    github_token = sys.argv[2]
    repo = sys.argv[3]
    pr_number = sys.argv[4]
    
    review = request_code_review(api_url, github_token, repo, pr_number)
    print(review)
