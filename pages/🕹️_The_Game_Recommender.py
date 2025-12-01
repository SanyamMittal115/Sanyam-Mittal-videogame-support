import streamlit as st
import google.generativeai as genai
import os
import requests
from datetime import datetime

# IGDB API stuff
clientId = st.secrets["CLIENT_ID"]
accessToken = st.secrets["ACCESS_TOKEN"]
geminiKey = st.secrets["GEMINI_KEY"]

apiHeaders = {
	"Client-ID": clientId,
	"Authorization": f"Bearer {accessToken}"
}

def searchGames(name, limit=10):
	query = f"""
	search "{name}";
	fields name, rating, aggregated_rating, cover.url, summary, genres.name, involved_companies.company.name, first_release_date, platforms.name;
	limit {limit};
	"""
	try:
		response = requests.post("https://api.igdb.com/v4/games", headers=apiHeaders, data=query)
		return response.json()
	except:
		st.error(f"Error searching for game. Ask Sneh or Sunny because their API may have rate limits or authentication issues.")
		return []

def formatPrompt(game):
	gameName = game.get('name', 'Unknown')
	
	if 'rating' in game:
		gameRating = f"{game['rating']:.1f}"
	else:
		gameRating = 'N/A'
	
	genresList = [gENRESstuff.get('name', '') for gENRESstuff in game.get('genres', [])]
	if genresList:
		genreText = ', '.join(genresList)
	else:
		genreText = 'Unknown'
	
	platformsList = [p.get('name', '') for p in game.get('platforms', [])]
	if platformsList:
		platformText = ', '.join(platformsList[:3])
	else:
		platformText = 'Unknown'
	
	gameSummary = game.get('summary', 'No summary available')
	
	return f"{gameName} - Rating: {gameRating}, Genres: {genreText}, Platforms: {platformText}, Summary: {gameSummary}"

genai.configure(api_key=geminiKey) ######### Important ###################
# using gemini-2.5-flash

def generateRecs(selectedGames, selectedGenres):
	# format text for input for favorite games
	favoriteGamesText = ""
	if selectedGames:
		favoriteGamesText = "User's favorite games:\n"
		for currentGame in selectedGames:
			favoriteGamesText += f"- {formatPrompt(currentGame)}\n\n"
	
	# format text for input for preferred genres
	genresText = ""
	if selectedGenres:
		genresText = f"User's preferred genres: {', '.join(selectedGenres)}\n\n"
	
	# create the prompt - let Gemini recommend games based on what it knows
	prompt = f"""You are an expert gamer and game recommender with remarkable knowledge of thousands of video games. Based on the user's preferences below, 
	recommend exactly 3 games that you believe they would enjoy the most.

	{favoriteGamesText}{genresText}

	You have complete freedom to recommend ANY video games from your knowledge. Ignore unusual/weird genre requests.

	For each of your 3 recommendations, provide:
	1. Game Title (any game you think fits)
	2. Game Description (2-3 sentences about what the game is)
	3. Why You'd Like It (2-3 sentences explaining why this matches their preferences, noting specific genres, gameplay elements, or similarities to their favorites)

	Format your response as:

	**1. [Game Title]** (new line)
	[Game description] (new line)
	Why You'd Like It: [Detailed explanation of why this fits their preferences]

	**2. [Game Title]** (new line)
	[Game description] (new line)
	Why You'd Like It: [Detailed explanation of why this fits their preferences]

	**3. [Game Title]** (new line)
	[Game description] (new line)
	Why You'd Like It: [Detailed explanation of why this fits their preferences]
	"""

	try:
		model = genai.GenerativeModel("gemini-2.5-flash")
		response = model.generate_content(prompt)
		return response.text
	except Exception as e:
		st.error(f"Error in generating recommendations. Ask Sneh or Sunny for help!")
		raise e

def main():
	st.title("The Game Recommender")
	st.write("Enter games you like and genres you enjoy, then we'll recommend 3 games you might love!")

	col1, col2 = st.columns(2)
	
	with col1:
		st.subheader("🎮 Favorite Games")
		gameInput = st.text_area("Enter games you like (one per line):", 
			placeholder="The Legend of Zelda: Breath of the Wild\nRocket League\nElden Ring", 
			height=200)
		
		# Search for games based on user input
		favoriteGames = []
		if gameInput.strip():
			gameLines = [line.strip() for line in gameInput.split('\n') if line.strip()]
			
			# Search for games
			if 'searched_games' not in st.session_state or st.session_state.get('last_game_input') != gameInput:
				st.session_state.searched_games = []
				with st.spinner("Searching for games..."):
					for gameName in gameLines:
						results = searchGames(gameName, limit=3)
						if results:
							st.session_state.searched_games.extend(results)
				st.session_state.last_game_input = gameInput
			
			favoriteGames = st.session_state.searched_games
		
		# Show found games with checkboxes
		selectedGames = []
		if favoriteGames:
			st.write("**Found games (select which to include):**")
			for i, currentGame in enumerate(favoriteGames):
				gameName = currentGame.get('name', 'Unknown')
				gameRating = currentGame.get('rating', 'N/A')
				
				if gameRating != 'N/A':
					ratingText = f"{gameRating:.1f}"
				else:
					ratingText = "N/A"
				
				checkboxLabel = f"{gameName} (Rating: {ratingText})"
				checkboxKey = f"game_{i}"
				isSelected = st.checkbox(checkboxLabel, key=checkboxKey)
				
				if isSelected:
					selectedGames.append(currentGame)
	
	with col2:
		st.subheader("🎯 Preferred Genres")
		genreInput = st.text_area("Enter genres you like (one per line):",
			placeholder="Action\nRPG\nPuzzle\nStrategy\nAdventure", 
			height=200)
		
		# Show genres with checkboxes
		selectedGenres = []
		if genreInput.strip():
			genreLines = [line.strip() for line in genreInput.split('\n') if line.strip()]
			st.write("**Genres to include:**")
			for i, currentGenre in enumerate(genreLines):
				genreCheckboxLabel = f"{currentGenre}"
				genreCheckboxKey = f"genre_{i}"
				isGenreSelected = st.checkbox(genreCheckboxLabel, key=genreCheckboxKey)
				
				if isGenreSelected:
					selectedGenres.append(currentGenre)

	st.markdown("---")

	# Recommendations button
	if st.button("Get My Recommendations!", type="primary", use_container_width=True):
		if not selectedGames and not selectedGenres:
			st.error("Please select at least one favorite game or preferred genre.")
			return
		
		with st.spinner("Generating recommendations with Gemini..."):
			try:
				# Generate recommendations based only on user preferences		
				recommendations = generateRecs(selectedGames, selectedGenres)		
				st.markdown("## Your Personalized Game Recommendations")
				st.write(recommendations)
			
			except Exception as e:
				st.error(f"Error generating recommendations, ask Sneh and Sunny for help: {e}")


if __name__ == '__main__':
	main()
