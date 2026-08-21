"""HTTP routes package."""

from api.routes.account import router as account_router
from api.routes.chat import router as chat_router
from api.routes.completion import router as completion_router
from api.routes.connected_papers import router as connected_papers_router
from api.routes.diary import router as diary_router
from api.routes.dim import router as dim_router
from api.routes.enrich import router as enrich_router
from api.routes.gap_heatmap import router as gap_heatmap_router
from api.routes.gap_profile import router as gap_profile_router
from api.routes.notes import router as notes_router
from api.routes.onboarding import router as onboarding_router
from api.routes.paper_detail import router as paper_detail_router
from api.routes.project import router as project_router
from api.routes.project_bibliometrics import router as project_bibliometrics_router
from api.routes.project_graph import router as project_graph_router
from api.routes.q import router as q_router
from api.routes.reading_list import router as reading_list_router
from api.routes.research_area import router as research_area_router
from api.routes.review import router as review_router
from api.routes.search import router as search_router
from api.routes.summarize import router as summarize_router
from api.routes.theme import router as theme_router
from api.routes.top5 import router as top5_router
from api.routes.tts import router as tts_router
from api.routes.waitlist import router as waitlist_router
from api.routes.workshop import router as workshop_router

__all__ = [
    "account_router",
    "chat_router",
    "completion_router",
    "connected_papers_router",
    "diary_router",
    "dim_router",
    "enrich_router",
    "gap_heatmap_router",
    "gap_profile_router",
    "notes_router",
    "onboarding_router",
    "paper_detail_router",
    "project_bibliometrics_router",
    "project_graph_router",
    "project_router",
    "q_router",
    "reading_list_router",
    "research_area_router",
    "review_router",
    "search_router",
    "summarize_router",
    "theme_router",
    "top5_router",
    "tts_router",
    "waitlist_router",
    "workshop_router",
]
