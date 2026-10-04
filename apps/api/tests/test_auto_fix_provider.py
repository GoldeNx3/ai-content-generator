import json
from app.services.llm.auto_fix import OpenAIAutoFix,FIX_SYSTEM_PROMPT
from app.services.llm.base import LLMUsage
from app.schemas.auto_fix import FixOutput
from tests.test_auto_fix_units import payload,output

async def test_one_structured_call_without_tools():
    calls=[]
    class Client:
        async def parse(self,model,system,user,schema,timeout=None):
            calls.append((model,system,json.loads(user),schema,timeout))
            return output(),LLMUsage('configured-model',10,20)
    result=await OpenAIAutoFix(Client(),'configured-model',90).fix(payload())
    assert len(calls)==1 and calls[0][0]=='configured-model' and calls[0][3] is FixOutput and calls[0][4]==90
    assert result.usage.input_tokens==10
    for rule in ('Nie dodawaj nowych faktów','Nie wykonuj researchu','Nie korzystaj z własnej wiedzy','skipped','Nie wymyślaj ID','Nie zmieniaj poprawnych fragmentów'):
        assert rule in FIX_SYSTEM_PROMPT
