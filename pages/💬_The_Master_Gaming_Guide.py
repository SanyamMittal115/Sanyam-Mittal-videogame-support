import streamlit as st
import google.generativeai as genai
import requests

# IGDB API credentials (same as other pages)
clientId = "v6yo10056ivny6edxfhgffzzehj0xi"
accessToken = "c2bjrpjxl4f4d3zh4b44xfvh7bn37w"
geminiKey = "AIzaSyCKOVdIzGdij5QOUT2YrVCJ1Fzh6qzsOkc"

apiHeaders = {
	"Client-ID": clientId,
	"Authorization": f"Bearer {accessToken}"
}

# get gemini working correctly
genai.configure(api_key=geminiKey)

def fetchGameData(gameName, limit=5):
	query = f"""
	search "{gameName}";
	fields name, rating, aggregated_rating, summary, genres.name, platforms.name, screenshots, first_release_date;
	limit {limit};
	"""
	try:
		response = requests.post("https://api.igdb.com/v4/games", headers=apiHeaders, data=query)
		return response.json()
	except Exception as e:
		st.error(f"Error fetching games. Ask Sneh or Sunny because their API may have rate limits or authentication issues.")
		return []

def fetchPopularGames(limit=20):
	query = f"""
	fields name, rating, aggregated_rating, summary, genres.name, platforms.name, screenshots, first_release_date;
	where rating != null & aggregated_rating != null;
	sort aggregated_rating desc;
	limit {limit};
	"""
	try:
		response = requests.post("https://api.igdb.com/v4/games", headers=apiHeaders, data=query)
		return response.json()
	except Exception as e:
		st.error(f"Error fetching popular games. Ask Sneh or Sunny because their API may have rate limits or authentication issues.")
		return []

def formatGameDataForContext(gameData):
	if not gameData:
		return "No specific game data available."
	
	contextText = "Current game database information:\n"
	for game in gameData[:25]:  # Limit to avoid token overflow
		contextText += f"\n- {game.get('name', 'Unknown')}"
		if 'rating' in game:
			contextText += f" (Expert Rating: {game['rating']:.1f})"
		if 'genres' in game:
			genres = [gENRESstuff.get('name', '') for gENRESstuff in game['genres']]
			if genres:
				contextText += f" - Genres: {', '.join(genres)}"
		if 'summary' in game and game['summary']:
			summary = game['summary']
			contextText += f" - {summary}"
		contextText += "\n"
	
	return contextText

def snehSunnyBOTResponse(userMessage, conversationHistory, gameContext):	
	systemPrompt = f"""You are a master gaming guide and expert gamer who specializes in helping players overcome challenges, 
	solve puzzles, and progress through difficult sections of video games. You can provide detailed assistance for any gaming situation.

    Current game data context:
    {gameContext}

    Conversation history:
    {conversationHistory}

    (Some of) Your Expertise Areas:
    Boss fight strategies and tactics
    Puzzle solutions and hints (without spoiling the experience)
    Character builds, skill trees, and optimization
    Combat mechanics and advanced techniques
    Hidden secrets, easter eggs, and collectibles
    Quest progression and story advancement
    Equipment recommendations and upgrade paths
	- and much more!

    Instructions:
    Provide specific solutions to gaming problems
    Offer step by step guidance for complex challenges
    Give strategic advice based on the user's skill level
    Include multiple strategies when possible (easy/hard modes, different playstyles)
    Be encouraging and supportive!
    Reference specific game mechanics, items, or locations when helpful

    User's current situation/question: {userMessage}
    """

	try:
		model = genai.GenerativeModel("gemini-2.5-flash") ########## Important #########
		response = model.generate_content(systemPrompt)
		return response.text
		
	except Exception as e:
		# Error handling for various issues
		errorMessage = str(e).lower()
		
		if "rate limit" in errorMessage or "quota" in errorMessage:
			return "I'm am currently hitting the rate limit on my requests! Ask Sneh and Sunny for help or try your question again in a few seconds!"
		elif "safety" in errorMessage or "inappropriate" in errorMessage:
			return "Werid. Your message might contain some fishy, perhaps inappropriate content. Ask Sneh and Sunny for help and try let's strictly talk about video games and gaming topics!"
		elif "timeout" in errorMessage:
			return "It took way too long to come up with a response. Ask Sneh and Sunny for help and try rephrasing your question!"
		else:
			return "Uhoh! There seems to be an unknown issue that occured when create my response. If the problem keeps happening, the developers (Sneh and Sunny) might need to check the system!"

def main():
	st.title("Master Gaming Guide")
	st.write("Stuck in a game? I'm your expert gaming guide! Tell me what challenge you're facing and I'll help you overcome it with detailed strategies, walkthroughs, and tips.")
	
	st.markdown("**💡 Example questions:**")
	st.markdown("- *I'm stuck on the Margit boss fight in Elden Ring*")
	st.markdown("- *How do I solve the water temple puzzle in Zelda?*")
	st.markdown("- *What's the best build for a beginner in Dark Souls?*")
	st.markdown("---")
	
	# Session state for Conversation history so gemini knows past messages
	if 'chatHistory' not in st.session_state:
		st.session_state.chatHistory = []
	if 'gameContext' not in st.session_state:
		# Load some popular games as initial Context
		popularGames = fetchPopularGames(40)
		st.session_state.gameContext = formatGameDataForContext(popularGames)
	
	# game Context loader
	with st.expander("Load specific game data for specific games"):
		searchGame = st.text_input("Enter the game you need help with:")
		if st.button("Load Game Data") and searchGame:
			with st.spinner("Loading game information..."):
				gameData = fetchGameData(searchGame, limit=3)
				if gameData:
					newContext = formatGameDataForContext(gameData)
					st.session_state.gameContext += f"\n\nDetailed context for '{searchGame}':\n{newContext}"
					st.success(f"Loaded data for {searchGame}! now I can provide more Specific help.")
				else:
					st.warning("couldn't find data for that game, but I can still help with general guidance! Make sure to type the exact game name.")
	
	for message in st.session_state.chatHistory:
		with st.chat_message(message["role"]):
			st.write(message["content"])
	
	# Chat input
	userInput = st.chat_input("What gaming challenge can I help you with?")
	
	if userInput:
		st.session_state.chatHistory.append({"role": "user", "content": userInput})
		
		with st.chat_message("user"):
			st.write(userInput)
		
		# generate bot response
		with st.chat_message("aiAssistant"):
			with st.spinner("I am thinking..."):
				# build conversation history string
				conversationHistory = ""
				for msg in st.session_state.chatHistory: 
					conversationHistory += f"{msg['role'].title()}: {msg['content']}\n"
				
				# generate response
				botResponse = snehSunnyBOTResponse(userInput, conversationHistory, st.session_state.gameContext)
				
				st.write(botResponse)
				
				# add bot response to history
				st.session_state.chatHistory.append({"role": "aiAssistant", "content": botResponse})

if __name__ == '__main__':
	main()