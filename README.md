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

2. Set up the virtual environment and install dependencies:
   ```bash
   make
   ```
   This will create a virtual environment and install all required packages.

## Usage

The project includes a Makefile for common tasks. Run `make help` to see all available commands.

### Basic Workflow

1. Extract a journal:
   ```bash
   make journal JOURNAL_ID=10467
   ```
   This creates `journal_10467.txt` with the extracted entries.

2. Enhance the journal with AI context:
   ```bash
   export AWS_REGION=us-east-1  # Required for Bedrock
   make enhance
   ```
   This creates `journal_10467_enhanced.txt` with AI-generated trail context.

### Testing

The project includes both unit tests and integration tests:

- Run unit tests:
  ```bash
  make test
  ```

- Run integration tests (requires AWS credentials):
  ```bash
  export AWS_REGION=us-east-1
  make test-integration
  ```

### AWS Setup

To use the enhancement feature, you need:

1. AWS credentials configured (via environment variables or `~/.aws/credentials`):
   ```bash
   export AWS_REGION=us-east-1
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   ```

2. Access to AWS Bedrock and the Claude model in your AWS account.

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
- boto3 (for AWS Bedrock)
- botocore (for AWS Bedrock)
- pytest (for testing)

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
