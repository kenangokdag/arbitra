"""F8 ROLE_MODULES registry (DM-LLM-7).

Pilot 3 mode (F8) + librarian (F9 P094) + hyde_packet (F9 P095) + vitrin (V1);
kalan 8 mode F9-S2.
"""

from pathlib import Path

from api.services.role_modules.academic_dimension import ACADEMIC_DIMENSION_BRIEF
from api.services.role_modules.advisor_summary import ADVISOR_SUMMARY_BRIEF
from api.services.role_modules.citation_critic import CITATION_CRITIC_BRIEF
from api.services.role_modules.completion_step_review import (
    COMPLETION_STEP_REVIEW_BRIEF,
)
from api.services.role_modules.critic_sempatik import CRITIC_SEMPATIK_BRIEF
from api.services.role_modules.critic_skeptik import CRITIC_SKEPTIK_BRIEF
from api.services.role_modules.critic_yontemci import CRITIC_YONTEMCI_BRIEF
from api.services.role_modules.defense_questions import DEFENSE_QUESTIONS_BRIEF
from api.services.role_modules.diary_pre_advisor import DIARY_PRE_ADVISOR_BRIEF
from api.services.role_modules.draft_skeleton import DRAFT_SKELETON_BRIEF
from api.services.role_modules.gap_heatmap import GAP_HEATMAP_BRIEF
from api.services.role_modules.gap_profile_story import GAP_PROFILE_STORY_BRIEF
from api.services.role_modules.impact_curve_comment import IMPACT_CURVE_COMMENT_BRIEF
from api.services.role_modules.jury_anti_tez import JURY_ANTI_TEZ_BRIEF
from api.services.role_modules.jury_canli import JURY_CANLI_BRIEF
from api.services.role_modules.jury_consistency import JURY_CONSISTENCY_BRIEF
from api.services.role_modules.jury_dis_disiplin import JURY_DIS_DISIPLIN_BRIEF
from api.services.role_modules.jury_hyde import JURY_HYDE_BRIEF
from api.services.role_modules.jury_pratisyen import JURY_PRATISYEN_BRIEF
from api.services.role_modules.jury_yontemci import JURY_YONTEMCI_BRIEF
from api.services.role_modules.librarian import LIBRARIAN_BRIEF
from api.services.role_modules.manuscript_auto_draft import MANUSCRIPT_AUTO_DRAFT_BRIEF
from api.services.role_modules.manuscript_classifier import MANUSCRIPT_CLASSIFIER_BRIEF
from api.services.role_modules.manuscript_quality import MANUSCRIPT_QUALITY_BRIEF
from api.services.role_modules.method_selection import METHOD_SELECTION_BRIEF
from api.services.role_modules.novelty_critic import NOVELTY_CRITIC_BRIEF
from api.services.role_modules.originality_micro import ORIGINALITY_MICRO_BRIEF
from api.services.role_modules.personal_feedback import PERSONAL_FEEDBACK_BRIEF
from api.services.role_modules.qualitative_rigor import QUALITATIVE_RIGOR_BRIEF
from api.services.role_modules.quantitative_validity import QUANTITATIVE_VALIDITY_BRIEF
from api.services.role_modules.review_advisor import REVIEW_ADVISOR_BRIEF
from api.services.role_modules.review_editor import REVIEW_EDITOR_BRIEF
from api.services.role_modules.review_writer import REVIEW_WRITER_BRIEF
from api.services.role_modules.reviewer_sempatik import REVIEWER_SEMPATIK_BRIEF
from api.services.role_modules.reviewer_skeptik import REVIEWER_SKEPTIK_BRIEF
from api.services.role_modules.reviewer_yontemci import REVIEWER_YONTEMCI_BRIEF
from api.services.role_modules.study_compare_advice import STUDY_COMPARE_ADVICE_BRIEF
from api.services.role_modules.synthesize_workshop import SYNTHESIZE_WORKSHOP_BRIEF
from api.services.role_modules.topic_exploration import TOPIC_EXPLORATION_BRIEF
from api.services.role_modules.topic_proposals import TOPIC_PROPOSALS_BRIEF
from api.services.role_modules.translate_query import TRANSLATE_QUERY_BRIEF
from api.services.role_modules.vitrin_literature import VITRIN_LITERATURE_BRIEF
from api.services.role_modules.vitrin_summary import VITRIN_SUMMARY_BRIEF

