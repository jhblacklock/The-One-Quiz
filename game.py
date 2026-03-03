#!/usr/bin/env python3
"""
The One Quiz — LOTR Quote Trivia
Guess which film each quote is from. Ten rounds. May the Valar guide you.

Usage:
    LOTR_API_KEY=<your-key> python game.py
"""

import os
import random
import sys
import time

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import IntPrompt, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from lotr_sdk import FilterOptions, LotrClient

console = Console()

# The six individual films (excluding the grouped "Series" entries which have no quotes)
FILMS = {
    "5cd95395de30eff6ebccde5c": "The Fellowship of the Ring",
    "5cd95395de30eff6ebccde5b": "The Two Towers",
    "5cd95395de30eff6ebccde5d": "The Return of the King",
    "5cd95395de30eff6ebccde58": "The Unexpected Journey",
    "5cd95395de30eff6ebccde59": "The Desolation of Smaug",
    "5cd95395de30eff6ebccde5a": "The Battle of the Five Armies",
}
FILM_IDS = list(FILMS.keys())
FILM_NAMES = list(FILMS.values())

TITLE = r"""
 _____ _             ___             ___        _
|_   _| |_  ___    / _ \ _ _  ___  / _ \ _  _ (_)___
  | | | ' \/ -_)  | (_) | ' \/ -_)| (_) | || || |_ /
  |_| |_||_\___|   \___/|_||_\___| \__\_\\_,_||_/__|
"""

EYE_ART = r"""
        .~.
      .'   `.
     /  o O  \      "Even the smallest person
    |   _|_   |      can change the course of
     \  / \  /       the future."
      `.___.`
"""

GRADE_EMOJI = {
    10: ("🏆", "Worthy of the Fellowship!", "bold gold1"),
    9:  ("🧙", "Gandalf would be proud!", "bold bright_white"),
    8:  ("⚔️",  "A true Ranger of the North.", "bold green"),
    7:  ("🌿", "Hobbit-smart, at least.", "bold green3"),
    6:  ("🗡️",  "You've seen the films... once.", "bold yellow"),
    5:  ("🍺", "Perhaps more time in the Shire.", "bold yellow3"),
    4:  ("💍", "The Ring is clouding your mind.", "bold orange3"),
    3:  ("🕷️",  "Even Gollum did better.", "bold red"),
    2:  ("🐛",  "You make a Sackville-Baggins look sharp.", "bold red3"),
    1:  ("💀", "One does not simply... remember anything.", "bold bright_red"),
    0:  ("🔥", "The Eye of Sauron weeps for you.", "bold bright_red"),
}


def clear():
    console.clear()


def title_screen():
    clear()
    console.print(Align.center(Text(TITLE, style="bold yellow")))
    console.print(Align.center(Text(EYE_ART, style="dim green")))
    console.print(
        Align.center(
            Panel(
                "[bold]10 rounds · Guess the film from the quote[/bold]\n"
                "[dim]The fate of Middle-earth rests on your knowledge.[/dim]",
                border_style="yellow",
                padding=(1, 6),
            )
        )
    )
    console.print()
    Prompt.ask("[yellow]  Press Enter to begin your quest[/yellow]", default="")


