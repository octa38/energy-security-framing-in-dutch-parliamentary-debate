"""
ParlaMint-NL Energy Security Framing Analysis
Processes ParlaMint-NL English .txt/.tsv files into a clean CSV.
"""

import re
import csv
import argparse
from pathlib import Path
from collections import Counter

import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords


# ---------------------------------------------------------------------------
# KEYWORD DICTIONARIES
# ---------------------------------------------------------------------------

ENERGY_KEYWORDS = [
    # Core energy sources and carriers
    "energy", "energy supply", "energy system", "energy market",
    "gas", "natural gas", "gas supply", "gas price", "gas prices",
    "lng", "liquefied natural gas", "oil", "crude oil", "petroleum",
    "coal", "electricity", "electricity supply", "electricity market",
    "nuclear energy",

    # Renewables and transition
    "renewable energy", "renewables", "solar energy", "solar panel",
    "wind energy", "wind turbine", "offshore wind", "onshore wind",
    "hydrogen", "green hydrogen", "blue hydrogen",
    "energy transition", "energy mix", "energy policy",
    "energy strategy", "energy act", "energy law",
    "fossil fuel", "fossil fuels", "decarbonisation", "decarbonization",

    # Infrastructure
    "pipeline", "gas pipeline", "nord stream", "interconnector",
    "power grid", "electricity grid", "electricity network",
    "energy grid", "smart grid", "distribution network",
    "transmission grid",

    # Heat and efficiency
    "district heating", "heat pump", "energy efficiency",
    "energy storage", "battery storage", "demand response",

    # Energy affordability / crisis
    "energy dependence", "energy dependency", "energy independence",
    "energy security", "energy poverty", "affordable energy",
    "energy price", "energy prices", "energy cost", "energy costs",
    "energy bill", "energy bills", "energy crisis",
    "blackout", "brownout", "power outage",

    # Dutch-specific energy actors / places
    "groningen gas", "groningen field", "slochteren",
    "gasunie", "tennet", "nam", "shell", "equinor",
    "vattenfall", "eneco", "essent",
]

SECURITY_KEYWORDS = [
    # Core security concepts
    "national security", "collective security", "hard security",
    "security policy", "security threat", "security risk",
    "strategic autonomy", "strategic interest", "strategic dependence",
    "strategic dependency", "strategic concept",
    "geopolitical", "geopolitics", "geopolitical situation",
    "geopolitical tension", "geopolitical tensions",
    "geoeconomic", "geoeconomics",

    # Dependency and vulnerability
    "dependency", "dependence", "over-reliance", "reliance on",
    "strategic vulnerability", "critical dependency",
    "choke point", "bottleneck", "economic coercion",
    "weaponization", "weaponisation", "weaponized", "weaponised",

    # Institutions and alliances
    "nato", "european union", "security council", "un security council",
    "osce", "military alliance", "allied security",
    "article 5", "collective defence", "collective defense",
    "burden sharing", "defence spending", "defense spending",
    "defence budget", "defense budget", "military spending",

    # Military / defence
    "armed forces", "military expenditure", "military capability",
    "military capabilities", "military capacity", "military threat",
    "defence", "defense", "deterrence", "nuclear deterrence",
    "extended deterrence", "arms control", "disarmament",
    "hybrid warfare", "information warfare", "cyberattack",
    "sabotage", "espionage", "intelligence gathering",

    # Threat landscape
    "threat perception", "threat assessment", "security threat",
    "military threat", "aggression", "provocation",
    "destabilisation", "destabilization",
    "disinformation", "propaganda", "foreign interference",
    "influence operation",

    # Conflict and actors
    "russia", "russian federation", "ukraine", "ukrainian",
    "china", "chinese", "iran", "north korea",
    "war in ukraine", "war in europe", "invasion of ukraine",
    "occupation", "annexation", "crimea", "donbas",
    "sanctions", "counter-sanctions", "embargo",
    "weapons system", "weapon systems", "arms export",

    # Resilience and sovereignty
    "sovereignty", "territorial integrity",
    "critical infrastructure", "supply chain security",
    "supply chain resilience", "strategic reserve",
    "crisis management", "civil protection",
    "continuity of government",
]