_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"
HYDE_PACKET_BRIEF = (_PROMPTS_DIR / "hyde_packet_v1.md").read_text(encoding="utf-8")

ROLE_MODULES: dict[str, str] = {
    "topic_exploration": TOPIC_EXPLORATION_BRIEF,
    "method_selection": METHOD_SELECTION_BRIEF,
    "gap_heatmap": GAP_HEATMAP_BRIEF,
    "librarian": LIBRARIAN_BRIEF,
    "hyde_packet": HYDE_PACKET_BRIEF,
    "vitrin_summary": VITRIN_SUMMARY_BRIEF,
    "vitrin_literature": VITRIN_LITERATURE_BRIEF,
    "translate_query": TRANSLATE_QUERY_BRIEF,
    "diary_pre_advisor": DIARY_PRE_ADVISOR_BRIEF,
    "advisor_summary": ADVISOR_SUMMARY_BRIEF,
    "synthesize_workshop": SYNTHESIZE_WORKSHOP_BRIEF,
    "originality_micro": ORIGINALITY_MICRO_BRIEF,
    "gap_profile_story": GAP_PROFILE_STORY_BRIEF,
    "study_compare_advice": STUDY_COMPARE_ADVICE_BRIEF,
    "impact_curve_comment": IMPACT_CURVE_COMMENT_BRIEF,
    "topic_proposals": TOPIC_PROPOSALS_BRIEF,
    "draft_skeleton": DRAFT_SKELETON_BRIEF,
    "manuscript_quality": MANUSCRIPT_QUALITY_BRIEF,
    "manuscript_auto_draft": MANUSCRIPT_AUTO_DRAFT_BRIEF,
    "defense_questions": DEFENSE_QUESTIONS_BRIEF,
    "personal_feedback": PERSONAL_FEEDBACK_BRIEF,
    "reviewer_skeptik": REVIEWER_SKEPTIK_BRIEF,
    "reviewer_sempatik": REVIEWER_SEMPATIK_BRIEF,
    "reviewer_yontemci": REVIEWER_YONTEMCI_BRIEF,
    "review_writer": REVIEW_WRITER_BRIEF,
    "citation_critic": CITATION_CRITIC_BRIEF,
    "novelty_critic": NOVELTY_CRITIC_BRIEF,
    # F14-S4 run_orchestration critics (Critique şeması) — reviewer_skeptik/
    # sempatik/yontemci'den AYRI: onlar F13 journal_sim_service'e ait,
    # ReviewerPersonaOutput (questions[]) bekler (2026-08-04 bug fix).
    "critic_skeptik": CRITIC_SKEPTIK_BRIEF,
    "critic_sempatik": CRITIC_SEMPATIK_BRIEF,
    "critic_yontemci": CRITIC_YONTEMCI_BRIEF,
    "review_editor": REVIEW_EDITOR_BRIEF,
    "jury_canli": JURY_CANLI_BRIEF,
    "jury_anti_tez": JURY_ANTI_TEZ_BRIEF,
    "jury_yontemci": JURY_YONTEMCI_BRIEF,
    "jury_dis_disiplin": JURY_DIS_DISIPLIN_BRIEF,
    "jury_pratisyen": JURY_PRATISYEN_BRIEF,
    "jury_hyde": JURY_HYDE_BRIEF,
    "jury_consistency": JURY_CONSISTENCY_BRIEF,
    "completion_step_review": COMPLETION_STEP_REVIEW_BRIEF,
    "manuscript_classifier": MANUSCRIPT_CLASSIFIER_BRIEF,
    "qualitative_rigor": QUALITATIVE_RIGOR_BRIEF,
    "quantitative_validity": QUANTITATIVE_VALIDITY_BRIEF,
    "academic_dimension": ACADEMIC_DIMENSION_BRIEF,
    "review_advisor": REVIEW_ADVISOR_BRIEF,
}

__all__ = ["HYDE_PACKET_BRIEF", "ROLE_MODULES"]
