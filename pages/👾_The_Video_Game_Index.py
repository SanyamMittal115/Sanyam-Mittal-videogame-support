import streamlit as st
import requests
import random
import time
import pandas as pd

# My IGDB API credentials - need these for every request
clientId = st.secrets["CLIENT_ID"]
accessToken = st.secrets["ACCESS_TOKEN"]

# Setting up headers for the API
apiHeaders = {
    "Client-ID": clientId,
    "Authorization": f"Bearer {accessToken}"
}


# Helper function to safely get cover URLs without crashing on missing data
def get_cover_url(game_dict, cover_size="t_cover_big"):
    if isinstance(game_dict, dict):
        cover = game_dict.get("cover")
        if isinstance(cover, dict) and cover.get("url"):
            url = cover["url"].replace("t_thumb", cover_size)
            return "https:" + url if url.startswith("//") else url
    return "https://via.placeholder.com/250x350?text=No+Cover+Available"


# Search function when user types in a game name
def searchGame(gameName):
    query = f"""
    search "{gameName}";
    fields name, rating, cover.url, summary, genres.name, involved_companies.company.name, 
           first_release_date, platforms.name, aggregated_rating, aggregated_rating_count;
    limit 20;
    """
    
    try:
        # Had to use POST instead of GET here - IGDB API requirement
        response = requests.post("https://api.igdb.com/v4/games", headers=apiHeaders, data=query)
        games = response.json()
        return games if isinstance(games, list) else []
    except Exception as e:
        st.error("Error searching for game. Check API credentials or rate limits.")
        return []


# Gets some preset games to show on the chart when page loads
def fetchInitialGames():
    gameNames = ["Grand Theft Auto V", "Minecraft", "Rocket League", "The Legend of Zelda: Breath of the Wild", "The Last of Us", "League of Legends", "Valorant", "Mario Hotel", "Bubsy 3D"]
    initialGames = []
    
    for gameName in gameNames:
        query = f"""
        search "{gameName}";
        fields name, rating, cover.url, summary, genres.name, involved_companies.company.name, 
               first_release_date, platforms.name, aggregated_rating, aggregated_rating_count;
        limit 1;
        """
        
        try:
            response = requests.post("https://api.igdb.com/v4/games", headers=apiHeaders, data=query)
            results = response.json()
            if results and isinstance(results, list) and 'rating' in results[0]:
                initialGames.append(results[0])
        except:
            # some games don't have a rating so skip them
            continue
    
    return initialGames


# Converts seconds to nice readable format
def formatTime(totalSeconds):
    minutes = totalSeconds / 60
    if minutes < 1:
        return f"{int(totalSeconds)} seconds"
    elif minutes == 1:
        return "1 minute"
    else:
        return f"{minutes:.1f} minutes"


# Shows all the details for a specific game
def gameDetails(game):
    col1, col2 = st.columns([1, 2])
    
    with col1:
        coverUrl = get_cover_url(game, "t_cover_big")
        st.image(coverUrl, use_container_width=True)
    
    with col2:
        # Game title at top
        st.subheader(game.get('name', 'Unknown Game'))
        
        # Show expert rating if available
        if 'rating' in game:
            st.metric("Expert Rating", f"{game['rating']:.1f}/100")
        
        # Show user rating maybe
        if 'aggregated_rating' in game:
            st.metric("User Rating", f"{game['aggregated_rating']:.1f}/100")
        
        # List all the genres
        if 'genres' in game and isinstance(game['genres'], list):
            genresList = [g['name'] for g in game['genres'] if isinstance(g, dict) and 'name' in g]
            if genresList:
                st.write(f"**Genres:** {', '.join(genresList)}")
        
        # List companies involved
        if 'involved_companies' in game and isinstance(game['involved_companies'], list):
            companiesList = [ic['company']['name'] for ic in game['involved_companies'] if isinstance(ic, dict) and 'company' in ic and 'name' in ic['company']]
            if companiesList:
                st.write(f"**Companies:** {', '.join(companiesList)}")
        
        # Release date
        if 'first_release_date' in game:
            from datetime import datetime
            releaseDate = datetime.fromtimestamp(game['first_release_date'])
            st.write(f"**Release Date:** {releaseDate.strftime('%B %d, %Y')}")
        
        # What platforms its on
        if 'platforms' in game and isinstance(game['platforms'], list):
            platforms = [p['name'] for p in game['platforms'] if isinstance(p, dict) and 'name' in p]
            if platforms:
                st.write(f"**Platforms:** {', '.join(platforms)}")
    
    # Game description at the bottom
    if game.get('summary'):
        st.write("**Summary:**")
        st.write(game['summary'])


