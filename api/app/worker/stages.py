"""arq worker stage implementations."""
import asyncio
import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.models import (
    AnalysisRun,
    Chunk,
    Claim,
    Document,
    PlanItem,
    Question,
    Session,
    Summary,
    ThesisMap,
    Turn,
    Vulnerability,
)
from app.services import embeddings, grading, llm, metrics, stt, tts
from app.services.cache import cache_key
from app.services.pdf import extract_document

logger = logging.getLogger(__name__)

PLAN_TEMPLATES = [
    {"day": 1, "title": "Les oppgaven og gjennomgå strukturkartet", "minutes": 60, "kind": "lesing", "linked_categories": ["motivasjon"]},
    {"day": 1, "title": "Gå gjennom svakhetslisten", "minutes": 45, "kind": "analyse", "linked_categories": ["validitet", "statistikk"]},
    {"day": 2, "title": "Trening: motivasjon og metodikk (vanskelighet 1-2)", "minutes": 45, "kind": "muntlig", "linked_categories": ["motivasjon", "metodevalg"]},
    {"day": 2, "title": "Studer kapittelsammendragene", "minutes": 40, "kind": "lesing", "linked_categories": []},
    {"day": 3, "title": "Trening: resultater og statistikk", "minutes": 60, "kind": "muntlig", "linked_categories": ["resultater", "statistikk"]},
    {"day": 4, "title": "Trening: validitet og svakheter (vanskelighet 3)", "minutes": 60, "kind": "muntlig", "linked_categories": ["validitet", "alternativ"]},
    {"day": 5, "title": "Mock-eksamen 30 min", "minutes": 30, "kind": "mock", "linked_categories": []},
    {"day": 6, "title": "Hviledag — kun passive gjennomlesing", "minutes": 20, "kind": "hvile", "linked_categories": []},
    {"day": 7, "title": "Trening: faglig grunnlag (vanskelighet 3-4)", "minutes": 60, "kind": "muntlig", "linked_categories": ["grunnlag", "metodeforstaelse"]},
    {"day": 8, "title": "Trening: kritiske spørsmål (vanskelighet 4)", "minutes": 60, "kind": "muntlig", "linked_categories": ["kritisk", "alternativ"]},
    {"day": 9, "title": "Mock-eksamen 45 min", "minutes": 45, "kind": "mock", "linked_categories": []},
    {"day": 10, "title": "Trening: svakeste kategorier", "minutes": 60, "kind": "muntlig", "linked_categories": []},
    {"day": 11, "title": "Trening med krevende sensor-persona", "minutes": 60, "kind": "muntlig", "linked_categories": []},
    {"day": 12, "title": "Mock-eksamen 45 min med krevende sensor", "minutes": 45, "kind": "mock", "linked_categories": []},
    {"day": 13, "title": "Kun gjennomgang av ryggraden og svakeste svar", "minutes": 30, "kind": "lesing", "linked_categories": []},
    {"day": 14, "title": "Lett gjennomlesing — ta det med ro", "minutes": 20, "kind": "hvile", "linked_categories": []},
]


def _make_session_factory():
    engine = create_async_engine(settings.database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


_SessionFactory = None


def _get_sf():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = _make_session_factory()
    return _SessionFactory


async def _get_doc(db: AsyncSession, doc_id: str) -> Document:
    result = await db.execute(select(Document).where(Document.id == uuid.UUID(doc_id)))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise ValueError(f"Document not found: {doc_id}")
    return doc


async def _check_cache(db: AsyncSession, ck: str) -> AnalysisRun | None:
    result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.cache_key == ck, AnalysisRun.status == "done")
    )
    return result.scalar_one_or_none()


