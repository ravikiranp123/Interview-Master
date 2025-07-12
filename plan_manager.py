import os
import json
import shutil
import glob
from datetime import datetime, timedelta
import click
import re

# --- CONFIGURATION ---

# --- Directory and File Paths ---
# The script assumes it's in the root of the LeetCode_Journey folder.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROBLEM_LISTS_DIR = os.path.join(BASE_DIR, 'problem_lists')
DAILY_PLANS_DIR = os.path.join(BASE_DIR, 'daily_plans')
WORKSPACE_DIR = os.path.join(BASE_DIR, 'workspace')
ARCHIVE_DIR = os.path.join(BASE_DIR, 'archive')
STATE_FILE = os.path.join(BASE_DIR, 'state.json')
DASHBOARD_FILE = os.path.join(BASE_DIR, 'dashboard.md')

# --- Spaced Repetition Schedule ---
# Intervals in days for repeated practice.
REPETITION_INTERVALS = [1, 7, 16, 35, 90]

# --- HELPER FUNCTIONS ---

def get_today_str():
    """Returns today's date as a 'YYYY-MM-DD' string."""
    return datetime.now().strftime('%Y-%m-%d')

def load_state():
    """Loads the state from state.json, returns None if it doesn't exist."""
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_state(state):
    """Saves the given state object to state.json."""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def ensure_dirs():
    """Ensures all necessary directories exist."""
    os.makedirs(PROBLEM_LISTS_DIR, exist_ok=True)
    os.makedirs(DAILY_PLANS_DIR, exist_ok=True)
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

# --- CORE LOGIC FUNCTIONS ---

def generate_dashboard():
    """Generates the dashboard.md file from the current state."""
    state = load_state()
    if not state:
        return

    plan_name = state.get('plan_name', 'Unknown Plan')
    
    # Create a dictionary for quick lookups of problem state by ID
    state_problems_map = {p['id']: p for p in state.get('problems', [])}
    
    # Load the canonical problem list to get the correct order
    plan_file_path = os.path.join(PROBLEM_LISTS_DIR, f"{plan_name.replace(' ', '')}.json")
    try:
        with open(plan_file_path, 'r', encoding='utf-8') as f:
            problem_data = json.load(f)
    except FileNotFoundError:
        click.echo(click.style(f"Dashboard generation skipped: Could not find '{plan_file_path}'", fg="yellow"))
        return

    total_problems = len(state_problems_map)
    completed_problems = sum(1 for p in state_problems_map.values() if p['status'] == 'completed')
    progress_percent = (completed_problems / total_problems * 100) if total_problems > 0 else 0

    content = [f"# LeetCode Journey: {plan_name} Dashboard\n"]
    content.append(f"**Overall Progress: {completed_problems} / {total_problems} ({progress_percent:.1f}%)**\n")
    content.append("---\n")

    # Iterate through the canonical list to preserve order
    for category, problems_in_list in problem_data['categories'].items():
        
        # Calculate category-specific progress
        cat_problem_ids = {p['id'] for p in problems_in_list}
        completed_in_cat = sum(1 for pid in cat_problem_ids if state_problems_map.get(pid, {}).get('status') == 'completed')
        total_in_cat = len(cat_problem_ids)
        content.append(f"### {category} ({completed_in_cat} / {total_in_cat})\n")
        
        # Iterate through problems in the exact order they appear in the JSON file
        for problem_template in problems_in_list:
            p_id = problem_template['id']
            # Get the current state for this problem from our map
            p_state = state_problems_map.get(p_id)
            
            if not p_state: continue # Should not happen in a valid state file

            checkbox = '[x]' if p_state['status'] == 'completed' else '[ ]'
            content.append(f"- {checkbox} {p_state['id']}\\. {p_state['title']}")
            
            # Display full history for completed problems
            if p_state['status'] == 'completed' and p_state['completion_history']:
                for i, entry in enumerate(p_state['completion_history']):
                    date = entry.get('date', 'N/A')
                    notes = entry.get('notes', 'No note recorded.')
                    time = f", {entry.get('time_taken', 'N/A')}" if entry.get('time_taken') else ""
                    content.append(f"  - **Attempt {i+1} ({date}{time}):** {notes}")

        content.append("\n---\n")

    with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))
    click.echo(click.style("Dashboard updated successfully!", fg="green"))

# --- CLI COMMANDS ---

@click.group()
def cli():
    """A command-line tool to manage your LeetCode study plan."""
    ensure_dirs()

