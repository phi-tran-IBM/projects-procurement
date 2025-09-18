"""
template_utils.py - Template extraction utilities
"""
import re
import logging
import xml.etree.ElementTree as ET
from typing import Any, List

logger = logging.getLogger(__name__)

def extract_text_from_response(response: Any) -> str:
    """
    Enhanced extraction for both template and JSON responses.
    Handles dict, string, template formats, and other types safely.
    """
    if response is None:
        return ""

    if isinstance(response, str):
        # Check if it's a template response
        if '<' in response and '>' in response:
            extracted = extract_template_response(response)
            if extracted and extracted != response:
                return extracted
        return response
    elif isinstance(response, dict):
        # Try common fields that might contain the text response
        for field in ['answer', 'text', 'content', 'response', 'result']:
            if field in response and response[field]:
                # Recursively extract in case the field contains template
                return extract_text_from_response(response[field])
        # Fallback to string representation
        return str(response)
    else:
        return str(response)

def extract_template_response(response_text: str) -> str:
    """
    Extract readable content from template-formatted responses.
    Handles various template formats used by the system.
    """
    if not response_text or not isinstance(response_text, str):
        return response_text
    
    # Check for recommendation template
    if '<recommendations>' in response_text.lower():
        return extract_recommendations_template(response_text)
    
    # Check for comparison template
    if '<comparison_start>' in response_text.lower():
        return extract_comparison_template(response_text)
    
    # Check for statistical template
    if '<statistical_analysis>' in response_text.lower():
        return extract_statistical_template(response_text)
    
    # Check for synthesis/general template
    if '<response_start>' in response_text.lower() or '<answer>' in response_text.lower():
        return extract_synthesis_template(response_text)
    
    # Check for insufficient data
    if '<insufficient_data>' in response_text.lower():
        match = re.search(r'<insufficient_data>(.*?)</insufficient_data>',
                         response_text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    
    # If no specific template found, try to clean generic tags
    cleaned = clean_template_tags(response_text)
    return cleaned if cleaned != response_text else response_text

def extract_recommendations_template(response_text: str) -> str:
    """Extract and format recommendation template responses from XML."""
    try:
        # Clean the input string to remove potential artifacts before the root element
        xml_string = response_text[response_text.lower().find('<recommendations>'):]
        root = ET.fromstring(xml_string)

        recommendations = root.findall("recommendation")
        if not recommendations:
            return "No recommendations provided."

        formatted = []
        for i, rec in enumerate(recommendations, 1):
            action = rec.findtext("action", "N/A")
            justification = rec.findtext("justification", "N/A")
            priority = rec.findtext("priority", "Medium")
            formatted.append(f"{i}. {action} (Priority: {priority})\n   Justification: {justification}")

        if formatted:
            return "Strategic Recommendations:\n\n" + "\n\n".join(formatted)

        return "No actionable recommendations found in the response."

    except (ET.ParseError, ValueError) as e:
        logger.error(f"Failed to parse recommendation XML: {e}")
        return clean_template_tags(response_text)

def extract_comparison_template(response_text: str) -> str:
    """Extract and format comparison template responses"""
    result = []
    
    # Extract summary
    summary_match = re.search(r'<SUMMARY>(.*?)</SUMMARY>', response_text, re.IGNORECASE | re.DOTALL)
    if summary_match:
        result.append(f"Summary: {summary_match.group(1).strip()}\n")
    
    # Extract vendor analyses
    for i in range(1, 11):  # Support up to 10 vendors
        vendor_pattern = f'<VENDOR{i}>\\s*<NAME>(.*?)</NAME>\\s*<PERFORMANCE>(.*?)</PERFORMANCE>\\s*(?:<STRENGTHS>(.*?)</STRENGTHS>)?\\s*(?:<CONCERNS>(.*?)</CONCERNS>)?\\s*</VENDOR{i}>'
        match = re.search(vendor_pattern, response_text, re.IGNORECASE | re.DOTALL)
        if match:
            name = match.group(1).strip()
            performance = match.group(2).strip()
            strengths = match.group(3).strip() if match.group(3) else "Not specified"
            concerns = match.group(4).strip() if match.group(4) else "None identified"
            
            result.append(f"**{name}**")
            result.append(f"Performance: {performance}")
            result.append(f"Strengths: {strengths}")
            result.append(f"Concerns: {concerns}\n")
    
    # Extract recommendation
    rec_match = re.search(r'<RECOMMENDATION>(.*?)</RECOMMENDATION>', response_text, re.IGNORECASE | re.DOTALL)
    if rec_match:
        result.append(f"Recommendation: {rec_match.group(1).strip()}")
    
    if result:
        return "\n".join(result)
    
    return clean_template_tags(response_text)

def extract_statistical_template(response_text: str) -> str:
    """Extract and format statistical template responses from XML."""
    try:
        xml_string = response_text[response_text.lower().find('<statistical_analysis>'):]
        root = ET.fromstring(xml_string)

        result = []

        summary = root.findtext("summary")
        if summary:
            result.append(f"Summary: {summary.strip()}\n")

        findings = root.findall("findings/finding")
        if findings:
            result.append("Key Findings:")
            for i, f in enumerate(findings, 1):
                result.append(f"{i}. {f.text.strip()}")
            result.append("")

        business_impact = root.findtext("business_impact")
        if business_impact:
            result.append(f"Business Impact: {business_impact.strip()}\n")

        recommendations = root.findall("recommendations/recommendation")
        if recommendations:
            result.append("Recommendations:")
            for rec in recommendations:
                result.append(f"- {rec.text.strip()}")

        if result:
            return "\n".join(result)

        return "Could not extract statistical analysis from the response."

    except (ET.ParseError, ValueError) as e:
        logger.error(f"Failed to parse statistical XML: {e}")
        return clean_template_tags(response_text)

def extract_synthesis_template(response_text: str) -> str:
    """Extract and format synthesis/general template responses"""
    # Try to extract main answer
    answer_match = re.search(r'<ANSWER>(.*?)</ANSWER>', response_text, re.IGNORECASE | re.DOTALL)
    if answer_match:
        return answer_match.group(1).strip()
    
    # Try to extract response content
    response_match = re.search(r'<RESPONSE>(.*?)</RESPONSE>', response_text, re.IGNORECASE | re.DOTALL)
    if response_match:
        return response_match.group(1).strip()
    
    # Fallback to cleaning tags
    return clean_template_tags(response_text)

def clean_template_tags(text: str) -> str:
    """Remove all template tags from text"""
    # Remove all XML-like tags
    cleaned = re.sub(r'<[^>]+>', '', text)
    # Clean up extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def format_llm_response_as_list(response: Any) -> List[str]:
    """
    Format LLM response as a list of strings.
    Enhanced to handle template responses.
    """
    text = extract_text_from_response(response)
    if not text:
        return []

    # Split by newlines and clean up
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # Remove bullet points or numbering if present
    cleaned_lines = []
    for line in lines:
        # Remove common bullet point formats
        line = line.lstrip('- ').lstrip('* ').lstrip('• ')
        # Remove numbering like "1. " or "1) "
        line = re.sub(r'^\d+[\.\)]\s*', '', line)
        if line:
            cleaned_lines.append(line)

    return cleaned_lines
