export const nb = {
  nav: {
    last_opp: "Last opp",
    bibliotek: "Bibliotek",
    trening: "Trening",
    eksamen: "Eksamen",
    oversikt: "Oversikt",
  },
  upload: {
    title: "Last opp masteroppgaven",
    drop: "Dra PDF-en hit, eller velg fil",
    analysing: "Analyserer oppgaven. Dette tar noen minutter og gjøres bare én gang.",
    cached: "Denne oppgaven er analysert fra før. Innholdet hentes fra databasen.",
  },
  drill: {
    start: "Start trening",
    record: "Ta opp svar",
    stop: "Stopp opptak",
    listening: "Hører etter …",
    transcribing: "Skriver ut svaret …",
    grading: "Vurderer svaret …",
    model_answer: "Vis eksempelsvar",
    why: "Hvorfor spørsmålet stilles",
    follow_up: "Still oppfølgingsspørsmål",
    next: "Neste spørsmål",
  },
  exam: {
    start: "Start eksamenssimulering",
    running: "Sesjonen pågår. Du får tilbakemelding når den er ferdig.",
    end: "Avslutt sesjonen",
    ended: "Sesjonen er avsluttet. Rapporten er klar om et par minutter.",
  },
  scores: {
    korrekthet: "Korrekthet",
    begrunnelse: "Begrunnelse",
    forbehold: "Forbehold og begrensninger",
    struktur: "Struktur og presisjon",
  },
  delivery: {
    duration: "Varighet",
    wpm: "Ord per minutt",
    fillers: "Fyllord",
    pause: "Lengste pause",
  },
  empty: {
    sessions: "Ingen sesjoner ennå. Start med en kort treningsrunde på ti spørsmål.",
    weakest: "Ikke nok data ennå. Svar på minst ti spørsmål.",
  },
  errors: {
    mic: "Fikk ikke tilgang til mikrofonen. Sjekk nettleserinnstillingene.",
    stt: "Klarte ikke å skrive ut svaret. Opptaket er lagret — prøv på nytt.",
    upload: "Opplastingen feilet. Filen må være en PDF under 50 MB.",
  },
} as const;