# Game over screen when player loses or time runs out
def showGameOverScreen():
    st.markdown("## Game Over!")

    if st.session_state.get("game_over_reason") == "time":
        st.warning("⏰ Time's up! ⏰")
    else:
        st.error("❌ Wrong Answer! ❌")
        if "last_game_info" in st.session_state:
            info = st.session_state.last_game_info
            st.write(f"{info['name']} has a rating of **{info['rating']:.1f}**")
    
    st.markdown("---")
    st.markdown(f"### 🏆 Final Score: **{st.session_state.get('score', 0)}** -- Sneh and Sunny think you did great!")
    st.markdown("---")
    
    # Button to restart
    if st.button("🎮 Play Again", use_container_width=True):
        savedChartGames = st.session_state.get('chart_games', [])
        st.session_state.clear()
        st.session_state.chart_games = savedChartGames
        st.rerun()


# Setup screen before game starts - choose time limit
def showSetupScreen():
    st.markdown("### How long do you want to play?")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        selectedMinutes = st.slider(
            "Game duration (minutes):",
            min_value=0.5,
            max_value=5.0,
            value=2.0,
            step=0.5,
            format="%.1f"
        )
        
        selectedSeconds = int(selectedMinutes * 60)
        
        if selectedMinutes < 1:
            timeDisplay = f"{selectedSeconds} seconds"
        elif selectedMinutes == 1:
            timeDisplay = "1 minute"
        else:
            timeDisplay = f"{selectedMinutes:.1f} minutes"
        
        st.write(f"**Selected time: {timeDisplay}**")
        noLimit = st.checkbox("♾️ No time limit ♾️")
        
        st.markdown("---")
        
        if st.button("🚀 Start Game 🚀", use_container_width=True, type="primary"):
            st.session_state.game_started = True
            st.session_state.selected_duration = None if noLimit else selectedSeconds
            st.rerun()


# Creates a bar chart based on the games list with filters
def makeChart(gamesList, minRating=0, maxRating=100, selectedGenres=None):
    if not gamesList:
        return None
    
    names = []
    ratings = []
    
    for game in gamesList:
        gameRating = game.get('rating', 0)
        if gameRating < minRating or gameRating > maxRating:
            continue
        
        shouldInclude = True
        if selectedGenres:
            shouldInclude = False
            if 'genres' in game and isinstance(game['genres'], list):
                for genre in game.get('genres', []):
                    if genre.get('name') in selectedGenres:
                        shouldInclude = True
                        break
        
        if shouldInclude:
            names.append(game.get('name', 'Unknown'))
            ratings.append(gameRating)
    
    if len(names) == 0:
        return None
    
    df = pd.DataFrame({'Game': names, 'Rating': ratings})
    df = df.sort_values('Rating')
    df = df.set_index('Game')
    return df


# This function grabs games from IGDB for the higher/lower game
def fetchGames():
    allGames = []
    ranges = [(20, 40), (40, 60), (60, 80), (80, 100)]
    
    for minRating, maxRating in ranges:
        randomOffset = random.randint(0, 2000)
        
        query = f"""
        fields name, rating, cover.url, summary;
        where rating != null & cover != null & rating >= {minRating} & rating <= {maxRating};
        limit 5;
        offset {randomOffset};
        """
        
        try:
            response = requests.post("https://api.igdb.com/v4/games", headers=apiHeaders, data=query)
            games = response.json()
            if isinstance(games, list):
                for game in games:
                    allGames.append(game)
        except:
            st.error(f"Error fetching games for rating range {minRating}-{maxRating}.")
            continue
    
    if len(allGames) < 2:
        st.error(f"Not enough games fetched. Only got {len(allGames)} games.")
        return []
    
    return allGames


