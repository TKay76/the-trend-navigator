"""Natural language prompt parsing models for user query processing"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from .video_models import VideoCategory, ChallengeType, DifficultyLevel


class ActionType(str, Enum):
    """Types of actions user can request"""
    FIND = "find"           # "찾아줘", "보여줘", "검색해줘"
    RECOMMEND = "recommend" # "추천해줘", "골라줘"
    ANALYZE = "analyze"     # "분석해줘", "살펴봐"
    COMPARE = "compare"     # "비교해줘"
    EXPLAIN = "explain"     # "설명해줘", "알려줘"


class ContentType(str, Enum):
    """Types of content user can request"""
    DANCE_CHALLENGE = "dance_challenge"
    FOOD_CHALLENGE = "food_challenge"
    FITNESS_CHALLENGE = "fitness_challenge"
    CREATIVE_CHALLENGE = "creative_challenge"
    GAME_CHALLENGE = "game_challenge"
    GENERAL_CHALLENGE = "general_challenge"
    ANY_VIDEO = "any_video"


class ParticipantType(str, Enum):
    """Types of participants in challenges"""
    INDIVIDUAL = "individual"  # "개인", "혼자", "solo"
    COUPLE = "couple"          # "커플", "둘이서", "couple"
    GROUP = "group"            # "그룹", "단체", "여러명"
    KIDS = "kids"              # "아이들", "어린이", "kids"
    FAMILY = "family"          # "가족", "family"
    ANY = "any"                # 특별한 제한 없음


class TimeRange(str, Enum):
    """Time ranges for content search"""
    TODAY = "today"           # "오늘", "today"
    THIS_WEEK = "this_week"   # "이번 주", "this week"
    THIS_MONTH = "this_month" # "이번 달", "this month"
    RECENT = "recent"         # "최근", "recent" (기본 7일)
    LAST_WEEK = "last_week"   # "지난 주"
    LAST_MONTH = "last_month" # "지난 달"
    CUSTOM = "custom"         # 사용자 지정 기간


class SortOrder(str, Enum):
    """Sort orders for results"""
    VIEW_COUNT_DESC = "view_count_desc"     # "조회수 높은 순"
    VIEW_COUNT_ASC = "view_count_asc"       # "조회수 낮은 순"
    LIKE_COUNT_DESC = "like_count_desc"     # "좋아요 많은 순"
    RECENT_FIRST = "recent_first"           # "최신순"
    OLDEST_FIRST = "oldest_first"           # "오래된 순"
    DIFFICULTY_ASC = "difficulty_asc"       # "쉬운 순"
    DIFFICULTY_DESC = "difficulty_desc"     # "어려운 순"
    RELEVANCE = "relevance"                 # "관련도순" (기본값)


class ContentFilter(BaseModel):
    """Content-related filters extracted from user input"""
    content_type: ContentType = Field(ContentType.GENERAL_CHALLENGE, description="Type of content requested")
    challenge_type: Optional[ChallengeType] = Field(None, description="Specific challenge type if specified")
    video_category: Optional[VideoCategory] = Field(None, description="Video category classification")
    
    # Content characteristics
    difficulty: Optional[DifficultyLevel] = Field(None, description="Requested difficulty level")
    participants: ParticipantType = Field(ParticipantType.ANY, description="Target participant type")
    
    # Keywords and tags
    keywords: List[str] = Field(default=[], description="Extracted keywords for search")
    must_include: List[str] = Field(default=[], description="Keywords that must be included")
    must_exclude: List[str] = Field(default=[], description="Keywords that must be excluded")
    
    # Genre/style filters
    genre: Optional[str] = Field(None, description="Music genre or style (e.g., 'K-pop', 'hip-hop')")
    style: Optional[str] = Field(None, description="Challenge style or theme")


class QuantityFilter(BaseModel):
    """Quantity and ranking related filters"""
    count: int = Field(10, description="Number of results requested", ge=1, le=50)
    top_n: Optional[int] = Field(None, description="TOP N ranking request")
    min_views: Optional[int] = Field(None, description="Minimum view count filter")
    max_views: Optional[int] = Field(None, description="Maximum view count filter")
    
    # Ranking preferences
    sort_order: SortOrder = Field(SortOrder.RELEVANCE, description="Preferred sort order")
    include_ranking: bool = Field(True, description="Whether to include ranking numbers")


class TimeFilter(BaseModel):
    """Time-related filters for content search"""
    time_range: TimeRange = Field(TimeRange.RECENT, description="Time range for search")
    custom_days: Optional[int] = Field(None, description="Custom number of days if time_range is CUSTOM")
    start_date: Optional[datetime] = Field(None, description="Custom start date")
    end_date: Optional[datetime] = Field(None, description="Custom end date")


class OutputPreferences(BaseModel):
    """User preferences for output format and content"""
    include_links: bool = Field(True, description="Include YouTube links")
    include_thumbnails: bool = Field(True, description="Include thumbnail images")
    include_analysis: bool = Field(True, description="Include detailed analysis")
    include_trends: bool = Field(True, description="Include trend analysis")
    
    format_preference: str = Field("markdown", description="Preferred output format")
    language: str = Field("korean", description="Preferred language for response")
    detail_level: str = Field("medium", description="Level of detail (basic/medium/detailed)")


class ParsedUserRequest(BaseModel):
    """
    Complete parsed user request with all extracted information
    """
    # Core request information
    original_input: str = Field(..., description="Original user input text")
    action_type: ActionType = Field(..., description="Type of action requested")
    confidence: float = Field(..., description="Parsing confidence score", ge=0.0, le=1.0)
    
    # Parsed filters
    content_filter: ContentFilter = Field(..., description="Content-related filters")
    quantity_filter: QuantityFilter = Field(..., description="Quantity and ranking filters")
    time_filter: TimeFilter = Field(..., description="Time-related filters")
    output_preferences: OutputPreferences = Field(..., description="Output preferences")
    
    # Metadata
    parsed_at: datetime = Field(default_factory=datetime.now, description="When this request was parsed")
    parser_version: str = Field("1.0", description="Version of parser used")
    
    # Additional context
    context_keywords: List[str] = Field(default=[], description="Additional context extracted")
    ambiguous_parts: List[str] = Field(default=[], description="Parts of input that were ambiguous")
    suggestions: List[str] = Field(default=[], description="Suggestions for clarification")


class ParsingExample(BaseModel):
    """
    Example input-output pairs for training and validation
    """
    input_text: str = Field(..., description="Example user input")
    expected_output: ParsedUserRequest = Field(..., description="Expected parsing result")
    category: str = Field(..., description="Example category for organization")
    difficulty: str = Field("medium", description="Parsing difficulty level")
    notes: Optional[str] = Field(None, description="Additional notes about this example")


class ParsingResult(BaseModel):
    """
    Result of parsing operation with metadata
    """
    success: bool = Field(..., description="Whether parsing was successful")
    parsed_request: Optional[ParsedUserRequest] = Field(None, description="Parsed request if successful")
    error_message: Optional[str] = Field(None, description="Error message if parsing failed")
    warnings: List[str] = Field(default=[], description="Warnings during parsing")
    processing_time: float = Field(..., description="Time taken to parse in seconds")
    
    # Debugging information
    raw_llm_response: Optional[str] = Field(None, description="Raw LLM response for debugging")
    parsing_steps: List[str] = Field(default=[], description="Steps taken during parsing")


# Common parsing patterns and examples
PARSING_EXAMPLES = [
    {
        "input": "댄스 챌린지 TOP 10 찾아줘",
        "category": "basic",
        "notes": "Simple dance challenge request"
    },
    {
        "input": "초보자도 쉽게 따라할 수 있는 K-pop 댄스 5개 추천해줘",
        "category": "filtered",
        "notes": "With difficulty and genre filters"
    },
    {
        "input": "커플이 함께 할 수 있는 로맨틱한 댄스 챌린지 보여줘",
        "category": "participant_specific",
        "notes": "Participant type and style specification"
    },
    {
        "input": "최근 2주간 조회수 100만 이상인 바이럴 댄스 3개만",
        "category": "complex_filter",
        "notes": "Time, view count, and quantity filters"
    },
    {
        "input": "아이들도 따라할 수 있는 안전한 댄스 챌린지가 있나?",
        "category": "safety_focused",
        "notes": "Safety and age-appropriate content"
    }
]


# Keywords mapping for Korean/English support
KOREAN_ACTION_KEYWORDS = {
    "find": ["찾아줘", "보여줘", "검색해줘", "알아봐줘", "찾아봐", "있나", "있어"],
    "recommend": ["추천해줘", "골라줘", "선택해줘", "제안해줘", "추천"],
    "analyze": ["분석해줘", "살펴봐", "분석", "어떤지", "어떻게"],
    "compare": ["비교해줘", "비교", "차이", "vs", "대비"],
    "explain": ["설명해줘", "알려줘", "가르쳐줘", "뭐야", "무엇"]
}

KOREAN_CONTENT_KEYWORDS = {
    "dance_challenge": ["댄스", "춤", "댄스챌린지", "댄스 챌린지", "안무", "춤챌린지", "kpop", "k-pop"],
    "food_challenge": ["음식", "먹방", "요리", "푸드", "food", "쿡방", "레시피", "recipe", "베이킹", "baking"],
    "fitness_challenge": ["운동", "헬스", "피트니스", "다이어트", "workout", "홈트", "요가", "yoga", "pilates"],
    "creative_challenge": ["창작", "그림", "만들기", "diy", "아트", "craft", "handmade", "튜토리얼"],
    "game_challenge": ["게임", "놀이", "퀴즈", "경기", "gaming", "play", "게임플레이"],
    "beauty_challenge": ["뷰티", "메이크업", "beauty", "makeup", "skincare", "화장", "스킨케어"],
    "tech_challenge": ["기술", "tech", "technology", "리뷰", "review", "언박싱", "unboxing"],
    "lifestyle_challenge": ["일상", "vlog", "lifestyle", "daily", "루틴", "routine"],
    "educational_challenge": ["교육", "학습", "배우기", "tutorial", "how to", "강의", "공부"]
}

KOREAN_DIFFICULTY_KEYWORDS = {
    "easy": ["쉬운", "간단한", "초보자", "기초", "easy", "simple", "basic"],
    "medium": ["보통", "중간", "적당한", "medium"],
    "hard": ["어려운", "고급", "복잡한", "힘든", "hard", "difficult", "advanced"]
}

KOREAN_PARTICIPANT_KEYWORDS = {
    "individual": ["혼자", "개인", "솔로", "solo", "individual"],
    "couple": ["커플", "둘이서", "couple", "duo", "pair"],
    "group": ["그룹", "단체", "여러명", "group", "team"],
    "kids": ["아이들", "어린이", "kids", "children"],
    "family": ["가족", "family"]
}

KOREAN_TIME_KEYWORDS = {
    "today": ["오늘", "today"],
    "this_week": ["이번주", "이번 주", "this week"],
    "this_month": ["이번달", "이번 달", "this month"],
    "recent": ["최근", "recent", "요즘"],
    "last_week": ["지난주", "지난 주", "last week"],
    "last_month": ["지난달", "지난 달", "last month"]
}

KOREAN_SORT_KEYWORDS = {
    "view_count_desc": ["조회수 높은 순", "인기순", "많이 본 순"],
    "view_count_asc": ["조회수 낮은 순", "적게 본 순"],
    "like_count_desc": ["좋아요 많은 순", "추천 많은 순"],
    "recent_first": ["최신순", "새로운 순", "최근 순"],
    "oldest_first": ["오래된 순", "옛날 순"],
    "difficulty_asc": ["쉬운 순", "난이도 낮은 순"],
    "difficulty_desc": ["어려운 순", "난이도 높은 순"]
}