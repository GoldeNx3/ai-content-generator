# Rola pliku: Zadanie `embed`: wektory znaczenia tekstów (tytuł + opis tematu, tytuł + lead artykułu)
# do wykrywania tego samego tematu z różnych źródeł. Płatne wywołanie jest częścią kroku, który je zleca.

from pydantic import BaseModel, Field

from ai.context import TaskContext


class EmbedInput(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=16)

    def model_post_init(self, __context) -> None:
        for text in self.texts:
            if not text.strip() or len(text) > 20000:
                raise ValueError("Each text must be non-empty and at most 20000 characters")


async def run(data: dict, ctx: TaskContext) -> dict:
    payload = EmbedInput.model_validate(data)
    embedder = ctx.providers["embed"]
    result = await ctx.call("embedding", lambda: embedder.embed(payload.texts))
    return {"vectors": result.vectors, "model": result._usage["model"]}
