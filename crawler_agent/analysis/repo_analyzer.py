class Analyzer:

    def build_repo_summary(self, repo_name, readme, commits):

        commit_text = "\n".join(commits)

        return f"""
Repository: {repo_name}

README:
{readme[:2000]}

Recent Commits:
{commit_text}
"""

    def build_article_summary(self, article):

        return f"""
Article URL:
{article['url']}

Content:
{article['text'][:3000]}
"""