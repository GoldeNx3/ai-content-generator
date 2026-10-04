# Rola pliku: Jawny wybór zapisu domenowego.
# W workerze execution kontroluje dzierżawę i zapis wyniku + statusu razem.
# Zwykłe krótkie operacje i testy serwisów nie mają zadania w kolejce.

async def save(session, execution=None, result=None, checkpoint=None, successor=None):
    if execution is None:
        if successor is not None: await successor()
        await session.commit()
    else:
        await execution.commit(session, result=result, checkpoint=checkpoint, successor=successor)


async def stage(execution, name):
    if execution is not None:
        await execution.stage(name)
