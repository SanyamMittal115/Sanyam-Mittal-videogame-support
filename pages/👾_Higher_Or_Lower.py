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
        return games
        # print(f"Got {len(games)} games from range {minRating}-{maxRating}") 
    except:
        st.error(f"Error searching for game. Ask Sneh or Sunny because their API may have rate limits or authentication issues.")
        return []
    
    # print(f"Total games fetched: {len(allGames)}")
    return allGames

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
            if results and 'rating' in results[0]:
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
        # Game cover image
        if 'cover' in game and 'url' in game['cover']:
            coverUrl = "https:" + game['cover']['url'].replace('t_thumb', 't_cover_big')
            st.image(coverUrl, use_container_width=True)
        else:
            st.info("No cover image available")
    
    with col2:
        # Game title at top
        st.subheader(game['name'])
        
        # Show expert rating if available
        if 'rating' in game:
            st.metric("Expert Rating", f"{game['rating']:.1f}/100")
        
        # Show user rating maybe
        if 'aggregated_rating' in game:
            st.metric("User Rating", f"{game['aggregated_rating']:.1f}/100")
        
        # List all the genres
        if 'genres' in game:
            genresList = []
            for g in game['genres']:
                if 'name' in g:
                    genresList.append(g['name'])
            genreString = ""
            for genre in genresList:
                genreString += genre + ", "
            genreString = genreString[:-2] 
            if genreString:
                st.write(f"**Genres:** {genreString}")
        
        # List companies involved
        if 'involved_companies' in game:
            companiesList = []
            for ic in game['involved_companies']:
                if 'company' in ic and 'name' in ic['company']:
                    companiesList.append(ic['company']['name'])
            companyString = ""
            for company in companiesList:
                companyString += company + ", "
            companyString = companyString[:-2]
            if companyString:
                st.write(f"**Companies:** {companyString}")
        
        # Release date
        if 'first_release_date' in game:
            from datetime import datetime  # importing here bc im lazy to put at top
            releaseDate = datetime.fromtimestamp(game['first_release_date'])  # IGDB gives POSIX timestamp so convert to readable format
            st.write(f"**Release Date:** {releaseDate.strftime('%B %d, %Y')}")
        
        # What platforms its on
        if 'platforms' in game:
            platforms = []
            for p in game['platforms']:
                if 'name' in p:
                    platforms.append(p['name'])
            platformString = ""
            for platform in platforms:
                platformString += platform + ", "
            platformString = platformString[:-2]
            if platformString:
                st.write(f"**Platforms:** {platformString}")
    
    # Game description at the bottom
    if 'summary' in game:
        st.write(f"**Summary:**")
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
        # Save chart games before clearing
        savedChartGames = st.session_state.get('chart_games', [])
        
        # Clear everything
        st.session_state.clear()
        
        # Restore chart games so they don't reload
        st.session_state.chart_games = savedChartGames
        st.rerun()

# Setup screen before game starts - choose time limit
def showSetupScreen():
    st.markdown("### How long do you want to play?")
    st.markdown("---")
    
    # Center everything with columns
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Slider for time (30 sec to 5 min)
        selectedMinutes = st.slider(
            "Game duration (minutes):",
            min_value=0.5,
            max_value=5.0,
            value=2.0,
            step=0.5,
            format="%.1f"
        )
        
        # Convert minutes to seconds for easier handling later
        selectedSeconds = int(selectedMinutes * 60)
        
        # Display time in nice format
        if selectedMinutes < 1:
            timeDisplay = f"{selectedSeconds} seconds"
        elif selectedMinutes == 1:
            timeDisplay = "1 minute"
        else:
            timeDisplay = f"{selectedMinutes:.1f} minutes"
        
        st.write(f"**Selected time: {timeDisplay}**")
        
        # Option for no time limit
        noLimit = st.checkbox("♾️ No time limit ♾️")
        
        st.markdown("---")
        
        # Start game button
        if st.button("🚀 Start Game 🚀", use_container_width=True, type="primary"):
            st.session_state.game_started = True
            if noLimit:
                st.session_state.selected_duration = None
            else:
                st.session_state.selected_duration = selectedSeconds
            st.rerun()


