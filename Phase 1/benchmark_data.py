"""
Benchmark test cases for adversarial temporal decay evaluation
"""

from datetime import datetime

# Adversarial Benchmark: Semantically richer STALE vs. sparse CURRENT
# The challenge: can decay flip rankings when stale docs are semantically stronger?

benchmark = [
    # CASE 1: Catholic Church leadership
    {
        "query": "Who leads the Catholic Church?",
        "entries": [
            {
                "text": "Pope Francis is the head of the Catholic Church and leads the Vatican.",
                "acquired": datetime(2023, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2025, 5, 7)
            },
            {
                "text": "Pope Leo XIV succeeded Francis in May 2025.",
                "acquired": datetime(2025, 5, 8),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 2: US President
    {
        "query": "Who is the President of the United States?",
        "entries": [
            {
                "text": "Joe Biden serves as the 46th President of the United States and Commander in Chief.",
                "acquired": datetime(2021, 1, 20),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2025, 1, 19)
            },
            {
                "text": "Donald Trump became President in January 2025.",
                "acquired": datetime(2025, 1, 20),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 3: UK Prime Minister
    {
        "query": "Who is the UK Prime Minister?",
        "entries": [
            {
                "text": "Rishi Sunak serves as Prime Minister of the United Kingdom and head of government.",
                "acquired": datetime(2022, 10, 25),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2024, 7, 4)
            },
            {
                "text": "Keir Starmer is PM after July 2024 election.",
                "acquired": datetime(2024, 7, 5),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 4: Twitter/X ownership
    {
        "query": "Who runs Twitter?",
        "entries": [
            {
                "text": "Jack Dorsey is the CEO of Twitter and leads the social media platform.",
                "acquired": datetime(2020, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2022, 10, 26)
            },
            {
                "text": "Elon Musk owns X, formerly Twitter.",
                "acquired": datetime(2022, 10, 27),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 5: Solar system planets
    {
        "query": "How many planets are in the solar system?",
        "entries": [
            {
                "text": "The solar system contains nine planets including Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune, and Pluto.",
                "acquired": datetime(2000, 1, 1),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": datetime(2006, 8, 23)
            },
            {
                "text": "Eight planets. Pluto reclassified in 2006.",
                "acquired": datetime(2006, 8, 24),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 6: Apple CEO
    {
        "query": "Who is the CEO of Apple?",
        "entries": [
            {
                "text": "Steve Jobs is the CEO of Apple Inc. and leads the technology company.",
                "acquired": datetime(2010, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2011, 8, 23)
            },
            {
                "text": "Tim Cook leads Apple since 2011.",
                "acquired": datetime(2011, 8, 24),
                "last_verified": datetime(2026, 3, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 7: German Chancellor
    {
        "query": "Who is the German Chancellor?",
        "entries": [
            {
                "text": "Angela Merkel serves as Chancellor of Germany and leads the government coalition.",
                "acquired": datetime(2020, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2021, 12, 7)
            },
            {
                "text": "Olaf Scholz is Chancellor since December 2021.",
                "acquired": datetime(2021, 12, 8),
                "last_verified": datetime(2026, 3, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 8: French President
    {
        "query": "Who is the President of France?",
        "entries": [
            {
                "text": "François Hollande serves as President of the French Republic and leads the nation.",
                "acquired": datetime(2015, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2017, 5, 13)
            },
            {
                "text": "Emmanuel Macron is French President since 2017.",
                "acquired": datetime(2017, 5, 14),
                "last_verified": datetime(2026, 3, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 9: Amazon CEO
    {
        "query": "Who runs Amazon?",
        "entries": [
            {
                "text": "Jeff Bezos is the CEO of Amazon and founder of the e-commerce giant.",
                "acquired": datetime(2020, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2021, 7, 4)
            },
            {
                "text": "Andy Jassy became Amazon CEO in 2021.",
                "acquired": datetime(2021, 7, 5),
                "last_verified": datetime(2026, 3, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 10: Microsoft CEO
    {
        "query": "Who is Microsoft's chief executive?",
        "entries": [
            {
                "text": "Steve Ballmer is CEO of Microsoft Corporation and leads the software company.",
                "acquired": datetime(2012, 1, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": datetime(2014, 2, 3)
            },
            {
                "text": "Satya Nadella runs Microsoft since 2014.",
                "acquired": datetime(2014, 2, 4),
                "last_verified": datetime(2026, 3, 1),
                "category": "INSTITUTIONAL_LEADERSHIP",
                "valid_until": None
            },
        ]
    },
    
    # CASE 11: Twitter verification
    {
        "query": "How does Twitter verification work?",
        "entries": [
            {
                "text": "Twitter blue checkmarks verify notable public figures, journalists, and organizations for free.",
                "acquired": datetime(2021, 1, 1),                
                "category": "CURRENT_EVENT",
                "valid_until": datetime(2023, 3, 31)
            },
            {
                "text": "X verification now works as a paid subscription called X Blue. "
                        "Free legacy checkmarks were removed.",
                "acquired": datetime(2023, 4, 1),
                "last_verified": datetime(2026, 3, 1),   
                "category": "CURRENT_EVENT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 12: COVID status
    {
        "query": "What is the status of COVID-19?",
        "entries": [
            {
                "text": "COVID-19 is a global pandemic with widespread lockdowns and emergency measures worldwide.",
                "acquired": datetime(2020, 6, 1),
                "category": "CURRENT_EVENT",
                "valid_until": datetime(2023, 5, 10)
            },
            {
                "text": "COVID-19 pandemic emergency status ended in May 2023. "
                        "The WHO and US government declared the public health emergency over.",
                "acquired": datetime(2023, 5, 11),
                "last_verified": datetime(2026, 3, 1),   
                "category": "CURRENT_EVENT",
                "valid_until": None
            },
        ]
    },
    
    # STABLE FACTS - decay should NOT hurt these
    
    # CASE 13: Speed of light
    {
        "query": "What is the speed of light?",
        "entries": [
            {
                "text": "Light travels at approximately 299,792,458 meters per second in vacuum.",
                "acquired": datetime(2018, 1, 1),
                "category": "PHYSICAL_LAW",
                "valid_until": None
            },
        ]
    },
    
    # CASE 14: Capital of France
    {
        "query": "What is the capital of France?",
        "entries": [
            {
                "text": "Paris is the capital city of France and seat of government.",
                "acquired": datetime(2019, 1, 1),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 15: Shakespeare
    {
        "query": "Who wrote Hamlet?",
        "entries": [
            {
                "text": "William Shakespeare wrote the tragedy Hamlet in the early 17th century.",
                "acquired": datetime(2017, 1, 1),
                "category": "HISTORICAL_SEAL",
                "valid_until": None
            },
        ]
    },
    
    # CASE 16: Pythagorean theorem
    {
        "query": "What is the Pythagorean theorem?",
        "entries": [
            {
                "text": "In a right triangle, the square of the hypotenuse equals the sum of squares of the other sides.",
                "acquired": datetime(2016, 1, 1),
                "category": "MATHEMATICAL_TRUTH",
                "valid_until": None
            },
        ]
    },
    
    # CASE 17: Water boiling point
    {
        "query": "At what temperature does water boil?",
        "entries": [
            {
                "text": "Water boils at 100 degrees Celsius or 212 degrees Fahrenheit at sea level.",
                "acquired": datetime(2015, 1, 1),
                "category": "PHYSICAL_LAW",
                "valid_until": None
            },
        ]
    },
    
    # CASE 18: Mount Everest
    {
        "query": "What is the tallest mountain?",
        "entries": [
            {
                "text": "Mount Everest is the tallest mountain on Earth at 8,849 meters above sea level.",
                "acquired": datetime(2020, 1, 1),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 19: Earth's moon
    {
        "query": "How many moons does Earth have?",
        "entries": [
            {
                "text": "Earth has one natural satellite called the Moon.",
                "acquired": datetime(2018, 1, 1),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 20: Pi value
    {
        "query": "What is the value of pi?",
        "entries": [
            {
                "text": "Pi equals approximately 3.14159, the ratio of circumference to diameter.",
                "acquired": datetime(2019, 1, 1),
                "category": "MATHEMATICAL_TRUTH",
                "valid_until": None
            },
        ]
    },
    
    # CASE 21: Capital of Germany
    {
        "query": "What is the capital of Germany?",
        "entries": [
            {
                "text": "The capital of Germany is Berlin.",
                "acquired": datetime(2020, 1, 1),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 22: Amazon rainforest location
    {
        "query": "Where is the Amazon rainforest?",
        "entries": [
            {
                "text": "The Amazon rainforest is in South America.",
                "acquired": datetime(2018, 6, 1),
                "category": "GEOGRAPHIC_FACT",
                "valid_until": None
            },
        ]
    },
    
    # CASE 23: DNA structure
    {
        "query": "What is the structure of DNA?",
        "entries": [
            {
                "text": "DNA is double-stranded.",
                "acquired": datetime(2017, 3, 15),
                "category": "PHYSICAL_LAW",
                "valid_until": None
            },
        ]
    },
]