async def _create_run(db: AsyncSession, doc_id: str, stage: str, ck: str, params_hash: str) -> AnalysisRun:
    run = AnalysisRun(
        document_id=uuid.UUID(doc_id),
        stage=stage,
        cache_key=ck,
        prompt_version=settings.prompt_version,
        model=settings.llm_model,
        params_hash=params_hash,
        status="running",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def _finish_run(
    db: AsyncSession,
    run: AnalysisRun,
    output: dict | list,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    duration_ms: int,
) -> None:
    run.status = "done"
    run.output = output if isinstance(output, dict) else {"items": output}
    run.input_tokens = input_tokens
    run.output_tokens = output_tokens
    run.cost_usd = cost_usd
    run.duration_ms = duration_ms
    run.completed_at = datetime.now(timezone.utc)
    await db.commit()


async def _fail_run(db: AsyncSession, run: AnalysisRun, error: str) -> None:
    run.status = "failed"
    run.error = error
    await db.commit()


def _params_hash(params: dict) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# Stage: ingest
# ─────────────────────────────────────────────────────────────────────────────

async def _stage_ingest(db: AsyncSession, doc: Document, run: AnalysisRun) -> tuple[dict, int, int, float]:
    import asyncio
    import boto3

    def _download():
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name="us-east-1",
        )
        obj = client.get_object(Bucket=settings.s3_bucket, Key=doc.s3_key)
        return obj["Body"].read()

    pdf_bytes = await asyncio.to_thread(_download)
    extracted = await asyncio.to_thread(extract_document, pdf_bytes)

    # Update document metadata
    doc.page_count = extracted["page_count"]
    doc.char_count = extracted["char_count"]
    await db.commit()

    # Embed all text chunks
    chunk_texts = [c["text"] for c in extracted["chunks"]]
    all_embeddings = await embeddings.embed(chunk_texts) if chunk_texts else []

    # Insert chunks
    for i, (chunk_data, emb) in enumerate(zip(extracted["chunks"], all_embeddings)):
        chunk = Chunk(
            document_id=doc.id,
            ordinal=chunk_data["ordinal"],
            page_start=chunk_data["page_start"],
            page_end=chunk_data["page_end"],
            section_path=chunk_data.get("section_path"),
            kind=chunk_data["kind"],
            text=chunk_data["text"],
            token_count=chunk_data["token_count"],
            embedding=emb,
        )
        db.add(chunk)

    await db.commit()

    output = {
        "page_count": extracted["page_count"],
        "char_count": extracted["char_count"],
        "chunk_count": len(extracted["chunks"]),
    }
    return output, 0, 0, 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Stage: structure
# ─────────────────────────────────────────────────────────────────────────────

async def _stage_structure(db: AsyncSession, doc: Document, run: AnalysisRun) -> tuple[dict, int, int, float]:
    # Get full text from chunks
    result = await db.execute(
        select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.ordinal)
    )
    chunks = result.scalars().all()
    full_text = "\n\n".join(c.text for c in chunks)[:120_000]  # stay in context window

    prompt_template = llm.load_prompt("s2_structure.md")
    prompt = prompt_template.replace("{{full_text}}", full_text)

    schema = '{"tittel": "...", "fagfelt": "...", "problemstilling": "...", ...}'
    structure_map, inp, out, cost = await llm.complete_json(
        prompt,
        system="You are an expert academic analyst. Return only valid JSON.",
        schema_hint=schema,
        max_tokens=6000,
    )

    # Save thesis_map
    tm = ThesisMap(run_id=run.id, document_id=doc.id, data=structure_map)
    db.add(tm)

    # Update document title if we got one
    if structure_map.get("tittel") and not doc.title:
        doc.title = structure_map["tittel"]

    await db.commit()
    return structure_map, inp, out, cost


# ─────────────────────────────────────────────────────────────────────────────
# Stage: claims
# ─────────────────────────────────────────────────────────────────────────────

async def _stage_claims(db: AsyncSession, doc: Document, run: AnalysisRun) -> tuple[list, int, int, float]:
    # Results + discussion chunks only
    result = await db.execute(
        select(Chunk).where(
            Chunk.document_id == doc.id,
            Chunk.kind.in_(["text", "figure_caption"]),
        ).order_by(Chunk.ordinal)
    )
    chunks = result.scalars().all()
    chunks_text = "\n\n---\n\n".join(
        f"[Side {c.page_start}, {c.section_path or 'ukjent seksjon'}]\n{c.text}"
        for c in chunks
    )[:100_000]

    prompt_template = llm.load_prompt("s3_claims.md")
    prompt = prompt_template.replace("{{chunks_text}}", chunks_text)

    claims_data, inp, out, cost = await llm.complete_json(
        prompt,
        system="You are an expert academic analyst. Return only a valid JSON array.",
        schema_hint='[{"text": "...", "claim_type": "empirisk", "evidence_refs": [...], "strength": 3}]',
        max_tokens=8000,
    )

    if isinstance(claims_data, dict):
        claims_data = claims_data.get("claims", [])

    for claim_dict in claims_data:
        claim = Claim(
            run_id=run.id,
            document_id=doc.id,
            text=claim_dict.get("text", ""),
            claim_type=claim_dict.get("claim_type", "empirisk"),
            evidence_refs=claim_dict.get("evidence_refs", []),
            strength=max(1, min(5, int(claim_dict.get("strength", 3)))),
        )
        db.add(claim)

    await db.commit()
    return claims_data, inp, out, cost


