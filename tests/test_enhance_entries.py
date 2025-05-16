import pytest
from pathlib import Path
from scripts.enhance_entries import enhance_journal, parse_entry_metadata
import os

def test_parse_entry_metadata():
    # Test parsing metadata from a journal entry
    entry_text = """Date: 2024-03-15
Destination: Springer Mountain
Start Location: Amicalola Falls
Miles Hiked: 8.8
Total Trip Miles: 8.8

This was a great day on the trail..."""
    
    metadata = parse_entry_metadata(entry_text)
    assert metadata == {
        'date': '2024-03-15',
        'destination': 'Springer Mountain',
        'start_location': 'Amicalola Falls',
        'miles_hiked': 8.8,
        'total_miles': 8.8
    }

def test_enhance_journal_bedrock(tmp_path):
    # Test enhancing a journal with AI-generated content using Bedrock
    input_file = tmp_path / "test_journal.txt"
    output_file = tmp_path / "enhanced_journal.txt"
    
    # Create a sample journal entry
    input_file.write_text("""Date: 2024-03-15
Destination: Springer Mountain
Start Location: Amicalola Falls
Miles Hiked: 8.8
Total Trip Miles: 8.8

This was a great day on the trail...

---

Date: 2024-03-16
Destination: Hawk Mountain
Start Location: Springer Mountain
Miles Hiked: 7.6
Total Trip Miles: 16.4

Another beautiful day...""")
    
    # Mock the Bedrock API response
    def mock_bedrock_response(metadata):
        return f"Trail Context: The section from {metadata['start_location']} to {metadata['destination']} typically features..."
    
    # Enhance the journal
    enhance_journal(input_file, output_file, bedrock_client=mock_bedrock_response)
    
    # Verify the enhanced content
    enhanced_content = output_file.read_text()
    assert "Trail Context:" in enhanced_content
    assert "Amicalola Falls" in enhanced_content
    assert "Springer Mountain" in enhanced_content
    assert "Hawk Mountain" in enhanced_content

def test_enhance_journal_handles_bedrock_errors(tmp_path):
    # Test handling of Bedrock API errors
    input_file = tmp_path / "test_journal.txt"
    output_file = tmp_path / "enhanced_journal.txt"
    
    input_file.write_text("""Date: 2024-03-15
Destination: Springer Mountain
Start Location: Amicalola Falls
Miles Hiked: 8.8
Total Trip Miles: 8.8

This was a great day on the trail...""")
    
    def mock_failing_bedrock(metadata):
        raise Exception("Bedrock API Error")
    
    # Should not raise an exception
    enhance_journal(input_file, output_file, bedrock_client=mock_failing_bedrock)
    
    # Should still have the original content
    enhanced_content = output_file.read_text()
    assert "This was a great day on the trail" in enhanced_content
    assert "Bedrock API Error" not in enhanced_content 

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("AWS_REGION"),
    reason="Requires AWS credentials and region configured."
)
def test_enhance_journal_bedrock_integration(tmp_path):
    """Integration test: actually call Bedrock to enhance a journal entry."""
    from scripts.enhance_entries import enhance_journal
    input_file = tmp_path / "test_journal.txt"
    output_file = tmp_path / "enhanced_journal.txt"

    input_file.write_text("""Date: 2024-03-15
Destination: Springer Mountain
Start Location: Amicalola Falls
Miles Hiked: 8.8
Total Trip Miles: 8.8

This was a great day on the trail...""")

    # This will use the real Bedrock client (requires AWS credentials and access)
    enhance_journal(input_file, output_file)

    enhanced_content = output_file.read_text()
    assert "Trail Context:" in enhanced_content
    assert "Springer Mountain" in enhanced_content
    assert "Amicalola Falls" in enhanced_content
    # The context should not be empty
    assert len(enhanced_content.split("Trail Context:")[1].strip()) > 10 