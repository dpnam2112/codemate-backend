from typing import Dict

JUDGE0_LANGUAGE_MAPPING: Dict[str, int] = {
    "C": 50,
    "C++": 54,
    "C++17": 59,
    "C++20": 76,
    "C#": 51,
    "Java": 62,
    "JavaScript": 63,
    "Python2": 70,
    "Python3": 71,
    "Go": 60,
    "Ruby": 72,
    "Rust": 73,
    "Swift": 83,
    "Kotlin": 78,
    "TypeScript": 74,
    "PHP": 68,
    "Perl": 85,
    "Scala": 81,
    "Haskell": 61,
    "Lua": 64,
    "R": 80
}

# Create reverse mapping
JUDGE0_ID_TO_LANGUAGE: Dict[int, str] = {v: k for k, v in JUDGE0_LANGUAGE_MAPPING.items()}

def get_language_name(language_id: int) -> str:
    """
    Get the language name for a given Judge0 language ID.
    
    Args:
        language_id (int): The Judge0 language ID
        
    Returns:
        str: The name of the programming language
        
    Raises:
        ValueError: If the language ID is not supported
    """
    if language_id not in JUDGE0_ID_TO_LANGUAGE:
        raise ValueError(f"Unsupported language ID: {language_id}")
    return JUDGE0_ID_TO_LANGUAGE[language_id]