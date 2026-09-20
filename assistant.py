import webbrowser
from datetime import datetime


def show_menu():
    print("\n" + "=" * 45)
    print("PYTHON COMMAND ASSISTANT")
    print("=" * 45)
    print("Available commands:")
    print("- time")
    print("- date")
    print("- open youtube")
    print("- open google")
    print("- help")
    print("- exit")


show_menu()

while True:
    command = input("\nCommand: ").strip().lower()

    if command == "time":
        now = datetime.now().strftime("%I:%M %p")
        print(f"Current time: {now}")

    elif command == "date":
        today = datetime.now().strftime("%d %B %Y")
        print(f"Today's date: {today}")

    elif command == "open youtube":
        webbrowser.open("https://www.youtube.com")
        print("Opening YouTube...")

    elif command == "open google":
        webbrowser.open("https://www.google.com")
        print("Opening Google...")

    elif command == "help":
        show_menu()

    elif command == "exit":
        print("Assistant closed.")
        break

    else:
        print("Command not recognized.")
