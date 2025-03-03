from pydantic import BaseModel
from typing import List, Optional


class FeedbackItem(BaseModel):
    title: str
    details: str


class FileReview(BaseModel):
    filename: str
    risk_score: int  # 1-5 scale
    feedback: List[FeedbackItem]
    commit_id: str


class CodeReviewResponse(BaseModel):
    reviews: List[FileReview]


def generate_review_response(file_reviews):
    """
    Generate the complete code review response combining all file reviews.

    :param file_reviews: List of FileReview objects
    :return: Formatted full review as a string
    """
    response = []

    for review in file_reviews:
        response.append(f"## {review.filename}")
        response.append(f"**Risk Score: {review.risk_score}/5**")
        response.append("")

        for feedback in review.feedback:
            response.append(f"### {feedback.title}")
            response.append(feedback.details)
            response.append("")

    return "\n".join(response)