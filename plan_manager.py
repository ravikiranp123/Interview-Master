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
PROBLEM_LISTS_DIR = os.path.join(BASE_DIR, "problem_lists")
DAILY_PLANS_DIR = os.path.join(BASE_DIR, "daily_plans")
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
ARCHIVE_DIR = os.path.join(BASE_DIR, "archive")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
DASHBOARD_FILE = os.path.join(BASE_DIR, "dashboard.md")

# --- Spaced Repetition Schedule ---
# Intervals in days for repeated practice.
REPETITION_INTERVALS = [1, 7, 16, 35, 90]

# --- HELPER FUNCTIONS ---


def get_today_str():
    """Returns today's date as a 'YYYY-MM-DD' string."""
    return datetime.now().strftime("%Y-%m-%d")


def load_state():
    """Loads the state from state.json, returning None if it doesn't exist."""
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    """Saves the given state object to state.json."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def ensure_dirs():
    """Ensures all necessary directories exist before running a command."""
    os.makedirs(PROBLEM_LISTS_DIR, exist_ok=True)
    os.makedirs(DAILY_PLANS_DIR, exist_ok=True)
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)


def format_duration(seconds):
    """Formats a duration in seconds into a human-readable string (e.g., '1h 25m')."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{int(minutes)}m {int(seconds % 60)}s"
    hours = minutes / 60
    return f"{int(hours)}h {int(minutes % 60)}m"


# --- CORE LOGIC FUNCTIONS ---


def generate_dashboard():
    """Generates the dashboard.md file from the current state."""
    state = load_state()
    if not state:
        return

    plan_name = state.get("plan_name", "Unknown Plan")
    state_problems_map = {p["id"]: p for p in state.get("problems", [])}

    plan_file_path = os.path.join(PROBLEM_LISTS_DIR, f"{plan_name.replace(' ', '')}.json")
    try:
        with open(plan_file_path, "r", encoding="utf-8") as f:
            problem_data = json.load(f)
    except FileNotFoundError:
        click.echo(click.style(f"Dashboard generation skipped: Could not find '{plan_file_path}'", fg="yellow"))
        return

    total_problems = len(state_problems_map)
    completed_problems = sum(1 for p in state_problems_map.values() if p["status"] == "completed")
    progress_percent = (completed_problems / total_problems * 100) if total_problems > 0 else 0

    content = [f"# LeetCode Journey: {plan_name} Dashboard\n"]
    content.append(f"**Overall Progress: {completed_problems} / {total_problems} ({progress_percent:.1f}%)**\n")
    content.append("---\n")

    for category, problems_in_list in problem_data["categories"].items():
        cat_problem_ids = {p["id"] for p in problems_in_list}
        completed_in_cat = sum(1 for pid in cat_problem_ids if state_problems_map.get(pid, {}).get("status") == "completed")
        total_in_cat = len(cat_problem_ids)
        content.append(f"### {category} ({completed_in_cat} / {total_in_cat})\n")

        for problem_template in problems_in_list:
            p_id = problem_template["id"]
            p_state = state_problems_map.get(p_id)
            if not p_state: continue

            checkbox = "[x]" if p_state["status"] == "completed" else "[ ]"
            repeat_date_str = ""
            if p_state.get("next_repetition_date"):
                repeat_date_str = f" (Next Repeat: {p_state['next_repetition_date']})"
            content.append(f"- {checkbox} {p_state['id']}\\. {p_state['title']}{repeat_date_str}")

            if p_state["status"] == "completed" and p_state["completion_history"]:
                for i, entry in enumerate(p_state["completion_history"]):
                    date = entry.get("date", "N/A")
                    notes = entry.get("notes")
                    if not notes: notes = "No notes provided."
                    else: notes = notes.strip()
                    time = f", Time: {entry.get('time_taken', 'N/A')}" if entry.get("time_taken") else ""
                    rating = f" - Rating: {entry.get('rating', 'N/A')}"
                    content.append(f"  - **Attempt {i+1} ({date}{time}{rating}):** {notes}")
        content.append("\n---\n")

    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(content))
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
        click.confirm(click.style("A 'state.json' file already exists. Continuing will overwrite it. Are you sure?", fg="yellow"), abort=True)

    available_lists = sorted([f.replace(".json", "") for f in os.listdir(PROBLEM_LISTS_DIR) if f.endswith(".json")])
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

    start_date_str = click.prompt("\nEnter start date (YYYY-MM-DD, leave blank for today)", default=get_today_str(), show_default=False)
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except ValueError:
        click.echo(click.style("Invalid date format. Please use YYYY-MM-DD.", fg="red"))
        return
    problems_per_day = click.prompt("How many new problems per day?", type=int, default=3, show_default=True)

    click.echo("\nPlease select a content richness level:")
    click.echo("  1. Minimal: Links to problems and solutions, notes, and manual time tracking.")
    click.echo("  2. Spoilers: Adds collapsible hints and full solution spoilers.")
    click.echo("  3. Video Link: Adds a direct link to the YouTube video walkthrough.")
    click.echo("  4. Video Embed: Embeds the YouTube video directly in the plan file.")
    richness_choice = click.prompt("Enter your choice (1-4)", type=click.IntRange(1, 4), default=1, show_default=True)

    level_map = {1: "minimal", 2: "spoilers", 3: "video_link", 4: "video_embed"}
    rich_content_level = level_map[richness_choice]

    try:
        with open(os.path.join(PROBLEM_LISTS_DIR, f"{plan_name}.json"), "r", encoding="utf-8") as f:
            problem_data = json.load(f)
    except FileNotFoundError:
        click.echo(click.style(f"Error: Could not find {plan_name}.json.", fg="red"))
        return

    all_problems = []
    current_date = start_date
    day_counter = 0

    for category, problems in problem_data["categories"].items():
        for problem in problems:
            if day_counter >= problems_per_day:
                current_date += timedelta(days=1)
                day_counter = 0
            
            problem_state = problem.copy()
            problem_state.update({
                "category": category, "status": "pending", "scheduled_date": current_date.strftime("%Y-%m-%d"),
                "next_repetition_date": None, "repetition_level": 0, "completion_history": []
            })
            all_problems.append(problem_state)
            day_counter += 1
            
    state = {"plan_name": problem_data["name"], "problems": all_problems, "rich_content_level": rich_content_level}
    save_state(state)
    generate_dashboard()
    click.echo(click.style(f"\nSuccessfully initialized '{plan_name}' plan with '{rich_content_level}' content level!", fg="green"))
    click.echo("Run 'python plan_manager.py plan' to generate your first daily plan.")


