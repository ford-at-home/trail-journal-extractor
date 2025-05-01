# trail-journal-extractor
Extract trail journals from TrailJournals.com.

My end goal is to produce some kind of hardcover book containing some of these memories, but for now I'm just trying to pull them all out in narrative form. The backstory on this is an AT thru-hike I completed in 2010. I'd like to someone be able to read these to my children, spruce them up, find art to go with the entries, or otherwise bring them into a format that's more digestable than this website. 

Technical specs:
* journals are all on easy to fetch URL's that appear hardcoded on my profile, making for easy bs4 slurping
* with that, I just have a simple data rendering problem and this project should be done in a few minutes.
* once I get my journals in Python object, it's time for me to render them into 1 big block with headers, maybe break it up into chapters.
* I'm thinking about getting LLM's involved somehow, but we'll leave that out for now also.
* ideally, I could somehow output these into a project file format used by a book publisher of some kind.
* I'm also going to go in and edit some of these to add details I may have left out, which will require me to just do a little memory lane walking.

Side note: huge shout out to the maintainers of TrailJournals.com for holding onto all of these journal entries for me!

---
## Setting up the Virtual Environment

This project uses a Python virtual environment to manage dependencies.

**To set up and activate the virtual environment:**

1.  Run the command: `venv_up`
2.  This script will:
    * Create a virtual environment named `venv` if it doesn't exist.
    * Activate the virtual environment.
    * Create an empty `requirements.txt` file if it doesn't exist.
    * Install dependencies listed in `requirements.txt` using `pip3 install -r requirements.txt`.
    * Ensure the `venv` directory is excluded from Git tracking by adding it to `.gitignore`.

**Managing Dependencies:**

* List your project dependencies in the `requirements.txt` file (one package per line).
* Install dependencies using: `pip install -r requirements.txt` (this is automatically run by `venv_up` after activation if the file is not empty).
* To add new dependencies, install them with pip while the virtual environment is active and then update `requirements.txt` using: `pip freeze > requirements.txt`

**Deactivating the Virtual Environment:**

* To exit the virtual environment, run the command: `deactivate`

**Excluding from Git:**

* The `venv` directory is automatically added to `.gitignore` to prevent committing environment-specific files.
