"""Safe errors: never retain response bodies or credentials in public messages."""
class WordPressError(Exception):
    def __init__(self, code, retryable=False, retry_after=None, details=None):
        self.code, self.retryable, self.retry_after, self.details = code, retryable, retry_after, details
        super().__init__(code)
