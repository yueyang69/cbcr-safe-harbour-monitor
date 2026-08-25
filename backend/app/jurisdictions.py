"""Recognised CbCR jurisdictions (countries / regions).

Single source of truth for the Jurisdiction field: the API validates financial
data against this list and the frontend fetches it via GET /jurisdictions, so a
free-text field can no longer produce junk values like "UK2" or "TestReturn".

Naming follows ISO-ish country names. A few common aliases are canonicalised on
input (e.g. "US" -> "United States") so the database stays consistent.
"""

CANONICAL_JURISDICTIONS = {
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda",
    "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain",
    "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan",
    "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria",
    "Burkina Faso", "Burundi", "Cabo Verde", "Cambodia", "Cameroon", "Canada",
    "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros",
    "Congo (Democratic Republic)", "Congo (Republic)", "Costa Rica", "Croatia", "Cuba",
    "Cyprus", "Czech Republic", "Denmark", "Djibouti", "Dominica",
    "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea",
    "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland", "France",
    "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada",
    "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "Hungary",
    "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy",
    "Ivory Coast", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati",
    "Kosovo", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho",
    "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Madagascar",
    "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands",
    "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia",
    "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal",
    "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea",
    "North Macedonia", "Norway", "Oman", "Pakistan", "Palau", "Palestine", "Panama",
    "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal",
    "Qatar", "Romania", "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia",
    "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe",
    "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore",
    "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Korea",
    "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland",
    "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo",
    "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu",
    "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States",
    "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela", "Vietnam",
    "Yemen", "Zambia", "Zimbabwe",
    # A few jurisdictions that routinely appear in CbCR reporting without being
    # standalone countries.
    "Hong Kong", "Macau", "Puerto Rico",
}

# Common aliases -> canonical name. Accepted on input and normalised on write.
JURISDICTION_ALIASES = {
    "UK": "United Kingdom",
    "England": "United Kingdom",
    "Scotland": "United Kingdom",
    "Wales": "United Kingdom",
    "Northern Ireland": "United Kingdom",
    "US": "United States",
    "USA": "United States",
    "U.S.": "United States",
    "U.S.A.": "United States",
    "Korea": "South Korea",
    "South Korea (Republic of Korea)": "South Korea",
    "North Korea (DPRK)": "North Korea",
    "Russia (Russian Federation)": "Russia",
    "Russia Federation": "Russia",
    "Czechia": "Czech Republic",
    "Iran (Islamic Republic of)": "Iran",
    "Syria (Syrian Arab Republic)": "Syria",
    "Venezuela (Bolivarian Republic of)": "Venezuela",
    "Bolivia (Plurinational State of)": "Bolivia",
    "Tanzania (United Republic of)": "Tanzania",
    "Laos (Lao People's Democratic Republic)": "Laos",
    "Moldova (Republic of)": "Moldova",
    "Congo": "Congo (Republic)",
    "DRC": "Congo (Democratic Republic)",
    "Ivory Coast (Côte d'Ivoire)": "Ivory Coast",
}


def normalize_jurisdiction(value: str) -> str:
    """Return the canonical name, or the original value if it is not recognised."""
    return JURISDICTION_ALIASES.get(value, value)


def is_valid_jurisdiction(value: str) -> bool:
    return normalize_jurisdiction(value) in CANONICAL_JURISDICTIONS
