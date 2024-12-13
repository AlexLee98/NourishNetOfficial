from typing import Annotated, List, Sequence
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_openai import ChatOpenAI


anthropic_model = "claude-3-5-haiku-latest"
gpt_model = "gpt-3.5-turbo"
############################## State for Analyst Graph ###########################
class AnalystState(TypedDict):
    macro_nutrients: str
    sustainability: str
    recipe: str


############################## Nutrition Analyzer ###########################

from langchain_anthropic import ChatAnthropic

nut_analyzer_prompt = ChatPromptTemplate.from_template(
    """You are a nutrition analyst. Your job is to analyze a recipe and generate a detailed report on the macronutrients 
        composition and calories analysis. You can see the recipe here:
        #######################
        {recipe}
        #######################
    """
)

nut_analyzer_llm = ChatAnthropic(model=anthropic_model)
nut_analyzer = nut_analyzer_prompt | nut_analyzer_llm

def nut_analyzer_node(state: AnalystState) -> AnalystState:
    res = nut_analyzer.invoke({"recipe": state["recipe"]})
    return { "macro_nutrients" : res.content}

############################## Environmental sustainability Analyzer ###########################

from langchain_anthropic import ChatAnthropic

env_analyzer_prompt = ChatPromptTemplate.from_template(
    """You are an environmental sustainability analyst. Your job is to analyze a recipe and generate a detailed report on 
        its environmental sustainability impact. Recommend ways to minimize the impact. Give a LETTER grade to the recipes based 
        on the impact to the environment.
        You can see the recipe here:
        #######################
        {recipe}
        #######################
    """
)

env_analyzer_llm = ChatAnthropic(model=anthropic_model)
env_analyzer = env_analyzer_prompt | env_analyzer_llm

def env_analyzer_node(state: AnalystState) -> AnalystState:
    res = env_analyzer.invoke({"recipe": state["recipe"]})
    return { "sustainability" : res.content}


############################## Analyst Graph ###########################

assessment_builder = StateGraph(AnalystState)
assessment_builder.add_node("nutrition_analyst", nut_analyzer_node)
assessment_builder.add_node("environment_analyst", env_analyzer_node)
assessment_builder.add_edge(START, "nutrition_analyst")
assessment_builder.add_edge("nutrition_analyst", "environment_analyst")
assessment_graph = assessment_builder.compile()

############################## State for Main Graph ###########################

class State(TypedDict):
    messages: Annotated[list, add_messages]
    plan: str
    recipe: str
    shopping_list: str
    macro_nutrients: str
    sustainability: str


############################## Assessment Node for the Main Graph ###########################

def analyst_node(state: State) -> State:
    res = assessment_graph.invoke({"recipe" : state["recipe"]})
    return ({"macro_nutrients": res["macro_nutrients"],
            "sustainability" : res["sustainability"]})

############################## Planner ###########################

planner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a meal planner and your job is to generate a meal plan based on the information  "
            " provided by the users. User will provide the kind of cuisine that they like, their dietary restriction, how many meals they need etc. "
            " Generate the meal plan based on the requirements from the users. If the user provides recommendations to improve the plan, respond "
            " with a revised version of your previous attempt. You must provide a verion of the meal plan in each iteration of your response.",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

planner_llm = ChatOpenAI(model=gpt_model, temperature=0)
planner = planner_prompt | planner_llm

async def planner_node(state: State) -> State:
    res = await planner.ainvoke(state["messages"])
    return {"messages": [res], "plan" : res.content}

############################## Reviewer ###########################

reviewer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a meal plan reviewer, your job is to review the generated meal plan "
            " to make sure the plan meets the user's requirements. You will provide "
            " a list of improvements the meal author can adopt to improve the plan."
            " Must recommend changes, major or minor, to the submitted plan in all iterations. ",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

reviewer_llm = ChatAnthropic(model=anthropic_model)
reviewer = reviewer_prompt | reviewer_llm


async def reviewer_node(state: State) -> State:
    cls_map = {"ai": HumanMessage, "human": AIMessage}
    translated = [state["messages"][0]] + [
        cls_map[msg.type](content=msg.content) for msg in state["messages"][1:]
    ]
    res = await reviewer.ainvoke(translated)
    # We treat the output of the reviewer as human feedback 
    return {"messages": [HumanMessage(content=res.content)]}


def should_continue_reviewer(state: State):
    if len(state["messages"]) > 4:
        # End after 3 iterations
        return "chef"
    return "reviewer"

############################## CHEF ###########################

from langchain_core.tools import tool

chef_prompt = ChatPromptTemplate.from_template(
    """You are a recipe author and your job is to generate the necessary recipes  
        based on the given meal plan here: 
        {plan}..
        Generate recipes for the entire meal plan, including breakfast, lunch and dinner.
        Must generate reipes for the full set of the plan, even if the plan spans across multiple days.
        The recipes must contain sufficiwnt details that 
        the users can follow to prepare the meals. Please use the ingredients that will 
        satisfy the user requirements and dietary restrictions. 
        Please specifiy the quantity and portion for each ingredient in the recipe.
    """
)

chef_llm = ChatAnthropic(model=anthropic_model)

chef = chef_prompt | chef_llm

def chef_node(state: State) -> State:

    res = chef.invoke({"plan": state["plan"]})
    return {"recipe" : res}

 
############################  Butler ###############################


from langchain_anthropic import ChatAnthropic
from my_agent.utils.tools import extract_costco_deals, return_ingredients_list
from langgraph.prebuilt import ToolNode

