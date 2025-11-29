"""Prompts used for data ingestion and cleaning tasks."""

PROMPT_CLEAN_MODEL = """
You are a car expert. You are given a list of car models with extraneous details included in the model string (like engine volume, door count, body type, etc.). Your task is to extract and return a list of the **unique, base model names** from this input.

Important: return only the json without any comments!

Example:

Input:
[
    ("toyota", "corolla 4dr 2.0l 4cyl 2wd"),
    ("toyota", "yaris 4dr 4cyl"),
    ("toyota", "yaris 1.5l 2wd"),
    ("chevrolet", "silverado 1500 extended cab")
]

Output:
{{ 
    "toyota": ["corolla", "yaris"],
    "chevrolet": ["silverado"]
}}

list of cars: {list_cars}
"""

PROMPT_ENRICH_COLUMNS = """
You will get a free text. You need to extract the following information, if available:
- manufacturer
- model
- year
- price
- odometer in km
- transmission
- fuel
- drive (4wd, fwd, ...)
- type (SUV, hatchback, sedan)
- paint_color
- condition (like new, good, excellent, ...).

If some fields are not found in the text, return them as null.
Do not add any comment, answer only with a JSON format.

EXAMPLE:
free text: 2019 Ford Focus Sedan 2.0L 4dr Sedan 4WD 2019 Ford Focus Sedan 2.0L
answer:
{{
    "manufacturer": "ford",
    "model": "focus",
    "year": "2019",
    "price": null,
    "odometer": null,
    "transmission": null,
    "fuel": null,
    "drive": "4wd",
    "type": "sedan",
    "paint_color": null,
    "condition": null
}}

free text: {free_text}
"""