def fetch_random_quote(client: LotrClient) -> tuple[str, str] | None:
    """Return (dialog, movie_id) for a random quote from one of the six individual films."""
    movie_id = random.choice(FILM_IDS)

    # Get the total number of quotes for this film, then pick a random page
    first_page = client.movies.get_quotes(movie_id, FilterOptions(limit=1, page=1))
    if first_page.total == 0:
        return None

    total_pages = max(1, first_page.total // 10)
    random_page = random.randint(1, total_pages)

    page = client.movies.get_quotes(movie_id, FilterOptions(limit=10, page=random_page))
    candidates = [q for q in page.docs if len(q.dialog.strip()) > 10]
    if not candidates:
        return None

    quote = random.choice(candidates)
    return quote.dialog.strip(), movie_id


def loading_animation(message: str):
    with Progress(
        SpinnerColumn(style="yellow"),
        TextColumn(f"[yellow]{message}[/yellow]"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("", total=None)
        time.sleep(1.2)


def ask_question(round_num: int, total: int, dialog: str, correct_id: str) -> bool:
    clear()
    console.print(Rule(f"[yellow]Round {round_num} of {total}[/yellow]", style="yellow"))
    console.print()

    # Display the quote
    console.print(
        Panel(
            Align.center(f'[italic white]"{dialog}"[/italic white]'),
            title="[bold yellow]⚔ The Quote ⚔[/bold yellow]",
            border_style="yellow",
            padding=(1, 4),
        )
    )
    console.print()
    console.print("  [bold]Which film is this from?[/bold]\n")

    # Build options: correct answer + 3 random wrong answers, shuffled
    wrong_ids = [fid for fid in FILM_IDS if fid != correct_id]
    wrong_choices = random.sample(wrong_ids, 3)
    options = [correct_id] + wrong_choices
    random.shuffle(options)
    correct_pos = options.index(correct_id) + 1  # 1-indexed

    for i, fid in enumerate(options, 1):
        console.print(f"  [bold cyan]{i}.[/bold cyan] {FILMS[fid]}")

    console.print()

    while True:
        try:
            answer = IntPrompt.ask("  [yellow]Your answer[/yellow]", console=console)
            if 1 <= answer <= 4:
                break
            console.print("  [red]Please enter a number between 1 and 4.[/red]")
        except (ValueError, KeyboardInterrupt):
            console.print("  [red]Please enter a number between 1 and 4.[/red]")

    correct = answer == correct_pos

    console.print()
    if correct:
        console.print(
            Panel(
                f"[bold green]✓ Correct![/bold green] "
                f"[dim]That was from [italic]{FILMS[correct_id]}[/italic][/dim]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]✗ Wrong![/bold red] "
                f"The answer was [italic bold]{FILMS[correct_id]}[/italic bold]",
                border_style="red",
            )
        )

    time.sleep(1.8)
    return correct


def results_screen(score: int, total: int):
    clear()
    console.print(Rule("[yellow]Quest Complete[/yellow]", style="yellow"))
    console.print()

    grade_key = min(score, 10)
    emoji, verdict, style = GRADE_EMOJI.get(grade_key, GRADE_EMOJI[0])

    # Score table
    table = Table(box=box.ROUNDED, border_style="yellow", show_header=False, padding=(0, 2))
    table.add_column(justify="right", style="dim")
    table.add_column(style="bold")
    table.add_row("Score", f"{score} / {total}")
    table.add_row("Grade", f"{emoji}  [{style}]{verdict}[/{style}]")

    console.print(Align.center(table))
    console.print()

    # Quote bar
    bar = "█" * score + "░" * (total - score)
    console.print(Align.center(f"[yellow]{bar}[/yellow]"))
    console.print()
    console.print(Align.center("[dim]May your next journey be swifter, friend.[/dim]"))
    console.print()


def main():
    api_key = os.environ.get("LOTR_API_KEY")
    if not api_key:
        console.print("[red]Error:[/red] LOTR_API_KEY environment variable is not set.")
        sys.exit(1)

    client = LotrClient(api_key=api_key)
    total_rounds = 10

    title_screen()

    score = 0
    round_num = 0

    while round_num < total_rounds:
        clear()
        loading_animation("Consulting the archives of Middle-earth...")

        result = fetch_random_quote(client)
        if result is None:
            # Rare — just skip and retry
            continue

        dialog, movie_id = result
        round_num += 1

        correct = ask_question(round_num, total_rounds, dialog, movie_id)
        if correct:
            score += 1

    results_screen(score, total_rounds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[dim]You have chosen... to flee. Farewell.[/dim]\n")