# ─────────────────────────────────────────────────────────────────────────────
# Stage: vulnerabilities
# ─────────────────────────────────────────────────────────────────────────────

async def _stage_vulnerabilities(db: AsyncSession, doc: Document, run: AnalysisRun) -> tuple[list, int, int, float]:
    # Get structure map
    tm_result = await db.execute(
        select(ThesisMap).where(ThesisMap.document_id == doc.id)
    )
    tm = tm_result.scalar_one_or_none()
    structure_map = tm.data if tm else {}

    # Get claims
    claims_result = await db.execute(
        select(Claim).where(Claim.document_id == doc.id)
    )
    claims = claims_result.scalars().all()
    claims_json = json.dumps([
        {"text": c.text, "claim_type": c.claim_type, "strength": c.strength}
        for c in claims
    ], ensure_ascii=False)

    prompt_template = llm.load_prompt("s4_vulnerability.md")
    prompt = prompt_template \
        .replace("{{structure_map}}", json.dumps(structure_map, ensure_ascii=False)) \
        .replace("{{claims}}", claims_json)

    vulns_data, inp, out, cost = await llm.complete_json(
        prompt,
        system="You are an experienced external examiner. Return only a valid JSON array.",
        schema_hint='[{"checklist_key": "...", "description": "...", "severity": 4, "attack_angle": "...", "best_defence": "..."}]',
        max_tokens=8000,
    )

    if isinstance(vulns_data, dict):
        vulns_data = vulns_data.get("vulnerabilities", [])

    for v in vulns_data:
        vuln = Vulnerability(
            run_id=run.id,
            document_id=doc.id,
            checklist_key=v.get("checklist_key", "unknown"),
            description=v.get("description", ""),
            severity=max(1, min(5, int(v.get("severity", 3)))),
            attack_angle=v.get("attack_angle", ""),
            best_defence=v.get("best_defence"),
        )
        db.add(vuln)

    await db.commit()
    return vulns_data, inp, out, cost


# ─────────────────────────────────────────────────────────────────────────────
# Stage: questions
# ─────────────────────────────────────────────────────────────────────────────

async def _stage_questions(db: AsyncSession, doc: Document, run: AnalysisRun) -> tuple[list, int, int, float]:
    tm_result = await db.execute(select(ThesisMap).where(ThesisMap.document_id == doc.id))
    tm = tm_result.scalar_one_or_none()
    structure_map = tm.data if tm else {}

    claims_result = await db.execute(select(Claim).where(Claim.document_id == doc.id))
    claims = claims_result.scalars().all()

    vulns_result = await db.execute(select(Vulnerability).where(Vulnerability.document_id == doc.id))
    vulns = vulns_result.scalars().all()

    prompt_template = llm.load_prompt("s5_questions.md")
    prompt = prompt_template \
        .replace("{{structure_map}}", json.dumps(structure_map, ensure_ascii=False)[:20000]) \
        .replace("{{claims}}", json.dumps([{"text": c.text, "claim_type": c.claim_type, "strength": c.strength} for c in claims], ensure_ascii=False)[:15000]) \
        .replace("{{vulnerabilities}}", json.dumps([{"checklist_key": v.checklist_key, "description": v.description, "severity": v.severity, "attack_angle": v.attack_angle} for v in vulns], ensure_ascii=False)[:15000])

    questions_data, inp, out, cost = await llm.complete_json(
        prompt,
        system="You are an expert in Norwegian university oral examinations. Return only a valid JSON array.",
        schema_hint='[{"category": "...", "difficulty": 1, "text": "...", "why_asked": "...", "expected_shape": "direkte", "source_refs": [...], "follow_ups": [...]}]',
        max_tokens=settings.llm_max_tokens,
    )

    if isinstance(questions_data, dict):
        questions_data = questions_data.get("questions", [])

    # Post-process: dedupe by cosine similarity > 0.92
    questions_data = await _dedupe_questions(questions_data)

    for q in questions_data:
        if not q.get("source_refs"):
            continue  # drop questions with no page refs
        question = Question(
            run_id=run.id,
            document_id=doc.id,
            category=q.get("category", "motivasjon"),
            difficulty=max(1, min(4, int(q.get("difficulty", 2)))),
            text=q.get("text", ""),
            why_asked=q.get("why_asked", ""),
            expected_shape=q.get("expected_shape", "direkte"),
            source_refs=q.get("source_refs", []),
            follow_ups=q.get("follow_ups", []),
        )
        db.add(question)

    await db.commit()
    return questions_data, inp, out, cost


