from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="reviewlens - backend")

class Review(BaseModel):
    id: int
    title: str
    content: str

# in-memory sample store
_reviews: List[Review] = [
    Review(id=1, title="Example review", content="This is a sample review."),
]

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/reviews", response_model=List[Review])
async def list_reviews():
    return _reviews

@app.post("/reviews", response_model=Review)
async def create_review(r: Review):
    _reviews.append(r)
    return r
