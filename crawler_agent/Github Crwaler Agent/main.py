import yaml
from crawler.github_crawler import GithubCrawler
from crawler.article_crawler import ArticleCrawler
from analysis.repo_analyzer import Analyzer
from llm.prompts import review_prompt,article_review_prompt
from llm.llm_factory import get_llm

from langchain.chains import LLMChain


def load_config():

    with open("config.yaml") as f:
        return yaml.safe_load(f)


def main():

    config = load_config()

    username = config["github"]["username"]
    max_repos = config["github"]["max_repos"]
    commit_limit = config["github"]["commit_limit"]

    provider = config["llm"]["provider"]
    model = config["llm"]["model"]

    keys = config["api_keys"]

    llm = get_llm(provider, model, keys)

    chain = LLMChain(
        llm=llm,
        prompt=review_prompt
    )
    article_chain = LLMChain(
        llm=llm,
        prompt=article_review_prompt
    )
    crawler = GithubCrawler(username)
    analyzer = Analyzer()

    repos = crawler.get_repos()

    for repo in repos[:max_repos]:

        name = repo["name"]

        print("\n========================")
        print("Repo:", name)

        readme = crawler.get_readme(name)
        commits = crawler.get_commits(name, commit_limit)

        summary = analyzer.build_repo_summary(name, readme, commits)

        review = chain.invoke({"repo_info": summary})

        print(review["text"])
    articles_config = config.get("articles")

    if articles_config:

        crawler = ArticleCrawler(
            articles_config["links"],
            articles_config["max_articles"]
        )

        articles = crawler.fetch_articles()

        analyzer = Analyzer()

        for article in articles:

            summary = analyzer.build_article_summary(article)

            review = article_chain.invoke(
                {"article_text": summary}
            )

            print("\n===== ARTICLE REVIEW =====")
            print(review["text"])

if __name__ == "__main__":
    main()