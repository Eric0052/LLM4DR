import numpy as np
import re
import asyncio
from metagpt.actions import Action
from metagpt.roles import Role
import asyncio

from metagpt.context import Context
from metagpt.roles.product_manager import ProductManager
from metagpt.logs import logger
from metagpt.schema import Message
import json
from AspectAnalyst import AnalyseAspect
from AspectReviewer import ReviewAspect

class TradeoffAnalyse(Action):

    PROMPT_TEMPLATE : str = """
    Here is a Software Architecture and its corresponding Architecture Design Decision below:\n
    Architecture Problem: {architecture_problem}\n
    Architecture Design Decision: {architecture_design_decision}\n
    This architectural decision has been analyzed from the following aspects:
    {review_rationale}
    Based on the analysis from various aspects above, please weigh the tradeoffs and provide the rationale for choosing this architectural decision.
    """

    name : str = "TradeoffAnalyse"


    async def run(self, architecture_problem: str, architecture_design_decision: str, review_results_str: str):
        prompt = self.PROMPT_TEMPLATE.format(architecture_problem=architecture_problem, architecture_design_decision=architecture_design_decision, review_rationale=review_results_str)
        rsp = await self._aask(prompt)
        relevant_aspect = TradeoffAnalyse.parse_relevant_aspect(rsp)
        return relevant_aspect
    
    
class TradeoffAnalyst(Role):
    name: str = "Agent5"
    profile: str = "TradeoffAnalyst"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([TradeoffAnalyse])
        self._watch([ReviewAspect])

    async def _act(self):
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo
        single_news = self.rc.news[0]
        msg_dict = json.loads(single_news.content)
        review_results_str = "\n".join(msg_dict["review_result"])
        print("+"*10)
        print(msg_dict)
        print("+"*10)
        code_text = await todo.run(msg_dict["architecture_problem"], msg_dict["architecture_design_decision"], review_results_str)
        with open("rationale.txt", "a") as f:
            f.write("*"*20+"Tradeoff Analysis"+ "*"*20)
            f.write("\n")
            f.write(code_text)
            f.write("\n")
            f.write("+"*40+"\n")
            f.write("+"*40+"\n")
            f.write("+"*40+"\n")
            print("The Trade-off results have been written to the file!！")