#!/usr/bin/env python3
"""TechBuddy Demo File Setup — create/refresh demo files on Windows Desktop + Notes."""

import platform
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    DESKTOP = Path.home() / "Desktop"
    DOCUMENTS = Path.home() / "Documents"
    NOTES_DIR = Path.home() / "TechBuddy Notes"
else:
    # WSL — find Windows user home
    _skip = {"Public", "Default", "Default User", "All Users", "desktop.ini"}
    _win_users = [p for p in Path("/mnt/c/Users").iterdir()
                  if p.is_dir() and p.name not in _skip] if Path("/mnt/c/Users").exists() else []
    WIN_HOME = _win_users[0] if _win_users else Path.home()
    DESKTOP = WIN_HOME / "Desktop"
    DOCUMENTS = WIN_HOME / "Documents"
    NOTES_DIR = WIN_HOME / "TechBuddy Notes"


DEMO_FILES = {
    DESKTOP / "Grocery List.txt": """\
Grocery List
============

- Milk (2%)
- Bread (whole wheat)
- Eggs (1 dozen)
- Bananas
- Chicken breasts
- Rice
- Tomato sauce
- Butter
- Orange juice
- Cheese (cheddar)

Don't forget: Sarah's birthday cake ingredients!
- Vanilla extract
- Powdered sugar
- Cream cheese
""",

    DESKTOP / "Doctors Appointment Notes.txt": """\
Doctor Appointment Notes
========================
Dr. Johnson - February 13, 2026

- Blood pressure: 128/82 (good!)
- Lisinopril renewed - 10mg daily
- Next checkup: 6 months
- Remember to bring medication list next time
- Ask about knee pain
""",

    DESKTOP / "Important Phone Numbers.txt": """\
Important Phone Numbers
=======================

Sarah (daughter): (555) 123-4567
Michael (son): (555) 987-6543
Dr. Johnson: (555) 234-5678
CVS Pharmacy: (555) 345-6789
Book Club Margaret: (555) 456-7890
""",

    DESKTOP / "Recipe - Pot Roast.txt": """\
Sarah's Famous Pot Roast
========================

Ingredients:
- 3 lb chuck roast
- 6 potatoes, quartered
- 4 carrots, chunked
- 1 onion, sliced
- 2 cups beef broth
- Salt, pepper, garlic powder

Directions:
1. Season roast with salt, pepper, garlic
2. Brown all sides in Dutch oven
3. Add broth, vegetables around roast
4. Cover and cook at 325F for 3 hours
5. Let rest 10 minutes before serving

Sarah always makes this for Sunday dinner!
""",

    DESKTOP / "Tommy Drawing.txt": """\
(Tommy's Duck Drawing)

Tommy drew this for Grandma on his last visit!
He's getting so good at drawing.
Save this to show Sarah on Sunday.

--- Tommy, age 8 ---
""",

    DOCUMENTS / "Letter to Sarah.txt": """\
Dear Sarah,

Thank you so much for the lovely dinner last Sunday. The pot roast
was absolutely delicious, and Tommy's drawings made my whole week!

I'd love to have you all over to my place next time. I'll make
my famous chocolate chip cookies that Tommy loves.

Give Tommy and Mike my love.

With all my heart,
Mom
""",
}


NOTES_FILES = {
    "preferences.md": """\
## User Preferences
Updated: February 12, 2026

- Prefers large text
- Likes to check email first thing in the morning
- Daughter Sarah visits on Sundays
- Favorite book club: meets first Tuesday of the month at the library
- Doctor is Dr. Johnson at 100 Medical Center Drive
""",

    "contacts.md": """\
## Contacts
Updated: February 12, 2026

- Sarah Johnson (daughter) - sarah.johnson@gmail.com - (555) 123-4567
- Michael Johnson (son) - michael.j@gmail.com - (555) 987-6543
- Tommy (grandson, 8 years old) - likes dinosaurs and ducks
- Dr. Johnson - (555) 234-5678
- CVS Pharmacy - 245 Main Street
- Book Club Margaret - margaret@library.org
""",
}


def main():
    print()
    print("TechBuddy Demo File Setup")
    print("=" * 40)
    print()

    # Create demo files on Desktop + Documents
    for path, content in DEMO_FILES.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"  Created: {path.name} ({path.parent.name}/)")

    print()

    # Create TechBuddy Notes
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    for filename, content in NOTES_FILES.items():
        note_path = NOTES_DIR / filename
        note_path.write_text(content, encoding="utf-8")
        print(f"  Created: {filename} (TechBuddy Notes/)")

    print()
    print(f"Done! {len(DEMO_FILES)} demo files + {len(NOTES_FILES)} notes created.")
    print(f"  Desktop:  {DESKTOP}")
    print(f"  Notes:    {NOTES_DIR}")
    print()


if __name__ == "__main__":
    main()