@cli.command()
def plan():
    """Generates the daily plan, including a rating legend."""
    state = load_state()
    if not state:
        click.echo(click.style("No plan initialized. Run 'init' first.", fg="red"))
        return

    rich_content_level = state.get("rich_content_level", "minimal")
    today = get_today_str()
    plan_file_path = os.path.join(DAILY_PLANS_DIR, f"{today}.md")

    for f in glob.glob(os.path.join(WORKSPACE_DIR, "*.py")):
        os.remove(f)
    click.echo(f"Cleaned workspace: '{WORKSPACE_DIR}'")

    all_pending = [p for p in state["problems"] if p["status"] == "pending"]
    all_completed = [p for p in state["problems"] if p["status"] == "completed"]

    overdue_tasks = [(p, 'new') for p in all_pending if p["scheduled_date"] < today]
    overdue_repetitions = [(p, 'rep') for p in all_completed if p.get("next_repetition_date") and p["next_repetition_date"] < today]
    
    all_overdue_items = overdue_tasks + overdue_repetitions
    def get_due_date(item):
        problem, item_type = item
        return problem['scheduled_date'] if item_type == 'new' else problem['next_repetition_date']
    all_overdue_items.sort(key=get_due_date)

    new_tasks_today = [p for p in all_pending if p["scheduled_date"] == today]
    reps_due_today = [p for p in all_completed if p.get("next_repetition_date") == today]
    overdue_to_solve = []

    if all_overdue_items:
        click.echo(click.style(f"You have {len(all_overdue_items)} overdue items.", fg="yellow"))
        focus_count = click.prompt(f"How many of the oldest ones would you like to focus on today?", type=click.IntRange(0, len(all_overdue_items)), default=min(2, len(all_overdue_items)))
        if focus_count > 0:
            overdue_to_solve = all_overdue_items[:focus_count]

    content = [f"# LeetCode Plan for: {today}\n"]
    
    rating_legend = [
        "### Rating Legend",
        "- **4: Again** - I was lost and need to review this tomorrow.",
        "- **3: Hard** - I needed hints or the solution to complete it.",
        "- **2: Medium** - I got the solution, but it took some time or had bugs.",
        "- **1: Easy** - I solved it quickly and feel confident.",
        "- **0: Mastered** - This is trivial; do not schedule for repetition.",
    ]
    content.extend(rating_legend)
    
    def generate_problem_markdown(task, level, is_overdue=False, is_rep=False):
        lines = []
        note = ""
        if is_overdue:
            due_date = task.get('next_repetition_date') if is_rep else task.get('scheduled_date')
            note = f" (Overdue from {due_date})"
        lines.append(f"-   [ ] {task['id']}\\. {task['title']} {note}")
        lines.append("    *   **Rating (0-4)**: ")
        lines.append("    *   **Notes**: ")
        lines.append("    *   **Time Taken (Manual)**: ")

        resource_blocks = []
        if level in ["minimal", "spoilers", "video_link", "video_embed"]:
            if task.get('leetcode_url'):
                 resource_blocks.append(f"        *   [LeetCode Problem]({task['leetcode_url']})")
            if task.get('solution_link'):
                link = task['solution_link']
                resource_blocks.append(f"        *   [{link.get('text', 'Solution Link')}]({link.get('url', '#')})")
        
        if level in ["spoilers", "video_link", "video_embed"]:
            if task.get('hints'):
                hint_lines = ["        *   **Hints:**"]
                for i, hint_text in enumerate(task['hints'], 1):
                    hint_lines.append(f"            - <details><summary>Hint {i}</summary>{hint_text}</details>")
                resource_blocks.append("\n".join(hint_lines))
            if task.get('solution'):
                sol = task['solution']
                sol_block = ["        *   <details><summary>Full Solution (Spoilers)</summary>"]
                if sol.get('explanation'):
                    sol_block.append(f"            **Explanation:**\n            {sol['explanation']}\n")
                if sol.get('code'):
                    for lang, code in sol['code'].items():
                        indented_code = "\n".join(["            " + line for line in code.split('\n')])
                        sol_block.append(f"            **{lang.capitalize()} Code:**\n            ```{lang}\n{indented_code}\n            ```")
                sol_block.append("            </details>")
                resource_blocks.append("\n".join(sol_block))
        
        if level in ["video_link", "video_embed"]:
            if task.get('youtube_id'):
                yt_id = task['youtube_id']
                video_url = f"https://www.youtube.com/watch?v={yt_id}"
                if level == "video_embed":
                    video_block = f"        *   **Video Walkthrough:**\n            <iframe src=\"https://www.youtube.com/embed/{yt_id}\" width=\"560\" height=\"315\" frameborder=\"0\" allowfullscreen></iframe>"
                    resource_blocks.append(video_block)
                else:
                    resource_blocks.append(f"        *   [Video Walkthrough]({video_url})")

        if resource_blocks:
            lines.append("    *   **Resources**:")
            lines.extend(resource_blocks)
        return "\n".join(lines)

    if new_tasks_today:
        content.append("---\n\n## 🚀 New Problems To Solve\n")
        for task in new_tasks_today:
            content.append(generate_problem_markdown(task, rich_content_level))

    if overdue_to_solve:
        content.append("---\n\n## 🔥 Overdue Focus\n")
        for item, item_type in overdue_to_solve:
            content.append(generate_problem_markdown(item, rich_content_level, is_overdue=True, is_rep=(item_type=='rep')))

    if reps_due_today:
        content.append("\n---\n\n## 🔁 Repetitions Due Today\n")
        for task in reps_due_today:
            content.append(generate_problem_markdown(task, rich_content_level))
    
    if not new_tasks_today and not overdue_to_solve and not reps_due_today:
        content.append("\n*Nothing scheduled for today. Use `add` to practice more or `rebalance` to adjust your schedule.*")
        
    with open(plan_file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content))

    click.echo(click.style(f"Today's plan created at: '{plan_file_path}'", fg="green"))


