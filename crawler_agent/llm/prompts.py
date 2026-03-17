from langchain.prompts import PromptTemplate


review_prompt = PromptTemplate(
    input_variables=["repo_info"],
    template="""
You are a senior software engineer reviewing a GitHub repository.

Give honest feedback.

Focus on:
- clarity of project
- README quality
- commit practices
- engineering maturity
- improvement suggestions

Repository info:

{repo_info}

Return in sections:

Project Understanding
Strengths
Weaknesses
Improvements
"""
)

article_review_prompt = PromptTemplate(
    input_variables=["article_text"],
    template="""
You are reviewing a technical article written by a developer.

Evaluate:

1. Technical depth
2. Clarity of explanation
3. Originality of ideas
4. Practical usefulness
5. Writing quality

Article Content:

{article_text}

Return response in this format:

Article Summary

Strengths

Weaknesses

Suggestions for Improvement

Author Skill Signal
(What this article indicates about the author's engineering maturity)
"""
)