#butler_llm = ChatOpenAI(model=gpt_model, temperature=0)
butler_llm = ChatAnthropic(model=anthropic_model)
butler_prompt = ChatPromptTemplate.from_template(
    """ 
      You are a meal ingredients recorder, based on the generated receipes
        you will do the following 4 tasks:  
        1. Inform the user of their current ingredient inventory. 
        2. Create a shopping list with ingredient quantities from the recipes, removing any items 
        already available in the current ingredient inventory. Ensure the quantities that you specify
        are suitable for grocery store purchases. For example, 2 tbsp of sugar should be upgraded to one box of sugar,
        1 cup of rice should be changed to 1 bag of rice. Quantity under one bottle or one box are not purchasable
        at a grocery store.
        3. Try your best effort to estimate the total cost of these ingridents on the shopping list
         needed for the recipes. Rough guess is ok.
        4. At the end, ask the user if he/she wants to go ahead to order the ingridents. Tell the user 
        to answer in yes/no. 

        You can find the current ingredient inventory list here:
        ########################################
        {ingredients_list}
        ########################################

        You can find the recipes here:
        ########################################
        {recipe}
        ########################################
    """
)

butler= butler_prompt | butler_llm


def butler_node(state: State) -> State:

    ingredients_list = return_ingredients_list()
    res = butler.invoke({"recipe": state["recipe"],  "ingredients_list" : ingredients_list})
    return {"shopping_list" : res}



############################  Human ###############################

#from langgraph.errors import NodeInterrupt

def human_feedback(state: State) -> State:
    '''
    raise NodeInterrupt("Proceed to do shopping?")
    return state
    '''
    pass

def should_continue_human(state: State):
    messages = state["messages"]
    last_message = messages[-1]
    
    if isinstance(last_message, HumanMessage):
        content = last_message.content
        if content.casefold() == "yes".casefold():
            return "agent"
    return "end"


############################  Shopper ###############################

from langchain_anthropic import ChatAnthropic
from my_agent.utils.tools import extract_costco_deals
from langgraph.prebuilt import ToolNode
from datetime import datetime
import pytz
import requests
import json
import getpass
import os


shopper_llm = ChatAnthropic(model=anthropic_model)
shopper_prompt = ChatPromptTemplate.from_template(
    """ 
      You are a grocery buyer, based on the generated shopping list
        you will do the following 3 tasks:  
        1. compose a professional message to the grocery vendor 
        'Wholefoods' to purchase the grocery items, use my name 'Marcus Lee' to sign the message
        2. If the messaging tool is available, send the composed message to the vendor.
        You can find the shopping list here:
        ########################################
        {shopping_list}
        ########################################
        3. Go to the next step (Continue) once the message is sent. Make sure only one and only one message will be sent.
    """
)

LOOP_AUTH_KEY = os.environ["LOOP_AUTH_KEY"]
LOOP_API_KEY = os.environ["LOOP_API_KEY"]
PHONE_NUMBER = os.environ["PHONE_NUMBER"]

@tool
def messaging_tool(mesg_body: str) -> State:
    """Call to send messages """


    # Get the current time in UTC
    now_utc = datetime.now(pytz.utc)
    timezone = pytz.timezone('America/Los_Angeles')
    now_local = now_utc.astimezone(timezone)
    formatted_time = now_local.strftime("%Y-%m-%d %H:%M:%S %Z%z")

    mesg_body = "The current time is " + formatted_time + "\n" + "Go Bears Forever!!!\n" + mesg_body

    url = "https://server.loopmessage.com/api/v1/message/send/"

    headers = {"Content-Type": "application/json; charset=utf-8",
                "Authorization": LOOP_AUTH_KEY,
                "Loop-Secret-Key": LOOP_API_KEY}

    data = {
        "recipient": PHONE_NUMBER,
        "text": mesg_body
    }

    response = requests.post(url, headers=headers, json=data)
    return {"messages": [AIMessage(content="Message sent.")]}


shopper_tools = [messaging_tool]
shopper_llm = shopper_llm.bind_tools(shopper_tools)
shopper = shopper_prompt | shopper_llm

shopper_tool_node = ToolNode(shopper_tools)

def shopper_node(state: State) -> State:
    translated = [{"shopping_list": state["shopping_list"]}] 
    res = shopper.invoke(translated)
    return {"messages": [res]}

def should_continue_shopper(state: State):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "shopper_tools"
    return "continue"


############################## Main Graph ######################################

builder = StateGraph(State)
builder.add_node("planner", planner_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("chef", chef_node)
builder.add_node("analyst", analyst_node)
builder.add_node("human", human_feedback)
builder.add_node("butler", butler_node)
builder.add_node("shopper", shopper_node)
builder.add_node("shopper_tools", shopper_tool_node)

builder.add_edge(START, "planner")

builder.add_conditional_edges("planner", should_continue_reviewer,
    {
        "chef": "chef",
        "reviewer": "reviewer",
    },)
builder.add_edge("reviewer", "planner")
builder.add_edge("chef", "analyst")
builder.add_edge("analyst", "butler")
builder.add_edge("butler", "human")

builder.add_conditional_edges("human", should_continue_human,
    {
        "agent": "shopper",
        "end": END
    },)

builder.add_conditional_edges("shopper", should_continue_shopper,
    {
        "shopper_tools": "shopper_tools",
        "continue": END
    },)

memory = MemorySaver()
graph = builder.compile(checkpointer=memory, interrupt_before=["human"])