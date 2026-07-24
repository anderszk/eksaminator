You are an expert in pharmacy and health science oral defence preparation at Norwegian universities. Generate a comprehensive question bank for this master's thesis defence.

REQUIREMENTS:
- Generate 120-180 questions total
- Fill the full category × difficulty grid
- Minimum 4 questions per category
- Minimum 25 questions at difficulty 4
- All questions in Norwegian bokmål (keep technical English terms as-is)
- Each question must be ≤ 40 words and phrased as a spoken question
- No compound multi-part questions
- Natural spoken Norwegian, not written academic register

CATEGORIES (use exactly these keys):
- motivasjon: Why this research question, why it matters
- metodevalg: Justification vs alternatives  
- metodeforstaelse: Mechanics, assumptions, failure modes
- resultater: Per figure/table results
- statistikk: Statistics and experimental design
- validitet: Controls, bias, confounders
- alternativ: Adversarial alternative explanations
- litteratur: Literature and positioning
- relevans: Clinical/pharmaceutical relevance
- etikk: Ethics and regulations (REK, personvern, dyrevelferd)
- reproduserbarhet: Reproducibility
- grunnlag: Fundamentals beneath the method (drop one level)
- videre: Further work
- kritisk: Premise-challenging questions (must challenge the premise, not just ask harder)

DIFFICULTY TIERS (use integer 1-4):
1 = gjenkalle: State a fact from your own work
2 = forklare: Explain a mechanism or a choice
3 = forsvare: Defend a choice against a named alternative
4 = motstå: Hold up under a challenged premise

ANSWER SHAPES (use exactly these values):
- direkte: påstand → belegg → forbehold (claim → evidence → boundary condition)
- utfordre: anerkjenn → omformuler → forsvar
- innrommelse: innrøm rent → resonner høyt → stopp

Return ONLY a JSON array — no prose, no markdown fences:

[
  {
    "category": "metodevalg",
    "difficulty": 3,
    "text": "Spørsmålstekst på norsk, ≤40 ord, som en sensor ville stille muntlig",
    "why_asked": "Én setning som forklarer hva sensoren tester, på norsk",
    "expected_shape": "direkte|utfordre|innrommelse",
    "source_refs": [{"page": 24, "section_path": "3. Metode > 3.2 HPLC-analyse"}],
    "follow_ups": [
      "Oppfølgingsspørsmål 1 som eskalerer hvis svaret var tynt",
      "Oppfølgingsspørsmål 2"
    ]
  }
]

STRUCTURE MAP:
{{structure_map}}

CLAIMS:
{{claims}}

VULNERABILITIES:
{{vulnerabilities}}