# Creates a bar chart based on the games list with filters
def makeChart(gamesList, minRating=0, maxRating=100, selectedGenres=None):
    if not gamesList:
        return None
    
    # Build lists for chart
    names = []
    ratings = []
    
    for game in gamesList:
        # Check rating range
        gameRating = game['rating']
        if gameRating < minRating or gameRating > maxRating:
            continue
        
        # Check genre filter
        shouldInclude = True
        if selectedGenres:
            shouldInclude = False
            if 'genres' in game:
                for genre in game.get('genres', []):
                    if genre['name'] in selectedGenres:
                        shouldInclude = True
                        break
        
        if shouldInclude:
            names.append(game['name'])
            ratings.append(gameRating)
    
    # Return None if no games passed filters
    if len(names) == 0:
        return None
    
    # Make the dataframe
    df = pd.DataFrame({'Game': names, 'Rating': ratings})
    df = df.sort_values('Rating')
    df = df.set_index('Game')
    return df


# This function grabs games from IGDB for the higher/lower game
def fetchGames():
    allGames = []
    
    # Different rating ranges so we get variety
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
            # print(f"Got {len(games)} games from range {minRating}-{maxRating}") 
            
            for game in games:
                allGames.append(game)
            
        except:
            st.error(f"Whoops. There was an error fetching games for the rating range {minRating}-{maxRating}.")
            continue
    
    # Make sure we actually got enough games to play with
    if len(allGames) < 2:
        st.error(f"Not enough games fetched. Only got {len(allGames)} games. Ask Sneh or Sunny because their API may have rate limits or authentication issues.")
        return []
    
    # print(f"Total games fetched: {len(allGames)}")
    return allGames


