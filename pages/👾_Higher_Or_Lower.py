import streamlit as st
import requests
import random
import time
import pandas as pd

# --- IGDB Setup ---
CLIENT_ID = st.secrets["CLIENT_ID"] 
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]

headers = {
    "Client-ID": CLIENT_ID,
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

# --- Get Games from IGDB API for Higher or Lower Game ---
def fetch_games():
    all_games = []
    
    # Get games from different rating ranges to ensure variety
    rating_ranges = [
        (20, 40), 
        (40, 60),   
        (60, 80),   
        (80, 100)   
    ]
    
    for min_rating, max_rating in rating_ranges:
        random_offset = random.randint(0, 2000)
        
        query = f"""
        fields name, rating, cover.url, summary;
        where rating != null & cover != null & rating >= {min_rating} & rating <= {max_rating};
        limit 5;
        offset {random_offset};
        """
        
        try:
            # Have to use POST request to send the query to IGDB API instead of GET
            response = requests.post("https://api.igdb.com/v4/games", headers=headers, data=query)
            games = response.json()
            
            all_games.extend(games)
            
        except:
            st.error(f"Whoops. There was an error fetching games for the rating range {min_rating}-{max_rating}.")
            continue
    
    if len(all_games) < 2:
        st.error(f"Not enough games fetched. Only got {len(all_games)} games. Ask Sneh or Sunny because their API may have rate limits or authentication issues.")
        return []
    
    return all_games

# --- Get Initial Games for Chart ---
def fetch_initial_games():
    # Get games for initial chart data
    game_names = ["Grand Theft Auto V", "Minecraft", "Rocket League", "The Legend of Zelda: Breath of the Wild", "The Last of Us", "The Sims 4", "Rainbow Six Siege", "Fortnite", "Overwatch", "League of Legends", "Valorant", "Mario Hotel", "Bubsy 3D"]
    games = []
    
    for game_name in game_names:
        query = f"""
        search "{game_name}";
        fields name, rating, cover.url, summary, genres.name, involved_companies.company.name, 
               first_release_date, platforms.name, aggregated_rating, aggregated_rating_count;
        limit 1;
        """
        
        try:
            response = requests.post("https://api.igdb.com/v4/games", headers=headers, data=query)
            results = response.json()
            if results and 'rating' in results[0]:
                games.append(results[0])
        except:
            continue
    
    return games

# --- Create a bar chart from the list of added games with filters applied ---
def create_comparison_chart(games_list, min_rating=0, max_rating=100, selected_genres=None):
    if not games_list:
        return None
    
    filtered_games = []
    for game in games_list:
        # Filter by rating
        if game['rating'] < min_rating or game['rating'] > max_rating:
            continue
        
        # Filter by genre
        if selected_genres:
            game_genres = []
            for genre in game.get('genres', []):
                game_genres.append(genre['name'])
            
            # Check if at least one selected genre matches
            genre_found = False
            for genre in selected_genres:
                if genre in game_genres:
                    genre_found = True
                    break
            
            if not genre_found:
                continue
        
        filtered_games.append(game)
    
    if not filtered_games:
        return None
    
    # Bar graph data stuff
    game_names = []
    game_ratings = []
    for game in filtered_games:
        game_names.append(game['name'])
        game_ratings.append(game['rating'])
    
    bar = pd.DataFrame({
        'Game': game_names,
        'Rating': game_ratings
    })
    
    bar = bar.sort_values('Rating')
    bar = bar.set_index('Game')
    
    return bar


# --- Search for specific game ---
def search_game(game_name):
    query = f"""
    search "{game_name}";
    fields name, rating, cover.url, summary, genres.name, involved_companies.company.name, 
           first_release_date, platforms.name, aggregated_rating, aggregated_rating_count;
    limit 20;
    """
    
    try:
        response = requests.post("https://api.igdb.com/v4/games", headers=headers, data=query)
        games = response.json()
        return games
    except:
        st.error(f"Error searching for game. Ask Sneh or Sunny because their API may have rate limits or authentication issues.")
        return []


# --- Display game details ---
def display_game_details(game):
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Display cover image
        if 'cover' in game and 'url' in game['cover']:
            cover_url = "https:" + game['cover']['url'].replace('t_thumb', 't_cover_big')
            st.image(cover_url, use_container_width=True)
        else:
            st.info("No cover image available")
    
    with col2:
        # Display game title
        st.subheader(game['name'])
        
        # Display rating
        if 'rating' in game:
            st.metric("Expert Rating", f"{game['rating']:.1f}/100")
        
        if 'aggregated_rating' in game:
            st.metric("User Rating", f"{game['aggregated_rating']:.1f}/100")
        
        # Display genres
        if 'genres' in game:
            genres = []
            for g in game['genres']:
                if 'name' in g:
                    genres.append(g['name'])
            genre_str = ""
            for genre in genres:
                genre_str += genre + ", "
            genre_str = genre_str[:-2]
            if genre_str:
                st.write(f"**Genres:** {genre_str}")
        
        # Display companies
        if 'involved_companies' in game:
            companies = []
            for ic in game['involved_companies']:
                if 'company' in ic and 'name' in ic['company']:
                    companies.append(ic['company']['name'])
            company_str = ""
            for company in companies:
                company_str += company + ", "
            company_str = company_str[:-2]
            if company_str:
                st.write(f"**Companies:** {company_str}")
        
        # Display release date
        if 'first_release_date' in game:
            from datetime import datetime # too lazy to move to top hahaha
            release_date = datetime.fromtimestamp(game['first_release_date']) # API provides timestamp in POSIX time so convert readable format
            st.write(f"**Release Date:** {release_date.strftime('%B %d, %Y')}")
        
        # Display platforms
        if 'platforms' in game:
            platforms = []
            for p in game['platforms']:
                if 'name' in p:
                    platforms.append(p['name'])
            platform_str = ""
            for platform in platforms:
                platform_str += platform + ", "
            platform_str = platform_str[:-2]
            if platform_str:
                st.write(f"**Platforms:** {platform_str}")
    
    # Display summary
    if 'summary' in game:
        st.write(f"**Summary:**")
        st.write(game['summary'])

# --- Display the game over screen with final score and play again option ---
def show_game_over_screen():
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
    
    if st.button("🎮 Play Again", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- Display hero screen where user can choose game duration and press play ---
def show_setup_screen():
    st.markdown("### How long do you want to play?")
    st.markdown("---")
    
    # Center the slider and button using columns
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Time slider (15 seconds to 5 minutes)
        selected_minutes = st.slider(
            "Game duration (minutes):",
            min_value=0.5,
            max_value=5.0,
            value=2.0,
            step=0.5,
            format="%.1f"
        )
        
        # Convert to seconds
        selected_seconds = int(selected_minutes * 60)
        
        # Show formatted time
        if selected_minutes < 1:
            time_display = f"{selected_seconds} seconds"
        elif selected_minutes == 1:
            time_display = "1 minute"
        else:
            time_display = f"{selected_minutes:.1f} minutes"
        
        st.write(f"**Selected time: {time_display}**")
        
        # No time limit option
        no_limit = st.checkbox("♾️ No time limit ♾️")
        
        st.markdown("---")
        
        if st.button("🚀 Start Game 🚀", use_container_width=True, type="primary"):
            st.session_state.game_started = True
            if no_limit:
                st.session_state.selected_duration = None
            else:
                st.session_state.selected_duration = selected_seconds
            st.rerun()

# --- Display the game search and comparison chart section ---
def display_search_and_graph():
    if 'chart_games' not in st.session_state:
        with st.spinner("Loading initial games..."):
            st.session_state.chart_games = fetch_initial_games()

    # Display bar graph if games exist
    if st.session_state.chart_games:
        st.subheader(f"📊 Game Ratings Comparison")
        
        # Filters Section
        with st.expander("Filters", expanded=False):
            col_f1, col_f2 = st.columns(2)
            
            with col_f1:
                # Rating range filter
                min_rating, max_rating = st.slider(
                    "Rating Range:",
                    min_value=0.0,
                    max_value=100.0,
                    value=(0.0, 100.0),
                    step=1.0
                )
            
            with col_f2:
                # Genre filter
                all_genres = []
                for game in st.session_state.chart_games:
                    if 'genres' in game:
                        for genre in game['genres']:
                            if genre['name'] not in all_genres:
                                all_genres.append(genre['name'])
                
                if all_genres:
                    all_genres.sort()
                    selected_genres = st.multiselect(
                        "Filter by Genre:",
                        options=all_genres,
                        default=None
                    )
                else:
                    selected_genres = None
        
        # Create and display chart
        if selected_genres:
            chart_data = create_comparison_chart(st.session_state.chart_games, min_rating, max_rating, selected_genres)
        else:
            chart_data = create_comparison_chart(st.session_state.chart_games, min_rating, max_rating, None)
        
        if chart_data is not None:
            st.bar_chart(chart_data, height=max(400, len(chart_data) * 40))
            
            # List of added games with remove option
            st.markdown("---")
            st.subheader("Added Games")
            
            for idx, game in enumerate(st.session_state.chart_games):
                col_g1, col_g2, col_g3, col_g4 = st.columns([3, 1, 1, 1])
                
                with col_g1:
                    st.write(f"**{game['name']}**")
                with col_g2:
                    st.write(f"⭐ {game['rating']:.1f}")
                with col_g3:
                    if 'first_release_date' in game:
                        from datetime import datetime
                        year = datetime.fromtimestamp(game['first_release_date']).year
                        st.write(f"📅 {year}")
                with col_g4:
                    if st.button("❌", key=f"remove_{idx}", use_container_width=True):
                        st.session_state.chart_games.pop(idx)
                        st.rerun()
        else:
            st.info("No games match the current filters. Adjust your filter settings.")
    
    st.markdown("---")


    # Search and add games
    col_search, col_clear = st.columns([4, 1])
    
    with col_search:
        search_query = st.text_input(
            "Search to add more games or view details:",
            placeholder="e.g., The Legend of Zelda, God of War, Elden Ring..."
        )
    
    with col_clear:
        st.write("")  # Spacing
        st.write("")  # Spacing again b/c for some reason the button is not centered without it
        if st.button("🔄 Reset Chart", use_container_width=True):
            with st.spinner("Resetting to default games..."):
                st.session_state.chart_games = fetch_initial_games()
            st.rerun()
    
    if search_query:
        with st.spinner(f"Searching for '{search_query}'..."):
            search_results = search_game(search_query)
        
        if search_results:            
            # If multiple results, let user choose
            if len(search_results) > 1:
                game_names = []
                for game in search_results:
                    game_names.append(game['name'])
                
                selected_game_name = st.selectbox(
                    "Multiple games found. Select one:",
                    options=game_names
                )
                
                # Find the selected game
                selected_game = None
                for game in search_results:
                    if game['name'] == selected_game_name:
                        selected_game = game
                        break
            else:
                selected_game = search_results[0]
            
            # Add to Chart button
            if 'rating' in selected_game:
                # Check if already added
                already_added = False
                for g in st.session_state.chart_games:
                    if g['name'] == selected_game['name']:
                        already_added = True
                        break
                
                if already_added:
                    pass
                else:
                    if st.button("Add to Comparison Chart", use_container_width=True, type="primary"):
                        # Make sure it has the necessary fields for the chart
                        if 'genres' not in selected_game:
                            # Fetch genres if not present
                            selected_game['genres'] = []
                        st.session_state.chart_games.append(selected_game)
                        st.rerun()
            
            display_game_details(selected_game)
        else:
            st.error(f"No games found matching \"{search_query}\". Try a different search term.")


# --- Higher or Lower game logic section ---
def play_higher_or_lower_game():
    # Show setup screen if game hasn't started
    if not st.session_state.get("game_started", False):
        show_setup_screen()
        return

    # Check if game is over
    if st.session_state.get("game_over", False):
        show_game_over_screen()
        return

    # Initialize timer
    if "time_left" not in st.session_state:
        duration = st.session_state.get("selected_duration")
        if duration is not None:
            st.session_state.time_left = duration
            st.session_state.last_update = time.time()
        else:
            # No time limit
            st.session_state.time_left = None

    # Update and display timer (only if time limit is set)
    if st.session_state.time_left is not None:
        current_time = time.time()
        st.session_state.time_left -= (current_time - st.session_state.last_update) # Subtract elapsed time
        st.session_state.last_update = current_time

        # Display timer
        if st.session_state.time_left > 0:
            mins = int(st.session_state.time_left) // 60
            secs = int(st.session_state.time_left) % 60
            st.markdown(f"### Time left: {mins:02d}:{secs:02d}")
        else:
            st.session_state.game_over = True
            st.session_state.game_over_reason = "time"
            st.rerun()
    else:
        st.markdown("### ♾️ No time limit ♾️")

    if "games" not in st.session_state:
        # Gets games and stores them in session state for the game
        st.session_state.games = fetch_games()
        
        # Check if we have enough games
        if len(st.session_state.games) < 2:
            st.error("❌ Unable to fetch enough games from the API. Please check your API credentials or try again later.")
            st.stop()
        
        # Start with the first two games in the list of random games for the initial state
        st.session_state.index = 0
        st.session_state.score = 0
        st.session_state.current = st.session_state.games[0]
        st.session_state.next = st.session_state.games[1]

    current = st.session_state.current
    next_game = st.session_state.next

    st.write(f"**Score: {st.session_state.score}**")
    st.markdown("---")

    # Display current and next game side by side with columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Current Game")
        st.image("https:" + current["cover"]["url"], width=250)
        st.subheader(current["name"])
        st.write(f"⭐ **Rating: {current['rating']:.1f}**")
        if current.get("summary"):
            st.write(current.get("summary"))
    
    with col2:
        st.markdown("### Next Game")
        st.image("https:" + next_game["cover"]["url"], width=250)
        st.subheader(next_game["name"])
        st.write("**Do you think this game has a higher or lower rating according to experts?**")
        
        if next_game.get("summary"):
            st.write(next_game.get("summary"))
        
        st.markdown("---")
        
        # Buttons for guessing
        if st.button("🔺 Higher", use_container_width=True):
            guess(True)
        if st.button("🔻 Lower", use_container_width=True):
            guess(False)

    # Auto-refresh every half a second to update timer
    time.sleep(0.5)
    st.rerun()

def guess(higher):
    current = st.session_state.current
    next_game = st.session_state.next
    correct = (next_game["rating"] > current["rating"]) == higher

    if correct:
        st.session_state.score += 1
        st.success(f"✅ Correct! {next_game['name']} has a rating of {next_game['rating']:.1f}")
    else:
        # Set game over state
        st.session_state.game_over = True
        st.session_state.game_over_reason = "wrong"
        st.session_state.last_game_info = {
            "name": next_game["name"],
            "rating": next_game["rating"]
        }
        time.sleep(1)
        st.rerun()
        return

    st.session_state.index += 1
    st.session_state.current = next_game
    
    # Check if we have more games
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


# --- Main Application ---
def main():
    st.title("The Video Game Index")

    st.markdown("---")
    st.header("🔍 Game Search & Ratings Comparison")
    display_search_and_graph()
    
    st.markdown("---")
    st.header("🎮 Higher or Lower Game")
    play_higher_or_lower_game()


if __name__ == "__main__":
    main()