@cli.command()
def sync():
    """Syncs progress using robust line-by-line parsing and applies adaptive repetition."""
    state = load_state()
    if not state:
        click.echo(click.style("No plan initialized. Run 'init' first.", fg="red"))
        return

    synced_files = []
    for plan_file in glob.glob(os.path.join(DAILY_PLANS_DIR, "*.md")):
        with open(plan_file, "r", encoding="utf-8") as f:
            content = f.read()

        problems_to_update = {}
        problem_starts = list(re.finditer(r"^[\*\-]\s*\[[ xX]\]", content, re.MULTILINE))

        for i, start_match in enumerate(problem_starts):
            if "[x]" not in start_match.group(0).lower(): continue

            start_pos = start_match.start()
            end_pos = problem_starts[i + 1].start() if i + 1 < len(problem_starts) else len(content)
            block = content[start_pos:end_pos]
            
            id_match = re.search(r"(\d+)\\?\.", block)
            if not id_match: continue
            
            problem_id = int(id_match.group(1))
            notes = ""; rating = -1; manual_time = ""
            
            for line in block.split('\n'):
                line_lower = line.strip().lower()
                if "**notes**:" in line_lower:
                    notes = line.split(":", 1)[1].strip()
                elif "**rating (0-4)**:" in line_lower:
                    # Split the line at the colon and take the second part.
                    value_part = line.split(":", 1)[1].strip()
                    # Ensure the value is a digit before converting to an integer.
                    if value_part and value_part.isdigit():
                        rating = int(value_part)
                elif "**time taken (manual)**:" in line_lower:
                    manual_time = line.split(":", 1)[1].strip()

            if rating == -1:
                click.echo(click.style(f"Warning: Rating not found for problem {problem_id}. Defaulting to 'Medium' (2).", fg="yellow"))
                rating = 2
            
            time_taken_str = "N/A"
            solution_files = glob.glob(os.path.join(WORKSPACE_DIR, f"{problem_id}.*"))
            if solution_files:
                try:
                    creation_time = os.path.getctime(solution_files[0])
                    modified_time = os.path.getmtime(solution_files[0])
                    duration_seconds = modified_time - creation_time
                    if duration_seconds > 1: time_taken_str = format_duration(duration_seconds)
                except FileNotFoundError: pass
            
            if time_taken_str == "N/A" and manual_time:
                time_taken_str = manual_time

            problems_to_update[problem_id] = {"notes": notes, "rating": rating, "time_taken": time_taken_str}

        if problems_to_update:
            for p in state["problems"]:
                if p["id"] in problems_to_update:
                    data = problems_to_update[p["id"]]
                    today_str = get_today_str()
                    if p["status"] == "pending" or (p["next_repetition_date"] and p["next_repetition_date"] <= today_str):
                        p["status"] = "completed"
                        p["completion_history"].append({"date": today_str, "notes": data["notes"], "rating": data["rating"], "time_taken": data["time_taken"]})
                        
                        rating = data.get("rating", 2)
                        current_level = p.get("repetition_level", 0)
                        
                        if rating == 0:
                            p["next_repetition_date"] = None
                        elif rating == 1:
                            next_interval = 60
                            next_date = datetime.now() + timedelta(days=next_interval)
                            p["next_repetition_date"] = next_date.strftime("%Y-%m-%d")
                        elif rating == 2:
                            next_interval = REPETITION_INTERVALS[min(current_level, len(REPETITION_INTERVALS) - 1)]
                            p["repetition_level"] = current_level + 1
                            next_date = datetime.now() + timedelta(days=next_interval)
                            p["next_repetition_date"] = next_date.strftime("%Y-%m-%d")
                        elif rating == 3:
                            next_interval = 2
                            next_date = datetime.now() + timedelta(days=next_interval)
                            p["next_repetition_date"] = next_date.strftime("%Y-%m-%d")
                        elif rating == 4:
                            next_interval = 1
                            next_date = datetime.now() + timedelta(days=next_interval)
                            p["next_repetition_date"] = next_date.strftime("%Y-%m-%d")
                        
                        click.echo(f"Synced progress for: {p['id']}. {p['title']} (Rating: {rating}, Time: {data['time_taken']})")
            save_state(state)
        synced_files.append(plan_file)

    if not synced_files:
        click.echo("No daily plans found to sync. Regenerating dashboard from current state...")
        generate_dashboard()
        return

    for f in synced_files:
        os.remove(f)
    click.echo(f"Synced and removed {len(synced_files)} daily plan(s).")
    generate_dashboard()


