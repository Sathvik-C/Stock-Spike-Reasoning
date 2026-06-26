import time
print("Importing summarization service...")
start = time.time()
from app.services.summarization_service import get_summarization_service
print("Calling get_summarization_service...")
summarizer = get_summarization_service()
print("Done in", time.time() - start, "seconds")