# Check if guess was right or wrong
def makeGuess(higherGuess):
    currentGame = st.session_state.current
    nextGame = st.session_state.next
    
    actuallyHigher = nextGame.get("rating", 0) > currentGame.get("rating", 0)
    isCorrect = actuallyHigher == higherGuess

    if isCorrect:
        st.session_state.score += 1
        st.success(f"✅ Correct! {nextGame.get('name')} has a rating of {nextGame.get('rating', 0):.1f}")
    else:
        st.session_state.game_over = True
        st.session_state.game_over_reason = "wrong"
        st.session_state.last_game_info = {
            "name": nextGame.get("name", "Unknown"),
            "rating": nextGame.get("rating", 0)
        }
        time.sleep(1)
        st.rerun()
        return

    st.session_state.index += 1
    st.session_state.current = nextGame
    
    if st.session_state.index + 1 >= len(st.session_state.games):
        st.success(f"You've completed all games! Final score: {st.session_state.score}")
        st.session_state.game_over = True
        st.session_state.game_over_reason = "complete"
        time.sleep(2)
        st.rerun()
        return
    
    st.session_state.next = st.session_state.games[st.session_state.index + 1]
    time.sleep(1)
    st.rerun()


# This section has the search bar and comparison chart
def searchAndGraph():
    if 'chart_games' not in st.session_state:
        with st.spinner("Loading initial games..."):
            st.session_state.chart_games = fetchInitialGames()

    if st.session_state.chart_games:
        st.subheader("📊 Game Ratings Comparison")
        
        with st.expander("Filters", expanded=False):
            colF1, colF2 = st.columns(2)
            
            with colF1:
                minRating, maxRating = st.slider(
                    "Rating Range:",
                    min_value=0.0,
                    max_value=100.0,
                    value=(0.0, 100.0),
                    step=1.0
                )
            
            with colF2:
                allGenres = []
                for game in st.session_state.chart_games:
                    if 'genres' in game and isinstance(game['genres'], list):
                        for genre in game['genres']:
                            if isinstance(genre, dict) and genre.get('name') and genre['name'] not in allGenres:
                                allGenres.append(genre['name'])
                
                selectedGenres = None
                if allGenres:
                    allGenres.sort()
                    selectedGenres = st.multiselect(
                        "Filter by Genre:",
                        options=allGenres,
                        default=None
                    )
        
        chartData = makeChart(st.session_state.chart_games, minRating, maxRating, selectedGenres)
        
        if chartData is not None:
            st.bar_chart(chartData, height=max(400, len(chartData) * 40))
            
            st.markdown("---")
            st.subheader("Added Games")
            
            for idx, game in enumerate(st.session_state.chart_games):
                colG1, colG2, colG3, colG4 = st.columns([3, 1, 1, 1])
                
                with colG1:
                    st.write(f"**{game.get('name', 'Unknown')}**")
                with colG2:
                    st.write(f"⭐ {game.get('rating', 0):.1f}")
                with colG3:
                    if 'first_release_date' in game:
                        from datetime import datetime
                        year = datetime.fromtimestamp(game['first_release_date']).year
                        st.write(f"📅 {year}")
                with colG4:
                    if st.button("❌", key=f"remove_{idx}", use_container_width=True):
                        st.session_state.chart_games.pop(idx)
                        st.rerun()
        else:
            st.info("No games match the current filters. Adjust your filter settings.")
    
    st.markdown("---")

    colSearch, colClear = st.columns([4, 1])
    
    with colSearch:
        searchQuery = st.text_input("Search to add more games or view details:", placeholder="e.g., The Legend of Zelda, God of War, Elden Ring...")
    
    with colClear:
        st.write("")
        st.write("")
        if st.button("🔄 Reset Chart", use_container_width=True):
            with st.spinner("Resetting to default games..."):
                st.session_state.chart_games = fetchInitialGames()
            st.rerun()
    
    if searchQuery:
        with st.spinner(f"Searching for '{searchQuery}'..."):
            searchResults = searchGame(searchQuery)
        
        if searchResults:            
            if len(searchResults) > 1:
                gameNames = [g.get('name', 'Unknown') for g in searchResults]
                selectedGameName = st.selectbox("Multiple games found. Select one:", options=gameNames)
                
                selectedGame = None
                for game in searchResults:
                    if game.get('name') == selectedGameName:
                        selectedGame = game
                        break
            else:
                selectedGame = searchResults[0]
            
            if selectedGame and 'rating' in selectedGame:
                alreadyAdded = any(g.get('name') == selectedGame.get('name') for g in st.session_state.chart_games)
                
                if not alreadyAdded:
                    if st.button("Add to Comparison Chart", use_container_width=True, type="primary"):
                        if 'genres' not in selectedGame:
                            selectedGame['genres'] = []
                        st.session_state.chart_games.append(selectedGame)
                        st.rerun()
            
            if selectedGame:
                gameDetails(selectedGame)
        else:
            st.error(f"No games found matching \"{searchQuery}\". Try a different search term.")