@cli.command()
@click.option("--count", default=3, help="Number of extra problems to add.")
def add(count):
    """Adds extra new problems to today's plan with full formatting."""
    state = load_state()
    today = get_today_str()
    plan_file_path = os.path.join(DAILY_PLANS_DIR, f"{today}.md")

    if not state or not os.path.exists(plan_file_path):
        click.echo(click.style("No plan for today. Run 'plan' first.", fg="red"))
        return

    extra_problems = [p for p in state["problems"] if p["status"] == "pending" and p["scheduled_date"] > today]
    extra_problems = sorted(extra_problems, key=lambda x: x["scheduled_date"])[:count]

    if not extra_problems:
        click.echo("No more pending problems left to add!")
        return

    rich_content_level = state.get("rich_content_level", "minimal")
    content = ["\n---\n\n## ✨ Added Problems\n"]

    def generate_problem_markdown(task, level):
        lines = []
        lines.append(f"- [ ] {task['id']}\\. {task['title']} ({task['category']})")
        lines.append("    *   **Rating (1-4)**: ")
        lines.append("    *   **Notes**: ")
        lines.append("    *   **Time Taken (Manual)**: ")

        resource_blocks = []
        if level in ["minimal", "spoilers", "video_link", "video_embed"]:
            if task.get('leetcode_url'):
                 resource_blocks.append(f"        *   [LeetCode Problem]({task['leetcode_url']})")
            if task.get('solution_link'):
                link = task['solution_link']
                resource_blocks.append(f"        *   [{link.get('text', 'Solution Link')}]({link.get('url', '#')})")
        
        if level in ["spoilers", "video_link", "video_embed"]:
            if task.get('hints'):
                hint_lines = ["        *   **Hints:**"]
                for i, hint_text in enumerate(task['hints'], 1):
                    hint_lines.append(f"            - <details><summary>Hint {i}</summary>{hint_text}</details>")
                resource_blocks.append("\n".join(hint_lines))
            if task.get('solution'):
                sol = task['solution']
                sol_block = ["        *   <details><summary>Full Solution (Spoilers)</summary>"]
                if sol.get('explanation'):
                    sol_block.append(f"            **Explanation:**\n            {sol['explanation']}\n")
                if sol.get('code'):
                    for lang, code in sol['code'].items():
                        indented_code = "\n".join(["            " + line for line in code.split('\n')])
                        sol_block.append(f"            **{lang.capitalize()} Code:**\n            ```{lang}\n{indented_code}\n            ```")
                sol_block.append("            </details>")
                resource_blocks.append("\n".join(sol_block))

        if level in ["video_link", "video_embed"]:
            if task.get('youtube_id'):
                yt_id = task['youtube_id']
                video_url = f"https://www.youtube.com/watch?v={yt_id}"
                if level == "video_embed":
                    video_block = f"        *   **Video Walkthrough:**\n            <iframe src=\"https://www.youtube.com/embed/{yt_id}\" width=\"560\" height=\"315\" frameborder=\"0\" allowfullscreen></iframe>"
                    resource_blocks.append(video_block)
                else:
                    resource_blocks.append(f"        *   [Video Walkthrough]({video_url})")

        if resource_blocks:
            lines.append("    *   **Resources**:")
            lines.extend(resource_blocks)
        return "\n".join(lines)

    for task in extra_problems:
        for p_state in state["problems"]:
            if p_state["id"] == task["id"]:
                p_state["scheduled_date"] = today
                break
        content.append(generate_problem_markdown(task, rich_content_level))

    with open(plan_file_path, "a", encoding="utf-8") as f:
        f.write("\n".join(content))

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
    
    if os.path.exists(STATE_FILE):
        shutil.move(STATE_FILE, os.path.join(ARCHIVE_DIR, f"{timestamp}_state.json"))
    if os.path.exists(DASHBOARD_FILE):
        shutil.move(DASHBOARD_FILE, os.path.join(ARCHIVE_DIR, f"{timestamp}_dashboard.md"))

    for f in os.listdir(DAILY_PLANS_DIR):
        os.remove(os.path.join(DAILY_PLANS_DIR, f))
    for f in os.listdir(WORKSPACE_DIR):
        os.remove(os.path.join(WORKSPACE_DIR, f))
        
    click.echo(click.style("System has been reset.", fg="green"))
    click.echo(f"Your previous state has been archived in '{ARCHIVE_DIR}'.")
    click.echo("Run 'init' to start a new journey.")


@cli.command()
def rebalance():
    """Reschedules all pending problems starting from today."""
    state = load_state()
    if not state:
        click.echo(click.style("No plan found to rebalance. Run 'init' first.", fg="red"))
        return

    pending_problems = sorted([p for p in state["problems"] if p["status"] == "pending"], key=lambda x: x["scheduled_date"])
    
    if not pending_problems:
        click.echo(click.style("No pending problems to rebalance.", fg="green"))
        return

    click.echo(f"You have {len(pending_problems)} pending problems.")
    new_rate = click.prompt("How many problems per day would you like to schedule going forward?", type=int, default=3)
    
    current_date = datetime.strptime(get_today_str(), "%Y-%m-%d").date()
    day_counter = 0

    for problem in pending_problems:
        if day_counter >= new_rate:
            current_date += timedelta(days=1)
            day_counter = 0
        
        problem["scheduled_date"] = current_date.strftime("%Y-%m-%d")
        day_counter += 1

    save_state(state)
    generate_dashboard()
    click.echo(click.style(f"Successfully rebalanced {len(pending_problems)} pending problems at a new rate of {new_rate} per day.", fg="green"))


if __name__ == "__main__":
    cli()