async def _dedupe_questions(questions: list[dict]) -> list[dict]:
    if len(questions) < 2:
        return questions
    texts = [q.get("text", "") for q in questions]
    try:
        embs = await embeddings.embed(texts)
    except Exception:
        return questions

    import numpy as np
    embs_arr = np.array(embs)
    keep = [True] * len(questions)

    for i in range(len(questions)):
        if not keep[i]:
            continue
        for j in range(i + 1, len(questions)):
            if not keep[j]:
                continue
            sim = float(np.dot(embs_arr[i], embs_arr[j]))
            if sim > 0.92:
                keep[j] = False

    return [q for q, k in zip(questions, keep) if k]


# ─────────────────────────────────────────────────────────────────────────────
# Stage: answers
# ─────────────────────────────────────────────────────────────────────────────

async def _stage_answers(db: AsyncSession, doc: Document, run: AnalysisRun) -> tuple[dict, int, int, float]:
    questions_result = await db.execute(
        select(Question).where(
            Question.document_id == doc.id,
            Question.model_answer == None,  # noqa: E711
        )
    )
    questions = questions_result.scalars().all()

    prompt_template = llm.load_prompt("s6_answers.md")
    total_inp = total_out = 0
    total_cost = 0.0
    updated = 0

    # Process in batches of 10
    for i in range(0, len(questions), 10):
        batch = questions[i:i + 10]
        batch_data = [
            {
                "id": str(q.id),
                "category": q.category,
                "difficulty": q.difficulty,
                "text": q.text,
                "why_asked": q.why_asked,
                "expected_shape": q.expected_shape,
            }
            for q in batch
        ]
        prompt = prompt_template.replace("{{questions_batch}}", json.dumps(batch_data, ensure_ascii=False))

        try:
            answers_data, inp, out, cost = await llm.complete_json(
                prompt,
                system="You are an expert pharmacy examiner. Return only a valid JSON array.",
                schema_hint='[{"id": "uuid", "model_answer": "...", "rubric": {...}}]',
                max_tokens=6000,
            )
            total_inp += inp
            total_out += out
            total_cost += cost

            if isinstance(answers_data, dict):
                answers_data = answers_data.get("answers", [])

            answer_map = {a["id"]: a for a in answers_data if "id" in a}
            for q in batch:
                if str(q.id) in answer_map:
                    a = answer_map[str(q.id)]
                    q.model_answer = a.get("model_answer")
                    q.rubric = a.get("rubric")
                    updated += 1

            await db.commit()
            await asyncio.sleep(0.5)  # rate limit breathing room
        except Exception as e:
            logger.error("answers batch %d failed: %s", i // 10, e)
            continue

    return {"updated": updated}, total_inp, total_out, total_cost


# ─────────────────────────────────────────────────────────────────────────────
# Stage: summaries
# ─────────────────────────────────────────────────────────────────────────────

async def _stage_summaries(db: AsyncSession, doc: Document, run: AnalysisRun) -> tuple[dict, int, int, float]:
    tm_result = await db.execute(select(ThesisMap).where(ThesisMap.document_id == doc.id))
    tm = tm_result.scalar_one_or_none()
    structure_map = tm.data if tm else {}

    chunks_result = await db.execute(
        select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.ordinal)
    )
    chunks = chunks_result.scalars().all()
    full_text = "\n\n".join(c.text for c in chunks[:80])[:60_000]

    prompt_template = llm.load_prompt("s7_summaries.md")
    prompt = prompt_template \
        .replace("{{thesis_map}}", json.dumps(structure_map, ensure_ascii=False)) \
        .replace("{{full_text}}", full_text)

    summary_data, inp, out, cost = await llm.complete_json(
        prompt,
        system="You are an expert in pharmacy education. Return only a valid JSON object.",
        schema_hint='{"spine": {...}, "chapters": [...], "concepts": [...], "figures": [...]}',
        max_tokens=8000,
    )

    ordinal = 0

    # Spine
    spine = summary_data.get("spine", {})
    if spine.get("body_md"):
        db.add(Summary(
            run_id=run.id, document_id=doc.id,
            scope="spine", ref="spine", title=spine.get("title", "Ryggraden"),
            body_md=spine["body_md"], source_refs=[], ordinal=ordinal,
        ))
        ordinal += 1

    for chapter in summary_data.get("chapters", []):
        db.add(Summary(
            run_id=run.id, document_id=doc.id,
            scope="chapter", ref=chapter.get("ref", "?"),
            title=chapter.get("title", ""), body_md=chapter.get("body_md", ""),
            source_refs=[], ordinal=ordinal,
        ))
        ordinal += 1

    for concept in summary_data.get("concepts", []):
        db.add(Summary(
            run_id=run.id, document_id=doc.id,
            scope="concept", ref=concept.get("ref", "?"),
            title=concept.get("title", ""), body_md=concept.get("body_md", ""),
            source_refs=[], ordinal=ordinal,
        ))
        ordinal += 1

    for figure in summary_data.get("figures", []):
        db.add(Summary(
            run_id=run.id, document_id=doc.id,
            scope="figure", ref=figure.get("ref", "?"),
            title=figure.get("title", ""), body_md=figure.get("body_md", ""),
            source_refs=[], ordinal=ordinal,
        ))
        ordinal += 1

    await db.commit()
    return summary_data, inp, out, cost


