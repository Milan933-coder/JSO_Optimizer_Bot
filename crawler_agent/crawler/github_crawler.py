import requests
import base64

GITHUB_API = "https://api.github.com"


class GithubCrawler:

    def __init__(self, username):
        self.username = username

    def get_repos(self):
        url = f"{GITHUB_API}/users/{self.username}/repos"
        return requests.get(url).json()

    def get_readme(self, repo):

        url = f"{GITHUB_API}/repos/{self.username}/{repo}/readme"
        r = requests.get(url)

        if r.status_code != 200:
            return ""

        content = r.json()["content"]
        return base64.b64decode(content).decode()

    def get_commits(self, repo, limit):

        url = f"{GITHUB_API}/repos/{self.username}/{repo}/commits?per_page={limit}"
        r = requests.get(url)

        commits = []
        for c in r.json():
            commits.append(c["commit"]["message"])

        return commits