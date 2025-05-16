# Trail Journal Extractor

A Python tool for extracting and formatting trail journals from TrailJournals.com into a single, readable text file.

## Project Overview

This project was created to extract trail journals from TrailJournals.com, specifically focusing on an AT (Appalachian Trail) thru-hike from 2010. The goal is to transform these online journal entries into a format suitable for creating a hardcover book, making the memories more accessible and presentable.

### Features

- Extracts journal entries from TrailJournals.com
- Preserves entry metadata (date, location, miles)
- Formats entries into a clean, readable text file
- Handles rate limiting to be respectful to the server
- Includes error handling for failed requests

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/ford-at-home/trail-journal-extractor.git
   cd trail-journal-extractor
   ```

2. Set up the virtual environment:
   ```bash
   ./venv_up
   ```

## Usage

To extract a journal, run:
```bash
python scripts/extract_entries.py <journal_id>
```

For example:
```bash
python scripts/extract_entries.py 10467
```

The script will:
1. Fetch all entries for the specified journal
2. Extract the content and metadata
3. Create a formatted text file named `journal_<id>.txt`

### Enhancing Journal Entries

To enhance a journal with AI-generated trail context, run:
```bash
python scripts/enhance_entries.py journal_<id>.txt
```

This will:
1. Read the extracted journal
2. For each entry, generate a brief description of the trail section using Claude AI
3. Add the context to each entry
4. Create a new file named `journal_<id>_enhanced.txt`

Options:
- `--output <file>`: Specify a custom output file
- `--cache <file>`: Use a cache file to store API responses (recommended for large journals)

Note: You'll need to set the `ANTHROPIC_API_KEY` environment variable with your Claude API key.

### Output Format

Each entry in the output file includes:
- Date and destination as a header
- Start location
- Miles hiked that day
- Total trip miles
- The full entry text
- A separator line between entries

## Dependencies

The project requires:
- Python 3.x
- requests
- beautifulsoup4
- mutagen

These are automatically installed when setting up the virtual environment.

## Future Plans

- [ ] Add support for image extraction
- [ ] Implement different output formats (e.g., PDF, EPUB)
- [ ] Add progress saving/resume capability
- [ ] Integrate with LLMs for content enhancement
- [ ] Create a book publisher-compatible output format
- [ ] Add support for manual entry editing
- [ ] Implement automated testing

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms of the included LICENSE file.

## Acknowledgments

Special thanks to the maintainers of TrailJournals.com for preserving these valuable memories and making them accessible through their platform.
