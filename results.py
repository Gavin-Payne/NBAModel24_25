from nba_api.live.nba.endpoints import scoreboard, boxscore

games = scoreboard.ScoreBoard()

dict_data = games.get_dict()

for game in dict_data['scoreboard']['games']:
    game_id = game['gameId']
    game_status = game['gameStatus']
    game_boxscore = boxscore.BoxScore(game_id)
    boxscore_data = game_boxscore.get_dict()
    
    status_text = "Finished" if game_status == 3 else "Not Finished"
    print(f"Game ID: {game_id}, Status: {status_text}")
    
    for player in boxscore_data['game']['homeTeam']['players']:
        print(f"Home Player: {player['name']}, Stats: {player['statistics']}")
    for player in boxscore_data['game']['awayTeam']['players']:
        print(f"Away Player: {player['name']}, Stats: {player['statistics']}")