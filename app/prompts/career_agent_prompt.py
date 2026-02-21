"""Prompt template for the Career Agent."""

import json


def build_career_agent_system_prompt(cv_profile: dict) -> str:
    """Build the system prompt for the Career Agent, injecting CV context."""

    cv_summary = _format_cv_summary(cv_profile)

    return f"""You are a professional Career Assistant AI Agent acting on behalf of a job candidate.
Your role is to read incoming employer messages and compose professional, polite, and concise responses
grounded in the candidate's CV/profile information provided below.

═══════════════════════════════════════
CANDIDATE PROFILE
═══════════════════════════════════════
{cv_summary}
═══════════════════════════════════════

INSTRUCTIONS:
1. Always maintain a **professional**, **concise**, and **polite** tone.
2. Ground every factual claim in the candidate's profile above — never fabricate experience, skills, or credentials.
3. Classify the employer's message into exactly ONE of these categories:
   - interview_invitation  — scheduling or confirming interviews
   - technical_question    — questions about skills, experience, or technical topics
   - offer_decline         — politely declining offers or opportunities
   - clarification         — requesting more details from the employer
   - unknown               — the message doesn't fit any above category or you are unsure
4. Output your response as a JSON object with exactly these fields:
   - "response"   (string): your professional reply to the employer
   - "confidence" (float 0-1): how confident you are that the response is accurate and appropriate
   - "category"   (string): one of the five categories above

CONFIDENCE GUIDELINES:
- 0.9-1.0 : Very confident — clear intent, straightforward response
- 0.7-0.89: Confident — reasonable interpretation, good response
- 0.4-0.69: Uncertain — ambiguous message, best-effort response
- 0.0-0.39: Low confidence — risky topic (salary negotiation, legal, non-compete, unknown deep technical area)

For salary negotiations, legal/contractual questions, non-compete clauses, or topics NOT covered in the CV,
set confidence below 0.4 so the system can flag it for human intervention.

OUTPUT FORMAT (strict JSON):
```json
{{
  "response": "...",
  "confidence": 0.85,
  "category": "interview_invitation"
}}
```

Respond ONLY with the JSON object. Do not include any extra text, explanation, or markdown outside the JSON.
"""


def _format_cv_summary(cv: dict) -> str:
    """Format CV profile dict into a readable summary string for the prompt."""
    if not cv:
        return "No CV profile loaded. Respond based on general professional etiquette."

    parts: list[str] = []

    # Name & Title
    if cv.get("name") or cv.get("title"):
        parts.append(f"Name: {cv.get('name', 'N/A')}  |  Title: {cv.get('title', 'N/A')}")

    # Summary
    if cv.get("summary"):
        parts.append(f"Summary: {cv['summary']}")

    # Experience
    if cv.get("experience"):
        parts.append("\nExperience:")
        for exp in cv["experience"]:
            techs = ", ".join(exp.get("technologies", []))
            parts.append(
                f"  • {exp.get('role', '')} @ {exp.get('company', '')} ({exp.get('period', '')})\n"
                f"    {exp.get('description', '')}\n"
                f"    Tech: {techs}"
            )

    # Education
    if cv.get("education"):
        parts.append("\nEducation:")
        for edu in cv["education"]:
            parts.append(
                f"  • {edu.get('degree', '')} {edu.get('field', '')} — {edu.get('institution', '')} ({edu.get('period', '')})"
            )

    # Skills
    if cv.get("skills"):
        skills = cv["skills"]
        skill_lines = []
        for category, items in skills.items():
            if isinstance(items, list):
                skill_lines.append(f"  {category}: {', '.join(items)}")
        if skill_lines:
            parts.append("\nSkills:\n" + "\n".join(skill_lines))

    # Certifications
    if cv.get("certifications"):
        parts.append("\nCertifications:")
        for cert in cv["certifications"]:
            parts.append(f"  • {cert.get('name', '')} — {cert.get('issuer', '')} ({cert.get('year', '')})")

    # Languages
    if cv.get("languages"):
        lang_strs = [f"{l.get('language', '')}: {l.get('level', '')}" for l in cv["languages"]]
        parts.append(f"\nLanguages: {', '.join(lang_strs)}")

    # Projects
    if cv.get("projects"):
        parts.append("\nKey Projects:")
        for proj in cv["projects"]:
            parts.append(f"  • {proj.get('name', '')}: {proj.get('description', '')}")

    # Preferences
    if cv.get("preferences"):
        prefs = cv["preferences"]
        parts.append(
            f"\nPreferences: {prefs.get('work_type', '')} | Notice: {prefs.get('notice_period', '')} | "
            f"Relocate: {'Yes' if prefs.get('willing_to_relocate') else 'No'}"
        )

    return "\n".join(parts)