ECONOMIC_KEYWORDS = [
    # Prices and affordability
    "energy price", "energy prices", "gas price", "gas prices",
    "electricity price", "electricity prices",
    "cost of living", "purchasing power",
    "inflation", "interest rate",

    # Trade and flows
    "trade balance", "trade deficit", "trade surplus",
    "import dependence", "export dependence",
    "imports", "exports", "tariff", "trade war",
    "protectionism", "free trade", "single market",

    # Macro / public finance
    "economic growth", "economic impact", "economic policy",
    "gdp", "recession", "public finance", "budget deficit",
    "public debt",

    # Households and welfare
    "household income", "household costs", "consumer prices",
    "wages", "poverty", "inequality", "welfare state",

    # Industry and investment
    "industrial policy", "manufacturing industry",
    "industrial production", "competitiveness",
    "market position", "market share",
    "foreign direct investment", "public investment",
    "infrastructure investment", "state aid",
    "subsidy", "subsidies",

    # Finance
    "banking sector", "credit market", "sovereign wealth fund",

    # Supply chains
    "supply chain", "supply chains", "logistics",
    "shipping", "freight", "container shipping",
    "reshoring", "nearshoring", "friend-shoring", "onshoring",
]

CLIMATE_KEYWORDS = [
    # Climate science / impacts
    "climate change", "climate crisis", "climate emergency",
    "global warming", "1.5 degrees", "2 degrees",
    "tipping point", "sea level rise", "permafrost",
    "extreme weather", "drought", "flood", "wildfire",

    # Emissions
    "co2", "carbon dioxide", "methane", "greenhouse gas",
    "greenhouse gases", "ghg", "emissions",
    "carbon footprint", "carbon budget", "carbon price",
    "carbon tax", "emissions trading", "carbon market",
    "carbon border adjustment", "cbam",

    # Policy frameworks
    "paris agreement", "paris accord", "cop26", "cop27", "cop28",
    "ipcc", "unfccc", "net zero", "net-zero",
    "carbon neutral", "carbon neutrality",
    "climate neutral", "climate target",
    "nationally determined contribution",

    # EU climate policy
    "european green deal", "green deal", "fit for 55",
    "sustainable finance", "green bond", "just transition",
    "coal phase-out", "methane regulation",

    # Environment
    "biodiversity", "deforestation", "ecosystem",
    "sustainability", "sustainable development",
    "circular economy",
]

MINERALS_KEYWORDS = [
    # Policy framing
    "critical minerals", "critical raw materials",
    "raw materials security", "strategic raw materials",
    "strategic materials", "resource security",
    "mineral security", "material security",
    "critical material", "critical materials",
    "scarce material", "scarce materials",

    # Specific minerals
    "rare earths", "rare earth elements",
    "lithium", "cobalt", "nickel", "graphite",
    "manganese", "gallium", "germanium", "indium",
    "tungsten", "molybdenum", "titanium", "vanadium",
    "platinum", "palladium", "iridium", "rhodium",
    "bauxite", "aluminium", "aluminum",

    # Technology applications when linked to material dependency
    "semiconductor supply", "semiconductor shortage",
    "chip shortage", "microchip shortage",
    "battery materials", "battery raw materials",
    "battery cell", "cathode", "anode",
    "permanent magnet", "wind turbine magnet",
    "ev battery",

    # Extraction and processing, made specific
    "mining", "mineral extraction", "raw material extraction",
    "lithium mining", "cobalt mining", "rare earth mining",
    "mineral refining", "raw material refining",
    "mineral processing", "raw material processing",
    "smelting",

    # Geography / dependency
    "dependence on china", "dependency on china",
    "chinese supply", "china dominance",
    "concentration risk", "single source supplier",
    "democratic republic of congo", "drc cobalt",
    "chile lithium", "indonesia nickel",
    "australia lithium",

    # Policy responses
    "urban mining", "critical minerals act",
    "critical raw materials act", "european chips act",
    "chips act", "stockpiling critical materials",
]

ALL_KEYWORDS = list(set(
    ENERGY_KEYWORDS + SECURITY_KEYWORDS + ECONOMIC_KEYWORDS + CLIMATE_KEYWORDS + MINERALS_KEYWORDS
))


# ---------------------------------------------------------------------------
# NLTK SETUP
# ---------------------------------------------------------------------------