# Check if guess was right or wrong
def makeGuess(higherGuess):
    currentGame = st.session_state.current
    nextGame = st.session_state.next
    
    # Did they guess right?
    actuallyHigher = nextGame["rating"] > currentGame["rating"]
    isCorrect = actuallyHigher == higherGuess

    if isCorrect:
        # add point and continue
        st.session_state.score += 1
        st.success(f"✅ Correct! {nextGame['name']} has a rating of {nextGame['rating']:.1f}")
    else:
        # game over
        st.session_state.game_over = True
        st.session_state.game_over_reason = "wrong"
        st.session_state.last_game_info = {
            "name": nextGame["name"],
            "rating": nextGame["rating"]
        }
        time.sleep(1)
        st.rerun()
        return

    # Move to next game
    st.session_state.index += 1
    st.session_state.current = nextGame
    
    # Check if we ran out of games
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

    # Only show bar graph if we have games
    if st.session_state.chart_games:
        st.subheader(f"📊 Game Ratings Comparison")
        
        # Filter section
        with st.expander("Filters", expanded=False):
            colF1, colF2 = st.columns(2)
            
            with colF1:
                # Rating slider
                minRating, maxRating = st.slider(
                    "Rating Range:",
                    min_value=0.0,
                    max_value=100.0,
                    value=(0.0, 100.0),
                    step=1.0
                )
            
            with colF2:
                # Get all unique genres
                allGenres = []
                for game in st.session_state.chart_games:
                    if 'genres' in game:
                        for genre in game['genres']:
                            if genre['name'] not in allGenres:
                                allGenres.append(genre['name'])
                
                selectedGenres = None
                if allGenres:
                    allGenres.sort()
                    selectedGenres = st.multiselect(
                        "Filter by Genre:",
                        options=allGenres,
                        default=None
                    )
                else:
                    selectedGenres = None
        
        # Make chart with filters
        chartData = makeChart(st.session_state.chart_games, minRating, maxRating, selectedGenres)
        
        if chartData is not None:
            st.bar_chart(chartData, height=max(400, len(chartData) * 40))
            
            # List of games with delete buttons
            st.markdown("---")
            st.subheader("Added Games")
            
            for idx, game in enumerate(st.session_state.chart_games):
                colG1, colG2, colG3, colG4 = st.columns([3, 1, 1, 1])
                
                with colG1:
                    st.write(f"**{game['name']}**")
                with colG2:
                    st.write(f"⭐ {game['rating']:.1f}")
                with colG3:
                    if 'first_release_date' in game:
                        from datetime import datetime
                        year = datetime.fromtimestamp(game['first_release_date']).year
                        st.write(f"📅 {year}")
                with colG4:
                    # Delete button for each game from the list of games
                    if st.button("❌", key=f"remove_{idx}", use_container_width=True):
                        st.session_state.chart_games.pop(idx)
                        st.rerun()
        else:
            st.info("No games match the current filters. Adjust your filter settings.")
    
    st.markdown("---")

    # Search bar and reset button
    colSearch, colClear = st.columns([4, 1])
    
    with colSearch:
        searchQuery = st.text_input("Search to add more games or view details:", placeholder="e.g., The Legend of Zelda, God of War, Elden Ring...")
    
    with colClear:
        st.write("")  # spacing
        st.write("")  # more spacing (otherwise button looks weird)
        if st.button("🔄 Reset Chart", use_container_width=True):
            with st.spinner("Resetting to default games..."):
                st.session_state.chart_games = fetchInitialGames()
            st.rerun()
    
    # If user typed something, search for it
    if searchQuery:
        with st.spinner(f"Searching for '{searchQuery}'..."):
            searchResults = searchGame(searchQuery)
        
        if searchResults:            
            # Let user pick if multiple results
            if len(searchResults) > 1:
                gameNames = []
                for game in searchResults:
                    gameNames.append(game['name'])
                
                selectedGameName = st.selectbox("Multiple games found. Select one:", options=gameNames )
                
                # Find which game they selected
                selectedGame = None
                for game in searchResults:
                    if game['name'] == selectedGameName:
                        selectedGame = game
                        break
            else:
                selectedGame = searchResults[0]
            
            # Button to add to chart
            if 'rating' in selectedGame:
                # Check if its already in the chart
                alreadyAdded = False
                for g in st.session_state.chart_games:
                    if g['name'] == selectedGame['name']:
                        alreadyAdded = True
                        break
                
                if alreadyAdded:
                    pass  # dont show add button
                else:
                    if st.button("Add to Comparison Chart", use_container_width=True, type="primary"):
                        if 'genres' not in selectedGame:
                            selectedGame['genres'] = []
                        st.session_state.chart_games.append(selectedGame)
                        st.rerun()
            
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

    # Setup timer stuff
    if "time_left" not in st.session_state:
        duration = st.session_state.get("selected_duration")
        if duration:
            st.session_state.time_left = duration
            st.session_state.last_update = time.time()
        else:
            st.session_state.time_left = None

    # Update timer countdown
    timerShouldRefresh = False
    if st.session_state.time_left is not None:
        currentTime = time.time()
        elapsed = currentTime - st.session_state.last_update
        st.session_state.time_left -= elapsed
        st.session_state.last_update = currentTime

        # show timer or end game if time ran out
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

    # Load games for the first time
    if "games" not in st.session_state:
        st.session_state.games = fetchGames()
        
        # Make sure we got enough games
        if len(st.session_state.games) < 2:
            st.error("❌ Unable to fetch enough games from the API. Please check your API credentials or try again later.")
            st.stop()
        
        # Set up initial state
        st.session_state.index = 0
        st.session_state.score = 0
        st.session_state.current = st.session_state.games[0]
        st.session_state.next = st.session_state.games[1]
        # print(f"Starting with {st.session_state.current['name']} vs {st.session_state.next['name']}")

    currentGame = st.session_state.current
    nextGame = st.session_state.next

    st.write(f"**Score: {st.session_state.score}**")
    st.markdown("---")

    # Two column layout for both games
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Current Game")
        st.image("https:" + currentGame["cover"]["url"], width=250)
        st.subheader(currentGame["name"])
        st.write(f"⭐ **Rating: {currentGame['rating']:.1f}**")
        if currentGame.get("summary"):
            st.write(currentGame.get("summary"))
    
    with col2:
        st.markdown("### Next Game")
        st.image("https:" + nextGame["cover"]["url"], width=250)
        st.subheader(nextGame["name"])
        st.write("**Do you think this game has a higher or lower rating according to experts?**")
        
        if nextGame.get("summary"):
            st.write(nextGame.get("summary"))
        
        st.markdown("---")
        
        # Higher and Lower buttons for guessing
        if st.button("🔺 Higher", use_container_width=True):
            makeGuess(True)
        if st.button("🔻 Lower", use_container_width=True):
            makeGuess(False)

    # Refresh timer if needed (do it at the end so game displays first)
    if timerShouldRefresh:
        time.sleep(2)
        st.rerun()


# Main stufffffffffff
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
