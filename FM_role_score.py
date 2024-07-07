import PySimpleGUI as sg
import json
import pandas as pd
from datetime import datetime

sg.theme('DarkAmber')

# Load roles from the JSON file
try:
    with open('player_roles.json', 'r') as file:
        roles_data = json.load(file)
except FileNotFoundError:
    sg.popup_error("Error: The file 'player_roles.json' was not found.")
    roles_data = {}
except json.JSONDecodeError:
    sg.popup_error("Error: The file 'player_roles.json' is not a valid JSON.")
    roles_data = {}
except Exception as e:
    sg.popup_error(f"An unexpected error occurred: {e}")
    roles_data = {}

# Create layout for the left side (checkboxes)
left_layout = []
for category, roles in roles_data.items():
    left_layout.append([sg.Text(category, font=("Arial", 12, "bold"))])
    for role in roles:
        left_layout.append([sg.Checkbox(role['role'], key=role['role_abbr'])])

# Create a scrollable column for the left side (roles)
left_column = sg.Column(left_layout, scrollable=True, vertical_scroll_only=True, size=(300, 400))

# Create layout for the right side (buttons and dropdown)
right_layout = [
    [sg.Button("Import", size=(15, 2), font=("Arial", 12))],
    [sg.Button("Calculate Selected", size=(15, 2), font=("Arial", 12))],
    [sg.Button("Save", size=(15, 2), font=("Arial", 12))],
    [sg.Combo(['-ALL-'], default_value='-ALL-', size=(18, 1), key='division_dropdown', readonly=True, enable_events=True)]
]

# Combine left and right layouts
layout = [
    [left_column, sg.VSeparator(), sg.Column(right_layout, vertical_alignment='top')]
]

# Create the window
window = sg.Window("FM Role Score Calculator", layout)

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
            window['division_dropdown'].update(values=['-ALL-'] + unique_divisions, value='-ALL-')
            sg.popup('Table Imported and Transformed')
            return df
        except Exception as e:
            sg.popup_error(f"Error importing table: {e}")
    return None

# Helper function to calculate scores
def calculate_scores(df, selected_roles, selected_division, roles_data):
    scores_dict = {}
    for category, roles_info in roles_data.items():
        for role_info in roles_info:
            role_abbr = role_info['role_abbr']
            if role_abbr in selected_roles:
                total_multiplier = sum(role_info[attr] for attr in role_info if attr not in ['role', 'role_abbr'])
                scores = [
                    (
                        player['Name'], player['Age'], player['Position'], player['Club'], player['Division'],
                        player['Height'], player['Weight'], player['Preferred Foot'],
                        sum(player[attr] * role_info[attr] for attr in role_info if attr not in ['role', 'role_abbr']) / total_multiplier
                    )
                    for _, player in df.iterrows() if selected_division == '-ALL-' or player['Division'] == selected_division
                ]
                sorted_scores = sorted(scores, key=lambda x: x[8], reverse=True)
                if sorted_scores:
                    top_score = sorted_scores[0][8]
                    scores_dict[role_info['role']] = [(player + (100 * ((top_score - player[8]) / top_score) if top_score else 0,)) for player in sorted_scores[:10]]
    return scores_dict

# Helper function to save scores
def save_scores(df, roles_data, selected_roles, selected_division):
    scores = calculate_scores(df, selected_roles, selected_division, roles_data)
    for role, players in scores.items():
        file_name = f"{role.lower()}_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.csv"
        pd.DataFrame(players, columns=["Name", "Age", "Position", "Club", "Division", "Height", "Weight", "Preferred Foot", "Score", "Diff to 1st (%)"]).to_csv(file_name, index=False)
        sg.popup(f"Saved {role} scores to {file_name}")

# Helper function to display scores
def display_scores(scores):
    display_text = "\n".join(
        f"{role}:\n{'Name':<25} {'Age':<5} {'Position':<10} {'Club':<25} {'Division':<15} {'Height':<7} {'Weight':<7} {'Preferred Foot':<15} {'Score':<5} {'Diff to 1st (%)':<5}\n"
        + "-" * 140 + "\n" + "\n".join(
            f"{player[0]:<25} {player[1]:<5} {player[2]:<10} {player[3]:<25} {player[4]:<15} {player[5]:<7} {player[6]:<7} {player[7]:<15} {player[8]:.2f} {player[9]:.2f}"
            for player in players) + "\n"
        for role, players in scores.items())
    sg.popup_scrolled("Top 10 Players for Each Role", display_text, size=(100, 30))

df = None
while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break
    elif event == "Import":
        df = import_html_table()
    elif event == "Calculate Selected":
        if df is not None:
            selected_roles = [role for role, selected in values.items() if selected]
            selected_division = values['division_dropdown']
            scores = calculate_scores(df, selected_roles, selected_division, roles_data)
            display_scores(scores)
    elif event == "Save":
        if df is not None:
            selected_roles = [role for role, selected in values.items() if selected]
            selected_division = values['division_dropdown']
            save_scores(df, roles_data, selected_roles, selected_division)

window.close()
