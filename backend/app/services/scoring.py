"""5-stage multi-agent tailoring pipeline: Strategist -> Parallel Fan-Out -> Gatekeeper -> Assembler -> Pro Safety Valve."""

import asyncio
import json
import re
import traceback as tb
from typing import Any

from app.models import ParsedJD, ScoredUnit
from app.services.gemini import generate_json, generate_json_parallel

# ── Stage 1: Tactical Planner ──

STAGE1_PLANNER_PROMPT = """
You are an Elite Technical Resume Strategist. Create a document-wide "Battle Plan" for tailoring this resume to {company}.

COMPANY CONTEXT:
Company: {company}
Mission: {business_mission}
Strategic Pillars: {pillars_text}

RESUME BULLETS:
{bullets_json}

INSTRUCTIONS:
1. Map each bullet to a specific Strategic Pillar.
2. Assign a "Preferred Starting Verb" to each bullet from the Impact Vocabulary or Elite alternatives. Ensure high diversity across the document.
3. Assign a "Tone Focus" (e.g., "scalability", "user-centricity", "operational efficiency").

Return a JSON object:
{{
  "bullet_id": {{
    "pillar": "...",
    "preferred_verb": "...",
    "tone_focus": "..."
  }}
}}
"""

# ── Stage 2: Parallel Fan-Out ──

STAGE2_FANOUT_PROMPT = """
You are an Elite Technical Resume Writer. Rewrite the provided resume bullets using the provided Battle Plan context.

VARIATION DIRECTIVE: {variation_directive}

CONTEXT:
Company: {company}
Seniority: {seniority_level}
Impact Vocabulary: {impact_language}

BATTLE PLAN:
{battle_plan_json}

STRICT CONSTRAINTS:
1. **Forbidden Weak Verbs**: NEVER use: Helped, Assisted, Participated in, Involved in, Worked on, Handled, Utilized, Used, Supported, Contributed to, Facilitated, Employed, Ensured, Demonstrated, Showcased, Gained, Revolutionized, Synergized.
2. **Preserve Anchors**: Keep all technical terms (e.g. React, Docker) and exact metrics (e.g. 98%, $500k) verbatim.
3. **Diversity**: Follow the Battle Plan's preferred verb, but if this variation directive says to vary, use a diverse alternative from the Impact Vocabulary.

BULLETS TO REWRITE:
{bullets_json}

Return a JSON array:
[
  {{ "id": "bullet_id", "tailored_text": "...", "score": 8.5, "reasoning": "..." }}
]
"""

# ── Stage 5: Pro Safety Valve ──

STAGE5_PRO_PROMPT = """
You are a Staff Resume Editor. Solve this structural puzzle for a high-priority bullet.

CONSTRAINTS:
1. **Uniqueness**: The starting verb MUST NOT be in: {used_verbs}
2. **Forbidden**: NEVER use: Helped, Assisted, Worked on, Utilized, etc.
3. **No Gerunds**: Avoid the ", ...ing " pattern entirely.
4. **Context**: Pillar: {pillar} | Original: {original_text}

Provide an elite, action-first rewrite.

Return a JSON object: {{"text": "..."}}
"""

# ── Forbidden Verbs ──
FORBIDDEN_VERBS = [
    "Helped", "Assisted", "Worked on", "Handled", "Utilized", "Used",
    "Participated in", "Involved in", "Responsible for", "Supported",
    "Contributed to", "Facilitated", "Employed", "Ensured",
    "Demonstrated", "Showcased", "Gained", "Revolutionized", "Synergized"
]

# ── Stage 3 & 4 Logic ──

def _extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+%?|\$\d+(?:k|m|b)?", text.lower()))

def _is_gerund_heavy(text: str) -> bool:
    return bool(re.search(r",\s+\w+ing\b", text))

def _stage3_gatekeeper(candidates: list[dict], original_bullets: dict, forbidden: list[str]) -> list[dict]:
    survivors = []
    forbidden_pattern = re.compile(rf"^({'|'.join(forbidden)})\b", re.IGNORECASE)
    
    for cand in candidates:
        text = cand.get("tailored_text", "").strip()
        bid = cand.get("id")
        orig = original_bullets.get(bid, "")
        if not text or not bid:
            continue
        
        # 1. Forbidden verb check
        if forbidden_pattern.match(text):
            continue
        
        # 2. Metric integrity
        orig_nums = _extract_numbers(orig)
        cand_nums = _extract_numbers(text)
        if orig_nums and not orig_nums.issubset(cand_nums):
            continue
        
        survivors.append(cand)
    return survivors

