from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


class ExampleResponse(BaseModel):
    title: str                           # Tiêu đề của ví dụ
    codeSnippet: Optional[str] = None    # Đoạn mã minh họa (nếu có)
    explanation: str                     # Giải thích chi tiết về ví dụ


class TheoryContentResponse(BaseModel):
    title: str                           # Tiêu đề của phần nội dung lý thuyết
    prerequisites: List[str]             # Các kiến thức cần có trước khi học phần này
    description: List[str]               # Mô tả chi tiết hoặc lý thuyết cần học
    examples: Optional[List[ExampleResponse]] = None  # Các ví dụ minh họa


class PracticalGuideResponse(BaseModel):
    title: str                           # Tiêu đề của bài hướng dẫn
    steps: List[str]                     # Các bước thực hành
    commonErrors: Optional[List[str]] = None  # Các lỗi thường gặp và cách khắc phục


class ReferenceResponse(BaseModel):
    title: str                           # Tiêu đề tài liệu tham khảo
    link: str                            # Liên kết đến tài liệu
    description: Optional[str] = None    # Mô tả ngắn về tài liệu


class ReviewQuestionResponse(BaseModel):
    id: UUID                             # ID của câu hỏi
    question: str                        # Nội dung câu hỏi
    answer: str                          # Đáp án
    maxscore: int                        # Điểm tối đa
    score: Optional[int] = None          # Điểm người dùng đạt được (nếu có)
    inputUser: Optional[str] = None      # Câu trả lời của người dùng (nếu có)


class SummaryAndReviewResponse(BaseModel):
    keyPoints: List[str]                 # Các điểm chính của tài liệu
    reviewQuestions: List[ReviewQuestionResponse]  # Các câu hỏi ôn tập
    quizLink: Optional[str] = None       # Liên kết đến bài kiểm tra (nếu có)


class DocumentResponse(BaseModel):
    id: UUID                             # ID của tài liệu
    name: str                            # Tên của tài liệu
    theoryContent: List[TheoryContentResponse]   # Nội dung lý thuyết
    practicalGuide: List[PracticalGuideResponse] # Hướng dẫn thực hành
    references: List[ReferenceResponse]          # Tài liệu tham khảo
    summaryAndReview: SummaryAndReviewResponse   # Tổng kết và câu hỏi ôn tập
