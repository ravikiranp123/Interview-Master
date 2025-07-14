# Interview Master

Interview Master is a personalized, local-first system designed to bring structure, discipline, and efficiency to your technical interview preparation. It moves beyond simple problem tracking by integrating proven learning techniques like adaptive spaced repetition and creating a rich, self-contained study environment directly on your machine.

The core philosophy is to keep you focused on solving problems, not on managing your study plan. The system is designed to be fully automated, private, and customizable to your specific needs, whether you're starting with data structures or preparing for a final-round system design interview.

### Core Features

-   🧠 **Adaptive Spaced Repetition:** The system automatically schedules problems for review based on your rated difficulty. Easy problems get pushed out, while challenging ones are repeated sooner, optimizing for long-term retention.
-   ⏰ **Automatic Local Time Tracking:** Time spent on a problem is recorded automatically and privately using your file system—no external services required. A manual entry option is also available as a fallback.
-   📚 **Rich, Self-Contained Study Plans:** Your daily plans can be enriched with direct links, collapsible hints, full solution explanations, and video walkthroughs, keeping you in your editor and out of your browser.
-   ⚙️ **Fully Customizable:** Every part of the system is controlled by simple JSON and Markdown files. Create your own problem lists, add custom resources, and tune the system to match your study style.
-   🏠 **Local-First and Private:** All your data—your progress, notes, and plans—stays on your local machine.

## Getting Started

### 1. Prerequisites

Make sure you have Python 3 installed on your system.

### 2. Install Dependencies

This system uses a single external library, `click`, to create the user-friendly manager. Install it using pip:

```bash
pip install click
```

### 3. Setting Up Your First Plan (`init`)

To begin your journey, you need to initialize a study plan. This is a one-time setup process that creates your master `state.json` file and dashboard.

Run the following command from your terminal within the project folder:

```bash
python plan_manager.py init
```

The system will guide you through a series of questions to configure your entire plan:

-   **Plan Selection:** Choose from any `.json` file in the `problem_lists` folder. This project comes pre-loaded with **NeetCode 150** and **Blind 75**.
-   **Start Date:** Sets the starting point for your schedule.
-   **Problems Per Day:** Defines the pace for your initial schedule.
-   **Content Richness Level:** Allows you to choose how much information is displayed in your daily plans, from a minimal list to a fully interactive environment.

## The Core Engine: Recommended VS Code Extensions

This system is designed to wrap around the excellent, community-driven VS Code LeetCode extensions. They form the backbone of the coding and debugging workflow.