def _stage4_assembler(bullet_ids: list[str], survivors: list[dict], org_role_groups: dict) -> tuple[dict, set]:
    selection = {}
    used_verbs_global = set()
    gerund_count = 0
    
    cand_map: dict[str, list[dict]] = {}
    for s in survivors:
        bid = s.get("id", "")
        if bid not in cand_map:
            cand_map[bid] = []
        cand_map[bid].append(s)
        
    for bid in bullet_ids:
        options = sorted(cand_map.get(bid, []), key=lambda x: x.get("score", 0), reverse=True)
        
        best = None
        for opt in options:
            text = opt.get("tailored_text", "").strip()
            if not text:
                continue
            first_word = text.split()[0].rstrip(",.;:").lower()
            
            is_ger = _is_gerund_heavy(text)
            if is_ger and gerund_count >= 2:
                continue
            
            if first_word in used_verbs_global:
                continue
            
            best = opt
            used_verbs_global.add(first_word)
            if is_ger:
                gerund_count += 1
            break
            
        selection[bid] = best
        
    return selection, used_verbs_global

# ── Main Pipeline ──

async def tailor_units_against_jd(units: list[dict[str, Any]], parsed_jd: ParsedJD) -> list[ScoredUnit]:
    """5-stage multi-agent tailoring pipeline with stage-level logging."""
    
    # 1. Split
    tailorable = [
        u for u in units
        if u.get("type") in ["bullet", "project"]
        and u.get("section", "").lower() != "education"
    ]
    passthrough = [u for u in units if u not in tailorable]
    
    print(f"\n{'='*60}")
    print(f"🚀 PIPELINE START: {len(tailorable)} bullets, {len(passthrough)} passthrough")
    print(f"{'='*60}")
    
    final_results: list[ScoredUnit] = []
    
    if tailorable:
        # Extract ONLY the fields the LLM needs (no ObjectId, datetime, etc.)
        tailorable_clean = [
            {
                "id": u.get("id"),
                "text": u.get("text", ""),
                "section": u.get("section", "experience"),
                "org": u.get("org"),
                "role": u.get("role"),
            }
            for u in tailorable
        ]
        bullets_dict = {u["id"]: u["text"] for u in tailorable_clean}
        org_role_groups = {u["id"]: f"{u.get('org')}_{u.get('role')}" for u in tailorable_clean}
        pillars_text = ", ".join([p.pillar_name for p in parsed_jd.strategic_pillars]) or "General"

        # ── STAGE 1 ──
        try:
            print("\n🎯 Stage 1: Tactical Planner...")
            plan_prompt = STAGE1_PLANNER_PROMPT.format(
                company=parsed_jd.company,
                business_mission=parsed_jd.business_mission or "not specified",
                pillars_text=pillars_text,
                bullets_json=json.dumps([{"id": k, "text": v} for k, v in bullets_dict.items()])
            )
            battle_plan = await generate_json(plan_prompt, temperature=0.1)
            bp_len = len(battle_plan) if isinstance(battle_plan, dict) else "?"
            print(f"   ✅ Stage 1 done — {bp_len} bullet strategies.")
        except Exception as e:
            print(f"   ❌ Stage 1 FAILED: {e}")
            tb.print_exc()
            raise

        # ── STAGE 2 ──
        try:
            print("\n🚀 Stage 2: Parallel Fan-Out (5x)...")
            directives = [
                "Follow the battle plan strictly.",
                "Use more descriptive synonyms for the preferred verbs.",
                "Focus on technical architecture and scope.",
                "Focus on business impact and outcomes.",
                "Vary all verbs to be as unique and punchy as possible.",
            ]
            fanout_prompts = [
                STAGE2_FANOUT_PROMPT.format(
                    company=parsed_jd.company,
                    seniority_level=parsed_jd.seniority_level or "not specified",
                    impact_language=", ".join(parsed_jd.impact_language) if parsed_jd.impact_language else "not specified",
                    battle_plan_json=json.dumps(battle_plan),
                    variation_directive=d,
                    bullets_json=json.dumps(tailorable_clean),
                )
                for d in directives
            ]
            responses = await generate_json_parallel(fanout_prompts, temperature=0.7)
            all_candidates = []
            for r in responses:
                if isinstance(r, list):
                    all_candidates.extend(r)
            print(f"   ✅ Stage 2 done — {len(all_candidates)} candidates.")
        except Exception as e:
            print(f"   ❌ Stage 2 FAILED: {e}")
            tb.print_exc()
            raise

        # ── STAGE 3 ──
        try:
            print(f"\n🛡️ Stage 3: Gatekeeper ({len(all_candidates)} candidates)...")
            survivors = _stage3_gatekeeper(all_candidates, bullets_dict, FORBIDDEN_VERBS)
            print(f"   ✅ Stage 3 done — {len(survivors)}/{len(all_candidates)} survived.")
        except Exception as e:
            print(f"   ❌ Stage 3 FAILED: {e}")
            tb.print_exc()
            raise

        # ── STAGE 4 ──
        try:
            print("\n🧩 Stage 4: Assembler...")
            selection, used_verbs = _stage4_assembler(
                [u["id"] for u in tailorable_clean], survivors, org_role_groups
            )
            assigned = sum(1 for v in selection.values() if v is not None)
            dead_ends = sum(1 for v in selection.values() if v is None)
            print(f"   ✅ Stage 4 done — {assigned} assigned, {dead_ends} dead-ends.")
            print(f"   Verbs: {used_verbs}")
        except Exception as e:
            print(f"   ❌ Stage 4 FAILED: {e}")
            tb.print_exc()
            raise

        # ── STAGE 5: Recovery + Build ──
        for u in tailorable:
            bid = u.get("id")
            chosen = selection.get(bid)

            if not chosen:
                print(f"\n🆘 Stage 5: Safety Valve for [{bid}]")
                try:
                    bp_entry = battle_plan.get(bid, {}) if isinstance(battle_plan, dict) else {}
                    pillar = bp_entry.get("pillar", "General") if isinstance(bp_entry, dict) else "General"
                    pro_prompt = STAGE5_PRO_PROMPT.format(
                        used_verbs=", ".join(used_verbs),
                        forbidden_words=", ".join(FORBIDDEN_VERBS),
                        pillar=pillar,
                        original_text=u.get("text", ""),
                    )
                    result = await generate_json(pro_prompt, temperature=0.1)
                    final_text = result.get("text", u.get("text", "")) if isinstance(result, dict) else str(result)
                    final_score = 7.0
                    reasoning = "Recovered via Safety Valve"
                    first = final_text.split()[0].lower() if final_text.split() else ""
                    used_verbs.add(first)
                    print(f"   ✅ Recovered: {final_text[:60]}...")
                except Exception as e:
                    print(f"   ❌ Stage 5 FAILED for [{bid}]: {e}")
                    final_text = u.get("text", "")
                    final_score = 5.0
                    reasoning = "Stage 5 failed — original preserved"
            else:
                final_text = chosen.get("tailored_text", u.get("text", ""))
                final_score = chosen.get("score", 8.0)
                reasoning = chosen.get("reasoning", "")

            final_results.append(ScoredUnit(
                unit_id=str(bid or ""),
                text=final_text,
                original_text=u.get("text", ""),
                section=u.get("section", "experience"),
                org=u.get("org"),
                role=u.get("role"),
                dates=u.get("dates"),
                tags=u.get("tags"),
                llm_score=float(final_score),
                reasoning=reasoning,
                matched_requirements=[],
            ))

    # Passthrough
    for p in passthrough:
        final_results.append(ScoredUnit(
            unit_id=str(p.get("id", "")),
            text=p.get("text", ""),
            original_text=p.get("text", ""),
            section=p.get("section", "skills"),
            org=p.get("org"),
            role=p.get("role"),
            dates=p.get("dates"),
            tags=p.get("tags"),
            llm_score=10.0,
            reasoning="Preserved verbatim",
            matched_requirements=[],
        ))

    print(f"\n{'='*60}")
    print(f"✅ PIPELINE COMPLETE: {len(final_results)} total units")
    print(f"{'='*60}\n")

    return final_results