@cli.command()
def init():
    """Initializes a new study plan interactively."""
    if os.path.exists(STATE_FILE):
        click.confirm(
            click.style("A 'state.json' file already exists. Continuing will overwrite it. Are you sure?", fg="yellow"),
            abort=True
        )

    # Choose problem list
    available_lists = sorted([f.replace('.json', '') for f in os.listdir(PROBLEM_LISTS_DIR) if f.endswith('.json')])
    if not available_lists:
        click.echo(click.style(f"No problem lists found in '{PROBLEM_LISTS_DIR}'. Please add JSON files for plans.", fg="red"))
        return

    click.echo("Please choose a plan from the list below:")
    for i, name in enumerate(available_lists, 1):
        click.echo(f"  {i}. {name}")
    
    choice = click.prompt("\nEnter the number of your chosen plan", type=int)

    if not 1 <= choice <= len(available_lists):
        click.echo(click.style("Invalid selection. Please run the command again.", fg="red"))
        return
    
    plan_name = available_lists[choice - 1]
    click.echo(f"You have selected: {click.style(plan_name, fg='cyan')}")

    # Get start date
    start_date_str = click.prompt("\nEnter start date (YYYY-MM-DD, leave blank for today)", default=get_today_str(), show_default=False)
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except ValueError:
        click.echo(click.style("Invalid date format. Please use YYYY-MM-DD.", fg="red"))
        return

    # Get problems per day
    problems_per_day = click.prompt("How many new problems per day?", type=int, default=3)

    # Load and schedule problems
    try:
        with open(os.path.join(PROBLEM_LISTS_DIR, f"{plan_name}.json"), 'r', encoding='utf-8') as f:
            problem_data = json.load(f)
    except FileNotFoundError:
        click.echo(click.style(f"Error: Could not find {plan_name}.json.", fg="red"))
        return

    all_problems = []
    current_date = start_date
    day_counter = 0

    # Iterate through categories in the order they appear in the JSON file
    for category, problems in problem_data['categories'].items():
        for problem in problems:
            if day_counter >= problems_per_day:
                current_date += timedelta(days=1)
                day_counter = 0
            
            all_problems.append({
                "id": problem['id'],
                "title": problem['title'],
                "category": category,
                "status": "pending",
                "scheduled_date": current_date.strftime('%Y-%m-%d'),
                "next_repetition_date": None,
                "repetition_level": 0,
                "completion_history": []
            })
            day_counter += 1
            
    state = {"plan_name": problem_data['name'], "problems": all_problems}
    save_state(state)
    generate_dashboard()
    click.echo(click.style(f"\nSuccessfully initialized '{plan_name}' plan!", fg="green"))
    click.echo("Run 'python plan_manager.py plan' to generate your first daily plan.")

@cli.command()
def plan():
    """Generates or refreshes today's study plan."""
    state = load_state()
    if not state:
        click.echo(click.style("No plan initialized. Run 'init' first.", fg="red"))
        return

    today = get_today_str()
    plan_file_path = os.path.join(DAILY_PLANS_DIR, f"{today}.md")

    # Clean the workspace for a fresh start
    for f in os.listdir(WORKSPACE_DIR):
        os.remove(os.path.join(WORKSPACE_DIR, f))
    click.echo(f"Cleaned workspace: '{WORKSPACE_DIR}'")

    # Find tasks for today
    new_tasks = [p for p in state['problems'] if p['status'] == 'pending' and p['scheduled_date'] <= today]
    repetitions = [p for p in state['problems'] if p['status'] == 'completed' and p['next_repetition_date'] == today]
    
    # Generate plan content
    content = [f"# LeetCode Plan for: {today}\n"]
    
    if new_tasks:
        content.append("---\n\n## 🚀 New Problems To Solve\n")
        for task in sorted(new_tasks, key=lambda x: x['scheduled_date']):
            content.append(f"*   [ ] {task['id']}\\. {task['title']} ({task['category']})")
            content.append(f"    *   **Notes**: ")
            content.append(f"    *   **Time Taken**: ")
    else:
        content.append("---\n\n## 🚀 New Problems To Solve\n\n*No new problems scheduled for today. Great job!*")

    if repetitions:
        content.append("\n---\n\n## 🔁 Repetitions Due\n")
        for task in repetitions:
            content.append(f"*   [ ] {task['id']}\\. {task['title']} ({task['category']})")
            content.append(f"    *   **Notes**: ")
            content.append(f"    *   **Time Taken**: ")
    else:
        content.append("\n---\n\n## 🔁 Repetitions Due\n\n*You have no repetitions due today.*")
        
    with open(plan_file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))

    click.echo(click.style(f"Today's plan created at: '{plan_file_path}'", fg="green"))