1.  **[LeetCode](https://marketplace.visualstudio.com/items?itemName=LeetCode.vscode-leetcode):** The essential extension for searching problems, writing code, and submitting solutions directly within VS Code.
2.  **[Debug LeetCode](https://marketplace.visualstudio.com/items?itemName=wangtao0101.debug-leetcode):** An invaluable tool for debugging your solutions locally with testcases.

### **CRITICAL SETUP STEP: Configuring Your Workspace**

For the automatic time tracking to work, you **must** configure the LeetCode extension to save its solution files inside this project's `workspace/` folder.

1.  In VS Code, go to `Settings`.
2.  Search for "LeetCode".
3.  Find the `Leetcode: Workspace Folder` setting.
4.  Set it to the **full, absolute path** of the `workspace` folder within your `Interview Master` project directory.

The system is designed to **clear this workspace folder daily** when you run the `plan` command. This is a key feature, not a bug! It forces you to re-solve problems from a blank slate, promoting true active recall instead of just recognizing your old code.

## The Recommended Daily Workflow

This system is designed to be a simple, three-step daily habit.

1.  **Generate Your Plan:**
    Start your study session by running `plan` from your terminal.
    ```bash
    python plan_manager.py plan
    ```
    This creates a fresh markdown file for the day in the `daily_plans` folder. If you have any overdue problems, it will intelligently prompt you to focus on a manageable number from your backlog first.

2.  **Open and Work in VS Code:**
    -   Open today's plan file and choose a problem (e.g., "1. Two Sum").
    -   Use the LeetCode extension's "Show Problem" command (Shortcut: `Ctrl+Alt+S`) and select the same problem. The extension will automatically create a file like `1.two-sum.py` in the `workspace/` folder.
    -   Code your solution in that file. Use the Debug LeetCode extension to test it.
    -   Once you've submitted your solution, go back to the daily plan markdown file.
    -   Click the checkbox to mark it as `[x]`.
    -   Fill in your **Rating (1-4)** and any **Notes**.

3.  **Sync Your Progress:**
    When you're done for the day, run `sync` from your terminal.
    ```bash
    python plan_manager.py sync
    ```
    The system will automatically read your completed problems, parse your notes and ratings, calculate the time you spent, schedule the next repetition, and update your master `dashboard.md`.

## The System Explained

### The Manager (`plan_manager.py`)

This is the heart of the system. Here are the available commands:

| Command | Description                                                                                                  |
| :-------- | :----------------------------------------------------------------------------------------------------------- |
| `init`    | **(Run Once)** Interactively creates and schedules a new study plan.                                           |
| `plan`    | **(Run Daily)** Generates your focused study plan for the day, prioritizing any overdue problems.             |
| `sync`    | **(Run after Studying)** Saves your progress, calculates time, schedules repetitions, and updates the dashboard. |
| `add`     | Adds a specified number of extra new problems to your current daily plan if you're feeling ambitious.           |
| `reset`   | Archives your current plan and progress, allowing you to `init` a completely new one.                        |

### The Folder Structure

```
/Interview Master
|
|-- 📊 dashboard.md          # Your high-level progress dashboard. ALWAYS UP-TO-DATE.
|
|-- 💻 workspace/             # A temporary folder for your code solutions. CLEARED DAILY.
|
|-- 📅 daily_plans/            # Your daily markdown checklists are generated here.
|
|-- 📜 state.json             # The "brain" of the system. Tracks all progress.
|
|-- 🐍 plan_manager.py       # The interactive Python script you will run.
|
|-- 🗂️ problem_lists/
    |-- neetcode150.json
    |-- blind75.json
    |-- test_plan.json
```

## Customization & Community

### Creating Your Own Study Plans

You can create your own `.json` study plans inside the `problem_lists` folder. The system will automatically detect them. This is perfect for creating company-specific lists (e.g., `google_top_50.json`).

**Example of a Fully Enriched Problem:**

```json
{
    "id": 217,
    "title": "Contains Duplicate",
    "leetcode_url": "https://leetcode.com/problems/contains-duplicate/",
    "solution_link": {
        "text": "NeetCode Solution",
        "url": "https://neetcode.io/solutions/contains-duplicate"
    },
    "youtube_id": "3OamzN90k_s",
    "hints": [
        "Think about the properties of a data structure that disallows duplicates."
    ],
    "solution": {
        "explanation": "To solve this problem efficiently, we can use a hash set...",
        "code": {
            "python": "class Solution:\n    def containsDuplicate(self, nums: list[int]) -> bool:\n        #..."
        }
    }
}
```

### Editors & Previews for Your Daily Plan

For the best experience viewing and editing your daily plan files inside VS Code, you may want a powerful markdown extension.

Here are some options:
-   **[Office Viewer (vscode-office)](https://marketplace.visualstudio.com/items?itemName=cweijan.vscode-office)**
-   **[Milkdown](https://marketplace.visualstudio.com/items?itemName=mirone.milkdown)**
-   **[Markdown Editor](https://marketplace.visualstudio.com/items?itemName=zaaack.markdown-editor)**

> ### **An Important Note on Previews**
> Markdown rendering is complex. The experience may vary between extensions, especially with rich content. **You may find that video embeds do not play, or that collapsible spoilers do not work correctly in every editor.**
>
> We encourage you to **test these extensions** and find the one that best suits your needs. The system provides four richness levels during `init` so you can choose a format that is most compatible with your preferred tools.

### Contributing

This project thrives on community contributions!

-   **Found a Bug? Have an Idea?** Please create an issue on the project's repository to report bugs or suggest new features.
-   **Submit Your Improvements:** Pull Requests (PRs) are welcome. Whether it's a code improvement, a bug fix, or a new feature, your contributions are valued.
-   **Share Your Problem Lists:** If you create a high-quality, company-specific problem list, consider submitting a PR to add it to the `problem_lists` folder for everyone to benefit from.

## The Future Roadmap

-   **Phase 1: Data Structures & Algorithms (Complete):** The current version of the system.
-   **Phase 2: System Design Mastery (Planned):** Extend the system to handle LLD and HLD preparation with dedicated templates and boilerplate code generation.
-   **Phase 3: AI-Powered Interview Preparation (Conceptual):** Integrate local or API-based AI for mock interviews, resume-tailored plans, dynamic hint generation, and code analysis.
