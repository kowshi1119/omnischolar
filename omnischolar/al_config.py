"""
al_config.py — Sri Lankan A/L stream and subject definitions for OmniScholar.

Source: Department of Examinations Sri Lanka / National Institute of Education
"""

# Maps each A/L stream to its core and optional subjects.
# Keys match the exact stream names used in the DB (al_stream column).
STREAM_SUBJECTS: dict[str, list[str]] = {
    "Physical Science Stream": [
        "Combined Mathematics",
        "Physics",
        "Chemistry",
    ],
    "Biological Science Stream": [
        "Biology",
        "Physics",
        "Chemistry",
    ],
    "Commerce Stream": [
        "Accounting",
        "Business Studies",
        "Economics",
    ],
    "Arts Stream": [
        "History",
        "Geography",
        "Political Science",
        "Logic",
        "Buddhist Civilization",
        "Hindu Civilization",
        "Islam Civilization",
        "Christian Civilization",
        "Sinhala",
        "Tamil",
        "English",
        "French",
        "German",
        "Japanese",
        "Arabic",
        "Pali",
        "Sanskrit",
    ],
    "Technology Stream - Engineering Technology": [
        "Engineering Technology",
        "Science for Technology",
        "Information & Communication Technology",
        "Agriculture & Food Technology",
    ],
    "Technology Stream - Bio-systems Technology": [
        "Bio-systems Technology",
        "Science for Technology",
        "Information & Communication Technology",
        "Agriculture & Food Technology",
    ],
}

# Default subjects shown pre-selected per stream (core 3)
STREAM_DEFAULT_SUBJECTS: dict[str, list[str]] = {
    "Physical Science Stream": [
        "Combined Mathematics", "Physics", "Chemistry"
    ],
    "Biological Science Stream": [
        "Biology", "Physics", "Chemistry"
    ],
    "Commerce Stream": [
        "Accounting", "Business Studies", "Economics"
    ],
    "Arts Stream": [
        "History", "Geography", "Political Science"
    ],
    "Technology Stream - Engineering Technology": [
        "Engineering Technology", "Science for Technology"
    ],
    "Technology Stream - Bio-systems Technology": [
        "Bio-systems Technology", "Science for Technology"
    ],
}

# Stream short codes used in syllabus file paths
STREAM_FOLDER_NAMES: dict[str, str] = {
    "Physical Science Stream":                  "physical_science",
    "Biological Science Stream":                "biological_science",
    "Commerce Stream":                          "commerce",
    "Arts Stream":                              "arts",
    "Technology Stream - Engineering Technology": "technology_engineering",
    "Technology Stream - Bio-systems Technology": "technology_biosystems",
}

# Subject file slugs (used to build data/al_syllabus/<stream>/<subject>.json)
SUBJECT_FILE_SLUGS: dict[str, str] = {
    "Biology":                "biology",
    "Physics":                "physics",
    "Chemistry":              "chemistry",
    "Combined Mathematics":   "combined_mathematics",
    "Accounting":             "accounting",
    "Business Studies":       "business_studies",
    "Economics":              "economics",
    "History":                "history",
    "Geography":              "geography",
    "Engineering Technology": "engineering_technology",
    "Science for Technology": "science_for_technology",
    "Bio-systems Technology": "biosystems_technology",
    "Information & Communication Technology": "ict",
    "Agriculture & Food Technology": "agriculture_food_tech",
    "Political Science":      "political_science",
    "Logic":                  "logic",
}

STUDENT_TYPES = ["A/L Student", "Undergraduate"]