@cli.command()
def sync():
    """Syncs progress from daily plans back to the main state."""
    state = load_state()
    if not state:
        click.echo(click.style("No plan initialized. Run 'init' first.", fg="red"))
        return

    synced_files = []
    
    for plan_file in glob.glob(os.path.join(DAILY_PLANS_DIR, '*.md')):
        with open(plan_file, 'r', encoding='utf-8') as f:
            content = f.read()

        problems_to_update = {}
        
        # Find all list items (checked or unchecked) to define the boundaries of each problem block.
        # The `re.MULTILINE` flag is crucial for `^` to match the start of each line.
        problem_starts = list(re.finditer(r'^\*\s*\[[ xX]\]', content, re.MULTILINE))

        for i, start_match in enumerate(problem_starts):
            # We only care about blocks that are explicitly checked with '[x]' or '[X]'
            if '[x]' not in start_match.group(0).lower():
                continue

            # Define the text block for this specific problem.
            # It starts at the beginning of the current problem's line...
            start_pos = start_match.start()
            # ...and ends at the beginning of the *next* problem's line (or the end of the file).
            end_pos = problem_starts[i+1].start() if i + 1 < len(problem_starts) else len(content)
            
            block = content[start_pos:end_pos]
            
            # Now, extract details from this isolated and safe block
            id_match = re.search(r'(\d+)\\?\.', block)
            notes_match = re.search(r'\*\*Notes\*\*:\s*(.*)', block, re.IGNORECASE)
            time_match = re.search(r'\*\*Time Taken\*\*:\s*(.*)', block, re.IGNORECASE)

            if id_match and notes_match and time_match:
                problem_id = int(id_match.group(1))
                # .strip() is important to remove leading/trailing whitespace
                notes = notes_match.group(1).strip()
                time_taken = time_match.group(1).strip()
                problems_to_update[problem_id] = {"notes": notes, "time_taken": time_taken}

        if problems_to_update:
            for p in state['problems']:
                if p['id'] in problems_to_update:
                    data = problems_to_update[p['id']]
                    # Sync only if it's a new completion or a due repetition
                    today_str = get_today_str()
                    if p['status'] == 'pending' or (p['next_repetition_date'] and p['next_repetition_date'] <= today_str):
                        p['status'] = 'completed'
                        p['completion_history'].append({"date": today_str, "notes": data['notes'], "time_taken": data['time_taken']})
                        
                        level = p['repetition_level']
                        if level < len(REPETITION_INTERVALS):
                            interval = REPETITION_INTERVALS[level]
                            next_date = datetime.now() + timedelta(days=interval)
                            p['next_repetition_date'] = next_date.strftime('%Y-%m-%d')
                            p['repetition_level'] += 1
                        else: # Mastered
                            p['next_repetition_date'] = None
                        click.echo(f"Synced progress for: {p['id']}. {p['title']}")

            save_state(state)
        
        synced_files.append(plan_file)

    if not synced_files:
        click.echo("No daily plans found to sync.")
        return
        
    for f in synced_files:
        os.remove(f)

    if synced_files:
        click.echo(f"Synced and removed {len(synced_files)} daily plan(s).")
        generate_dashboard()

@cli.command()
@click.option('--count', default=3, help='Number of extra problems to add.')
def add(count):
    """Adds extra new problems to today's plan."""
    state = load_state()
    today = get_today_str()
    plan_file_path = os.path.join(DAILY_PLANS_DIR, f"{today}.md")

    if not state or not os.path.exists(plan_file_path):
        click.echo(click.style("No plan for today. Run 'plan' first.", fg="red"))
        return
    
    extra_problems = [p for p in state['problems'] if p['status'] == 'pending' and p['scheduled_date'] > today]
    extra_problems = sorted(extra_problems, key=lambda x: x['scheduled_date'])[:count]

    if not extra_problems:
        click.echo("No more pending problems left to add!")
        return
    
    content = ["\n---\n\n## ✨ Added Problems\n"]
    for task in extra_problems:
        # Pull the problem's schedule date to today
        for p_state in state['problems']:
            if p_state['id'] == task['id']:
                p_state['scheduled_date'] = today
                break
        
        content.append(f"*   [ ] {task['id']}\\. {task['title']} ({task['category']})")
        content.append(f"    *   **Notes**:")
        content.append(f"    *   **Time Taken**:")

    with open(plan_file_path, 'a', encoding='utf-8') as f:
        f.write('\n'.join(content))
    
    save_state(state)
    click.echo(click.style(f"Added {len(extra_problems)} extra problem(s) to today's plan.", fg="green"))

@cli.command()
def reset():
    """Archives the current plan and resets the system."""
    if not os.path.exists(STATE_FILE):
        click.echo(click.style("Nothing to reset. Run 'init' to start.", fg="yellow"))
        return

    click.confirm("Are you sure you want to reset? This will archive your current progress.", abort=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    # Archive essential files
    if os.path.exists(STATE_FILE):
        shutil.move(STATE_FILE, os.path.join(ARCHIVE_DIR, f"{timestamp}_state.json"))
    if os.path.exists(DASHBOARD_FILE):
        shutil.move(DASHBOARD_FILE, os.path.join(ARCHIVE_DIR, f"{timestamp}_dashboard.md"))
        
    # Clear working directories
    for f in os.listdir(DAILY_PLANS_DIR):
        os.remove(os.path.join(DAILY_PLANS_DIR, f))
    for f in os.listdir(WORKSPACE_DIR):
        os.remove(os.path.join(WORKSPACE_DIR, f))
        
    click.echo(click.style("System has been reset.", fg="green"))
    click.echo(f"Your previous state has been archived in '{ARCHIVE_DIR}'.")
    click.echo("Run 'init' to start a new journey.")


if __name__ == '__main__':
    cli()