def ensure_nltk_resource(resource_path: str, download_name: str) -> None:
    try:
        nltk.data.find(resource_path)
    except LookupError:
        nltk.download(download_name)


ensure_nltk_resource("corpora/wordnet", "wordnet")
ensure_nltk_resource("corpora/stopwords", "stopwords")

LEMMATIZER = WordNetLemmatizer()

STOPWORDS = set(stopwords.words("english")) | {
    "mr", "mrs", "chairman", "president", "minister", "secretary",
    "state", "government", "chamber", "house", "thank", "thanks",
    "question", "answer", "floor", "continue", "debate"
}


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Normalize text for matching:
    - lowercase
    - remove punctuation except % and hyphen
    - remove stopwords
    - lemmatize tokens
    """
    text = text.lower()
    text = re.sub(r"[^a-zA-Z0-9%\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    tokens = []
    for token in text.split():
        if token in STOPWORDS:
            continue
        tokens.append(LEMMATIZER.lemmatize(token))

    return " ".join(tokens)


def normalize_keyword(keyword: str) -> str:
    """Apply the same normalization to keyword phrases as to text."""
    return normalize_text(keyword)


def compile_keyword_patterns(keywords: list[str]) -> list[re.Pattern]:
    """Precompile regex patterns for efficient phrase-aware matching."""
    normalized_keywords = sorted(
        {normalize_keyword(kw) for kw in keywords if normalize_keyword(kw)},
        key=len,
        reverse=True,
    )

    return [re.compile(r"\b" + re.escape(kw) + r"\b") for kw in normalized_keywords]


ENERGY_PATTERNS = compile_keyword_patterns(ENERGY_KEYWORDS)
SECURITY_PATTERNS = compile_keyword_patterns(SECURITY_KEYWORDS)
ECONOMIC_PATTERNS = compile_keyword_patterns(ECONOMIC_KEYWORDS)
CLIMATE_PATTERNS = compile_keyword_patterns(CLIMATE_KEYWORDS)
MINERALS_PATTERNS = compile_keyword_patterns(MINERALS_KEYWORDS)
ALL_PATTERNS = compile_keyword_patterns(ALL_KEYWORDS)


def count_patterns(normalized_text: str, patterns: list[re.Pattern]) -> int:
    """Count keyword/phrase matches in already-normalized text."""
    return sum(len(pattern.findall(normalized_text)) for pattern in patterns)


def contains_patterns(normalized_text: str, patterns: list[re.Pattern]) -> bool:
    """Return True if any pattern appears in already-normalized text."""
    return any(pattern.search(normalized_text) for pattern in patterns)


def safe_density(score: int, word_count: int) -> float:
    """Keyword hits per 1,000 normalized words."""
    if word_count == 0:
        return 0.0
    return round((score / word_count) * 1000, 4)


def classify_framing_from_scores(
    energy_score: int,
    security_score: int,
    economic_score: int,
    climate_score: int,
    minerals_score: int,
) -> str:
    """Return the dominant framing label from keyword scores."""
    scores = {
        "security": security_score,
        "economic": economic_score,
        "climate": climate_score,
        "minerals": minerals_score,
        "energy-general": energy_score,
    }

    if max(scores.values()) == 0:
        return "other"

    return max(scores, key=scores.get)


def parse_date_from_filename(fname: str) -> str | None:
    """Extract ISO date from filenames like ParlaMint-NL-en_2022-07-11-..."""
    match = re.search(r"(\d{4}-\d{2}-\d{2})", fname)
    return match.group(1) if match else None


def parse_chamber_from_filename(fname: str) -> str:
    """Detect eerstekamer / tweedekamer from filename."""
    fname_lower = fname.lower()
    if "eerstekamer" in fname_lower:
        return "Eerste Kamer"
    if "tweedekamer" in fname_lower:
        return "Tweede Kamer"
    return "Unknown"


def parse_utterances(filepath: Path) -> list[dict]:
    """Parse a single ParlaMint .txt/.tsv file into a list of utterance dicts."""
    fname = filepath.name
    date_str = parse_date_from_filename(fname)
    chamber = parse_chamber_from_filename(fname)
    session_id = fname.replace(".txt", "").replace(".tsv", "")

    utterances = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Format: <utterance_id>\t<text>
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue

            utt_id, raw_text = parts[0].strip(), parts[1].strip()

            normalized_text = normalize_text(raw_text)
            word_count = len(normalized_text.split())

            # Only remove ultra-short procedural lines; short substantive interruptions are kept.
            if word_count < 5:
                continue


            energy_score = count_patterns(normalized_text, ENERGY_PATTERNS)
            security_score = count_patterns(normalized_text, SECURITY_PATTERNS)
            economic_score = count_patterns(normalized_text, ECONOMIC_PATTERNS)
            climate_score = count_patterns(normalized_text, CLIMATE_PATTERNS)
            minerals_score = count_patterns(normalized_text, MINERALS_PATTERNS)

            # Only keep utterances that are actually about energy or minerals
            if energy_score == 0 and minerals_score == 0:
                continue

            total_frame_score = security_score + economic_score + climate_score + minerals_score
            securitization_index = security_score / (economic_score + climate_score + minerals_score + 1)

            utterances.append({
                "utterance_id": utt_id,
                "session_id": session_id,
                "date": date_str,
                "year": date_str[:4] if date_str else None,
                "month": date_str[:7] if date_str else None,
                "chamber": chamber,

                # Keep both raw and normalized text.
                "text": raw_text,
                "normalized_text": normalized_text,
                "word_count": word_count,

                # Raw keyword scores.
                "energy_score": energy_score,
                "security_score": security_score,
                "economic_score": economic_score,
                "climate_score": climate_score,
                "minerals_score": minerals_score,

                # Length-normalized keyword densities.
                "energy_density": safe_density(energy_score, word_count),
                "security_density": safe_density(security_score, word_count),
                "economic_density": safe_density(economic_score, word_count),
                "climate_density": safe_density(climate_score, word_count),
                "minerals_density": safe_density(minerals_score, word_count),

                # Composite indicators.
                "total_frame_score": total_frame_score,
                "securitization_index": round(securitization_index, 4),

                # Labels.
                "primary_framing": classify_framing_from_scores(
                    energy_score,
                    security_score,
                    economic_score,
                    climate_score,
                    minerals_score,
                ),
                "is_energy_security": energy_score > 0 and security_score > 0,
                "is_energy_minerals": energy_score > 0 and minerals_score > 0,
                "is_security_heavy": security_score >= 3,
            })

    return utterances


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Process ParlaMint-NL .txt/.tsv files")
    parser.add_argument("--data_dir", required=True, help="Root folder, e.g. ./ParlaMint-NL-en.txt")
    parser.add_argument("--out_dir", default="./processed", help="Output folder")
    parser.add_argument(
        "--years",
        nargs="+",
        default=["2019", "2020", "2021", "2022"],
        help="Only process files from these year subfolders (default: 2019-2022)",
    )
    args = parser.parse_args()

    out_path = Path(args.out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    csv_file = out_path / "energy_security_utterances.csv"

    data_dir = Path(args.data_dir)

    txt_files = []
    for year in args.years:
        year_dir = data_dir / year
        if not year_dir.exists():
            print(f"Warning: year folder '{year_dir}' not found, skipping")
            continue
        txt_files.extend(sorted(year_dir.glob("*.txt")))
        txt_files.extend(sorted(year_dir.glob("*.tsv")))

    print(f"Found {len(txt_files)} files to process...")

    all_rows = []
    for i, fp in enumerate(txt_files, start=1):
        all_rows.extend(parse_utterances(fp))
        if i % 50 == 0:
            print(f"Processed {i}/{len(txt_files)} files, {len(all_rows)} utterances so far")

    print(f"\nTotal relevant utterances: {len(all_rows)}")
    print(f"Writing to {csv_file}...")

    if not all_rows:
        print("No rows found — check your --data_dir path and file contents.")
        return

    fieldnames = list(all_rows[0].keys())
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print("\nDone! Summary:")
    framing_counts = Counter(r["primary_framing"] for r in all_rows)
    for label, count in framing_counts.most_common():
        print(f"  {label}: {count}")

    energy_security_count = sum(1 for r in all_rows if r["is_energy_security"])
    energy_minerals_count = sum(1 for r in all_rows if r["is_energy_minerals"])

    print(f"  Energy+Security overlap: {energy_security_count}")
    print(f"  Energy+Minerals overlap: {energy_minerals_count}")


if __name__ == "__main__":
    main()