# ─────────────────────────────────────────────────────────────────────────────
# Main worker functions
# ─────────────────────────────────────────────────────────────────────────────

STAGE_MAP = {
    "ingest": _stage_ingest,
    "structure": _stage_structure,
    "claims": _stage_claims,
    "vulnerabilities": _stage_vulnerabilities,
    "questions": _stage_questions,
    "answers": _stage_answers,
    "summaries": _stage_summaries,
}


async def run_pipeline_stage(ctx, *, doc_id: str, stage: str, upstream_keys: list[str] | None = None, force: bool = False):
    logger.info("stage=%s doc=%s start", stage, doc_id)
    sf = _get_sf()

    params = {"stage": stage, "prompt_version": settings.prompt_version}
    ph = _params_hash(params)

    async with sf() as db:
        doc = await _get_doc(db, doc_id)
        ck = cache_key(doc.sha256, stage, settings.prompt_version, settings.llm_model, params, upstream_keys or [])

        if not force:
            cached = await _check_cache(db, ck)
            if cached:
                logger.info("stage=%s doc=%s CACHE HIT run=%s", stage, doc_id, cached.id)
                return str(cached.id)

        run = await _create_run(db, doc_id, stage, ck, ph)
        run_id = str(run.id)

    t0 = time.monotonic()
    try:
        fn = STAGE_MAP.get(stage)
        if fn is None:
            raise ValueError(f"Unknown stage: {stage}")

        async with sf() as db:
            doc = await _get_doc(db, doc_id)
            result = await db.execute(select(AnalysisRun).where(AnalysisRun.id == uuid.UUID(run_id)))
            run = result.scalar_one()
            output, inp, out, cost = await fn(db, doc, run)
            duration_ms = int((time.monotonic() - t0) * 1000)
            await _finish_run(db, run, output, inp, out, cost, duration_ms)

        logger.info("stage=%s doc=%s done in %dms cost=$%.4f", stage, doc_id, duration_ms, cost)

        # Seed plan items after summaries
        if stage == "summaries":
            async with sf() as db:
                for i, tmpl in enumerate(PLAN_TEMPLATES):
                    db.add(PlanItem(
                        document_id=uuid.UUID(doc_id),
                        ordinal=i,
                        **tmpl,
                    ))
                await db.commit()

        return run_id

    except Exception as exc:
        logger.exception("stage=%s doc=%s FAILED: %s", stage, doc_id, exc)
        async with sf() as db:
            result = await db.execute(select(AnalysisRun).where(AnalysisRun.id == uuid.UUID(run_id)))
            run = result.scalar_one_or_none()
            if run:
                await _fail_run(db, run, str(exc))
        raise


