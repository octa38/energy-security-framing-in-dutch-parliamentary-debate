# ParlaMint-NL - Energy Security Framing Analysis

## Project Overview

This project analyses how energy is framed as a security issue in Dutch parliamentary debates (2019–2022) using the ParlaMint-NL dataset.

The central research question is:
 *To what extent has energy policy discourse in the Dutch Parliament become securitized, particularly after the 2022 Russian invasion of Ukraine?*

The project combines:
* data engineering (text processing + enrichment)
* data visualisation (interactive dashboard)
* advanced analytics (statistical tests, clustering, trends)
* generative AI (speech interpretation and reporting)
---

## Scope of the Project

### Temporal scope

* 2019–2022 parliamentary debates
* Key geopolitical turning point: **February 24, 2022 (Russia invades Ukraine)**

### Substantive scope

The analysis focuses on energy-related discourse, specifically when it intersects with:
* Security
* Economics
* Climate
* Critical raw materials

### Unit of analysis

* Utterances (speech segments) from parliamentary debates

---

##  Analytical Pillar

This project is built on the “Climate, Energy, Materials & Food” pillar.

This means that energy is not treated purely as a technical or economic issue. Instead, it is analysed as a strategic, geopolitical, and security concern

The framework captures whether energy is framed in terms of:
* vulnerability
* dependency (e.g. on Russia)
* resilience
* national or European security

---

##  Methodology

### 1. Data Processing

Script: `process_parlamint.py`
* Text normalization (lowercasing, punctuation removal)
* Stopword removal and lemmatization
* Phrase-aware keyword matching
* Calculation of: keyword counts, density scores (per 1,000 words)

This produces:
```
processed/energy_security_utterances.csv
```

---

### 2. Metadata Enrichment

Script: `enrich_speakers.py`

* Extracts speaker metadata from TEI/XML:
  * name
  * party
  * gender
  * role
* Links metadata to utterances

Output:
```
processed/energy_security_utterances_enriched.csv
```

---

### 3. Framing Measurement

Each utterance is scored across five dimensions:
* Energy
* Security
* Economic
* Climate
* Critical Materials

Derived indicators:
* Primary framing
* Energy–Security overlap
* Securitization index
* Frame density scores

---

### 4. Advanced Analytics

Script: `advanced_analysis_energy_security.py`

Implements:
* Descriptive statistics
* Frame frequency & co-occurrence
* Trend analysis (yearly & monthly)
* Pre/post 2022 statistical tests
* Correlation analysis
* Speaker & party analysis
* Speech clustering (KMeans)
* Speaker clustering

Outputs:
```
analysis_outputs/
```

---

### 5. Dashboard

App: `app.py`

Interactive Streamlit dashboard featuring:
* framing trends over time
* securitization indicators
* actor-level analysis
* qualitative search interface
* AI-assisted interpretation

---

### 6. Generative AI Component

The dashboard integrates AI to:
* summarise speeches
* generate structured policy reports
* infer political orientation from language

This supports qualitative interpretation alongside quantitative analysis.

---

##  Key Insights

### 1. Strong increase in securitization after 2022

* Security framing increases significantly after the invasion of Ukraine
* Energy becomes tied to geopolitics and strategic vulnerability

### 2. Energy–security overlap rises

* A growing share of utterances combine both frames
* Indicates a shift from policy → strategy discourse

### 3. Dependency narratives dominate

* Frequent references to:
  * Russia
  * gas supply
  * LNG alternatives
* Emphasis on reducing external dependence

### 4. Actor-level differences

* Some speakers consistently use securitized framing
* Variation across parties suggests political positioning

### 5. Multi-dimensional framing

* Energy debates increasingly combine:
  * security + economic concerns
  * climate + strategic autonomy
---

## Data Architecture

A star schema is designed to support scalable querying:

* Fact table: `fact_utterance`
* Dimensions:
  * date
  * session
  * speaker
  * party
* Bridge table:
  * speaker-party (handles party switching)
This enables complex analytical queries across time and actors.

---

##  How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Project Structure

```
processed/                 → cleaned datasets
analysis_outputs/          → advanced analytics results
app.py                     → dashboard
process_parlamint.py       → preprocessing
enrich_speakers.py         → metadata enrichment
advanced_analysis_energy_security.py → analytics pipeline
```

---

## Limitations

* Keyword-based approach (may miss implicit framing)
* Party metadata incomplete in some cases

---

##  Conclusion

This project demonstrates that:

> **Energy discourse in Dutch parliament has become increasingly securitized, especially after 2022, reflecting broader geopolitical shifts in Europe.**

It combines quantitative accuracy with qualitative interpretation, aligned with HCSS analytical standards.