# Main game logic for higher or lower
def higherOrLowerGame():
    if not st.session_state.get("game_started", False):
        showSetupScreen()
        return

    if st.session_state.get("game_over", False):
        showGameOverScreen()
        return

    if "time_left" not in st.session_state:
        duration = st.session_state.get("selected_duration")
        if duration:
            st.session_state.time_left = duration
            st.session_state.last_update = time.time()
        else:
            st.session_state.time_left = None

    timerShouldRefresh = False
    if st.session_state.time_left is not None:
        currentTime = time.time()
        elapsed = currentTime - st.session_state.last_update
        st.session_state.time_left -= elapsed
        st.session_state.last_update = currentTime

        if st.session_state.time_left > 0:
            mins = int(st.session_state.time_left) // 60
            secs = int(st.session_state.time_left) % 60
            st.markdown(f"### Time left: {mins:02d}:{secs:02d}")
            timerShouldRefresh = True
        else:
            st.session_state.game_over = True
            st.session_state.game_over_reason = "time"
            st.rerun()
    else:
        st.markdown("### ♾️ No time limit ♾️")

    if "games" not in st.session_state:
        st.session_state.games = fetchGames()
        
        if len(st.session_state.games) < 2:
            st.error("❌ Unable to fetch enough games from the API. Please check your API credentials or try again later.")
            st.stop()
        
        st.session_state.index = 0
        st.session_state.score = 0
        st.session_state.current = st.session_state.games[0]
        st.session_state.next = st.session_state.games[1]

    currentGame = st.session_state.current
    nextGame = st.session_state.next

    st.write(f"**Score: {st.session_state.score}**")
    st.markdown("---")

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Current Game")
        st.image(get_cover_url(currentGame), width=250)
        st.subheader(currentGame.get("name", "Unknown Game"))
        st.write(f"⭐ **Rating: {currentGame.get('rating', 0):.1f}**")
        if currentGame.get("summary"):
            st.write(currentGame.get("summary"))
    
    with col2:
        st.markdown("### Next Game")
        st.image(get_cover_url(nextGame), width=250)
        st.subheader(nextGame.get("name", "Unknown Game"))
        st.write("**Do you think this game has a higher or lower rating according to experts?**")
        
        if nextGame.get("summary"):
            st.write(nextGame.get("summary"))
        
        st.markdown("---")
        
        if st.button("🔺 Higher", use_container_width=True):
            makeGuess(True)
        if st.button("🔻 Lower", use_container_width=True):
            makeGuess(False)

    if timerShouldRefresh:
        time.sleep(2)
        st.rerun()


# Main script entry
def main():
    st.title("The Video Game Index")

    st.markdown("---")
    st.header("🔍 Game Search & Ratings Comparison")
    searchAndGraph()
    
    st.markdown("---")
    st.header("🎮 Higher or Lower Game")
    higherOrLowerGame()


if __name__ == "__main__":
    main()