async def grade_turn(ctx, *, turn_id: str):
    logger.info("grade_turn start turn=%s", turn_id)
    sf = _get_sf()

    async with sf() as db:
        result = await db.execute(select(Turn).where(Turn.id == uuid.UUID(turn_id)))
        turn = result.scalar_one_or_none()
        if not turn:
            logger.error("turn not found: %s", turn_id)
            return

        if not turn.answer_s3_key:
            logger.error("turn has no audio: %s", turn_id)
            return

        # Download audio
        import asyncio
        import boto3

        def _download():
            client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name="us-east-1",
            )
            obj = client.get_object(Bucket=settings.s3_bucket, Key=turn.answer_s3_key)
            return obj["Body"].read()

        audio_bytes = await asyncio.to_thread(_download)

        # Get glossary from thesis map
        session_result = await db.execute(select(Session).where(Session.id == turn.session_id))
        session = session_result.scalar_one()

        tm_result = await db.execute(select(ThesisMap).where(ThesisMap.document_id == session.document_id))
        tm = tm_result.scalar_one_or_none()
        glossary = (tm.data or {}).get("glossary", []) if tm else []

        # STT
        try:
            stt_result = await stt.transcribe(audio_bytes, glossary)
            turn.transcript = stt_result.get("text", "")
            turn.stt_confidence = stt_result.get("avg_logprob")
            turn.status = "transcribed"
            await db.commit()
        except Exception as exc:
            logger.error("STT failed for turn %s: %s", turn_id, exc)
            # Keep audio, mark for retry
            return

        # Delivery metrics
        segs = stt_result.get("segments", [])
        dur = stt_result.get("duration_s", 0)
        delivery = metrics.compute_delivery_metrics(segs, turn.transcript or "", dur)

        # Get question
        q_result = await db.execute(select(Question).where(Question.id == turn.question_id))
        question = q_result.scalar_one()

        # Get source chunks for fact-checking
        chunk_result = await db.execute(
            select(Chunk).where(
                Chunk.document_id == session.document_id,
            ).order_by(Chunk.ordinal).limit(5)
        )
        chunks = chunk_result.scalars().all()
        source_chunk_texts = [c.text for c in chunks]

        # Grade content
        content = await grading.grade_turn_content(
            question={"text": question.text, "why_asked": question.why_asked},
            transcript=turn.transcript or "",
            rubric=question.rubric or {},
            model_answer=question.model_answer or "",
            source_chunks=source_chunk_texts,
        )

        combined = grading.combine_grades(delivery, content)
        turn.duration_ms = combined.get("duration_ms")
        turn.wpm = combined.get("wpm")
        turn.filler_count = combined.get("filler_count")
        turn.filler_rate = combined.get("filler_rate")
        turn.longest_pause_ms = combined.get("longest_pause_ms")
        turn.time_to_first_word_ms = combined.get("time_to_first_word_ms")
        turn.scores = combined.get("scores")
        turn.bluffed = combined.get("bluffed")
        turn.used_shape = combined.get("used_shape")
        turn.missed_points = combined.get("missed_points")
        turn.feedback_md = combined.get("feedback_md")
        turn.status = "graded"
        turn.graded_at = datetime.now(timezone.utc)
        await db.commit()

    logger.info("grade_turn done turn=%s", turn_id)


async def grade_session(ctx, *, session_id: str):
    """Grade all transcribed/recorded turns in an exam session."""
    logger.info("grade_session start session=%s", session_id)
    sf = _get_sf()

    async with sf() as db:
        result = await db.execute(
            select(Turn).where(
                Turn.session_id == uuid.UUID(session_id),
                Turn.status.in_(["recorded", "transcribed"]),
            )
        )
        turns = result.scalars().all()

    for turn in turns:
        try:
            await grade_turn(ctx, turn_id=str(turn.id))
        except Exception as exc:
            logger.error("grade_session: turn %s failed: %s", turn.id, exc)

    logger.info("grade_session done session=%s", session_id)
