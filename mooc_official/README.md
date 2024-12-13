NourishNet Meal Planning System User Guide

Prerequisite
1. Docker Desktop 4.24
2. Docker-compose version 2.22.0+ or higher.
3. MacOS 


1. Download and install Docker Desktop a. https://docs.docker.com/engine/install/
2. Download and install langgraph studio 0.0.30 a. https://github.com/langchain-ai/langgraph-studio/releases
3. Download the nourishNet githiub repo a. https://github.com/AlexLee98/NourishNet/tree/main
4. Create a Langsmith account a. https://smith.langchain.com/
5. Optional: Create a Loop Message iMessage API free sandbox account (if you want to receive the shopping list from the shopper agent via text messaging) a. https://loopmessage.com/server
6. Edit the mooc/env file to enter API keys for the following services 
	a. Anthropic Claude LLM 
		i. Key name: ANTHROPIC_API_KEY 
	b. Langsmith service 
		i. Key name: LANGSMITH_API_KEY 
	c. Open AI 
		i. Key name: OPENAI_API_KEY 
	d. LOOP Message Service (If you want to receive the shopping list from the Shopper Agent) 
		i. Key name: LOOP_AUTH_KEY 
		ii. Key name: LOOP_API_KEY 
		iii. Key name (phone number to receive the shopping list): PHONE_NUMBER
7. Rename the env to .env in the mooc folder
8. Launch the Langgraph Studio
9. Click on the “Click to select” button on the Langgraph Studio GUI
10. Select the NourishNet/mooc folder to load the NourishNet project. This will load the NourishNet project into the Langgraph Studio GUI
11. After the project is loaded, in the Input Dialogue box, click on the “Messages” box, and enter your prompt in the “1” text box within the "[]". There should be dietary requirements and preferences included in the prompt, for example: “Generate a 1-day Keto style meal plan”
12. Click on the "Submit" button
13. The planner agent, the reviewer agent, the chef agent, the analyst team, and the butler agent will take your input and do their processing. The butler will generate a shopping list and ask you if you would like to send the shopping list to a grocery vendor
14. Click on the “Messages” box, and enter yes within the "[]" to send the shopping list to the vendor, or enter no to end the whole process. 
