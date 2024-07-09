import PySimpleGUI as sg
import json
import pandas as pd
from datetime import datetime

sg.theme('DarkAmber')

# Function to create layout for GUI
def create_layout():
    layout = [
        [sg.Button("Import HTML", size=(15, 2), font=("Arial", 12))],
        [sg.Text("Select League:", font=("Arial", 12, "bold"))],
        [sg.Combo([], key='league_dropdown', size=(25, 1), readonly=True, enable_events=True)],
        [sg.Text("Select Team:", font=("Arial", 12, "bold"))],
        [sg.Combo([], key='team_dropdown', size=(25, 1), readonly=True)],
        [sg.Checkbox("Don't calculate GK scores", key='exclude_gk')],
        [sg.Button("Calculate", size=(15, 2), font=("Arial", 12))],
        [sg.Multiline(size=(100, 30), key='output', font=("Arial", 10), autoscroll=True)]
    ]
    return layout

# Popup to select JSON file
def import_json():
    json_file_path = sg.popup_get_file('Choose a JSON file', file_types=(("JSON Files", "*.json"),))
    if not json_file_path:
        sg.popup_error("No file selected. Exiting.")
        return None

    # Load roles from the selected JSON file
    try:
        with open(json_file_path, 'r') as file:
            roles_data = json.load(file)
        return roles_data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        sg.popup_error(f"Error: {str(e)}")
        return None

# Helper function to transform values
def transform_value(column, value):
    if column not in ["Inf", "Rec", "Name", "Nat", "Club", "Division", "Position", "Preferred Foot", "Height", "Weight"]:
        return int(value.split('-')[0].strip() or 1) if isinstance(value, str) and '-' in value else int(float(value)) if pd.notna(value) and value != '-' else 1
    elif column in ["Age", "Height", "Weight"]:
        return int(value.split()[0]) if isinstance(value, str) else int(float(value)) if pd.notna(value) else value
    return value

# Helper function to import HTML table
def import_html_table():
    file_path = sg.popup_get_file('Choose an HTML file', file_types=(("HTML Files", "*.html"),))
    if file_path:
        try:
            df = pd.read_html(file_path, encoding='utf-8')[0].dropna(subset=["Name"])
            df = df.apply(lambda x: x.map(lambda v: transform_value(x.name, v)))
            unique_divisions = sorted(df['Division'].dropna().unique().tolist())
            return df, unique_divisions
        except Exception as e:
            sg.popup_error(f"Error importing table: {e}")
    return None, []

# Helper function to calculate scores
def calculate_scores(df, roles_data, selected_team, exclude_gk):
    scores_dict = {}
    df_team = df[df['Club'] == selected_team]

    for category, roles_info in roles_data.items():
        for role_info in roles_info:
            role_abbr = role_info['role_abbr']
            if exclude_gk and role_abbr in ['gkd', 'skd', 'sks', 'ska']:
                continue
            total_multiplier = sum(role_info[attr] for attr in role_info if attr not in ['role', 'role_abbr'])
            df_team[f'{role_abbr}_score'] = df_team.apply(
                lambda player: sum(player[attr] * role_info[attr] for attr in role_info if attr not in ['role', 'role_abbr']) / total_multiplier, axis=1
            )

    return df_team

# Helper function to save scores to CSV
def save_scores_to_csv(df_team):
    current_date = datetime.now().strftime("%Y_%m_%d")
    file_name = f"{current_date}.csv"
    df_team.to_csv(file_name, index=False)
    sg.popup(f"Scores saved to {file_name}")

# Import JSON data at startup
roles_data = import_json()
if roles_data is None:
    exit()

# Create the layout
layout = create_layout()

# Create the window
window = sg.Window("FM Role Score Calculator", layout)

df = None

while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break
    elif event == "Import HTML":
        df, unique_leagues = import_html_table()
        if df is not None:
            window['league_dropdown'].update(values=unique_leagues)
            sg.popup('HTML Table Imported and Transformed Successfully')
    elif event == "league_dropdown":
        selected_league = values['league_dropdown']
        unique_teams = sorted(df[df['Division'] == selected_league]['Club'].dropna().unique().tolist())
        window['team_dropdown'].update(values=unique_teams)
    elif event == "Calculate":
        if df is not None and roles_data is not None:
            selected_team = values['team_dropdown']
            exclude_gk = values['exclude_gk']
            if selected_team:
                team_scores = calculate_scores(df, roles_data, selected_team, exclude_gk)
                save_scores_to_csv(team_scores)
                output_text = team_scores.to_string(index=False)
                window['output'].update(output_text)
            else:
                sg.popup_error("Please select a team.")
        else:
            sg.popup_error("Please import both JSON and HTML data first.")

window.close()
