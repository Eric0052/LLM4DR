from AspectIdentifier import AspectIdentifier
from AspectAnalyst import AspectAnalyst
from AspectReviewer import AspectReviewer
from metagpt.context import Context
from metagpt.environment import Environment
from metagpt.schema import Message
import asyncio
from InformationCollector import InformationCollector
from TradeoffAnalyst import TradeoffAnalyst
import pandas as pd
from metagpt.actions import Action, UserRequirement
import os
import json
        

async def main():
    os.environ["http_proxy"] = "http://127.0.0.1:10809"
    os.environ["https_proxy"] = "http://127.0.0.1:10809"
    context = Context() # Load config2.yaml
    env = Environment(context=context)
    env.add_roles([AspectIdentifier(),InformationCollector(),AspectAnalyst(),AspectReviewer(),TradeoffAnalyst()])

    df = pd.read_excel("C:\\Research\\LLMsForDesignProblem\\code\\formal_experiment\\AI_Agent\\formal_experiment_AIAgent-test.xlsx")
    selected_columns = df[["Post ID","Architecture Problem","Architecture Decision"]]
    for index,row in selected_columns.iterrows():
        data = {
        "architecture_problem": row['Architecture Problem'].replace('\n', ' '),
        "architecture_design_decision": row['Architecture Decision'].replace('\n', ' ')
        }
        temp_str = json.dumps(data)
        print(temp_str)
        with open("C:\\Research\\LLMsForDesignProblem\\code\\formal_experiment\\AI_Agent\\rationale.txt", "a") as f:
            f.write("+"*40+"\n")
            f.write("+"*40+"\n")
            f.write("+"*40+"\n")
            f.write("###"+str(row['Post ID'])+"###"+'\n')
            f.write("\n")
            print("The Issue ID have been written to the file!！")
        env.publish_message(Message(content=temp_str, cause_by=UserRequirement))
        while not env.is_idle:
            await env.run()

asyncio.run(main())