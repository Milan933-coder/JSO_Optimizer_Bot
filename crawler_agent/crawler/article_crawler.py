from newspaper import Article


class ArticleCrawler:

    def __init__(self, links, max_articles=2):

        self.links = links
        self.max_articles = max_articles

    def fetch_articles(self):

        articles = []
        consecutive_failures = 0

        for link in self.links:

            if len(articles) >= self.max_articles:
                break

            try:

                article = Article(link)
                article.download()
                article.parse()

                text = article.text

                if len(text) < 200:
                    raise ValueError("Article too small")

                articles.append(
                    {
                        "url": link,
                        "text": text
                    }
                )

                consecutive_failures = 0

            except Exception:

                print(f"⚠️ Failed to fetch article: {link}")

                consecutive_failures += 1

                if consecutive_failures >= 2:
                    print("❌ Consecutive article failures. Stopping.")
                    break

        return articles