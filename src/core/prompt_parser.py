"""Natural language prompt parser using LLM and pattern matching"""

import re
import json
import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..clients.llm_provider import create_llm_provider
from ..models.prompt_models import (
    ParsedUserRequest, ParsingResult, ContentFilter, QuantityFilter, 
    TimeFilter, OutputPreferences, ActionType, ContentType, ParticipantType,
    TimeRange, SortOrder, DifficultyLevel, ChallengeType, VideoCategory,
    KOREAN_ACTION_KEYWORDS, KOREAN_CONTENT_KEYWORDS, KOREAN_DIFFICULTY_KEYWORDS,
    KOREAN_PARTICIPANT_KEYWORDS, KOREAN_TIME_KEYWORDS, KOREAN_SORT_KEYWORDS
)
from ..core.exceptions import ClassificationError

logger = logging.getLogger(__name__)


@dataclass
class ParsingContext:
    """Context information for parsing process"""
    original_input: str
    normalized_input: str
    detected_language: str
    confidence_factors: Dict[str, float]
    processing_steps: List[str]


class PromptParser:
    """
    Advanced natural language prompt parser using hybrid approach:
    1. Regex pattern matching for common patterns
    2. LLM-based parsing for complex/ambiguous cases
    3. Confidence scoring and validation
    """
    
    def __init__(self):
        """Initialize the prompt parser"""
        self.llm_provider = None
        self.parsing_patterns = self._compile_patterns()
        logger.info("PromptParser initialized")
    
    async def _ensure_llm_provider(self):
        """Ensure LLM provider is available"""
        if self.llm_provider is None:
            self.llm_provider = create_llm_provider()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile common regex patterns for quick matching"""
        patterns = {
            # Numbers and quantities
            'numbers': re.compile(r'\b(\d+)(?:개|명|인|번|위)?\b'),
            'top_n': re.compile(r'(?:top|상위|탑)\s*(\d+)', re.IGNORECASE),
            'count_request': re.compile(r'(\d+)\s*(?:개|명|인|번)'),
            
            # Time expressions
            'time_recent': re.compile(r'(?:최근|요즘|recent)\s*(\d+)?\s*(?:일|주|달|개월|month|week|day)?'),
            'time_this': re.compile(r'(?:이번|this)\s*(?:주|달|월|week|month)'),
            'time_last': re.compile(r'(?:지난|last)\s*(?:주|달|월|week|month)'),
            'time_days': re.compile(r'(\d+)\s*(?:일|day)(?:간|동안|내)?'),
            
            # View count filters
            'view_count': re.compile(r'조회수\s*(\d+(?:만|억|천|,\d+)*)\s*(?:이상|넘는|초과)'),
            'view_count_million': re.compile(r'(\d+)(?:만|million)'),
            'view_count_hundred_million': re.compile(r'(\d+)(?:억|hundred million)'),
            
            # Content types
            'dance_related': re.compile(r'댄스|춤|dance|안무|choreography', re.IGNORECASE),
            'challenge_related': re.compile(r'챌린지|challenge', re.IGNORECASE),
            'kpop': re.compile(r'(?:k-?pop|케이팝|아이돌)', re.IGNORECASE),
            
            # Difficulty
            'easy': re.compile(r'쉬운|간단한|초보자|기초|easy|simple|basic', re.IGNORECASE),
            'hard': re.compile(r'어려운|고급|복잡한|힘든|hard|difficult|advanced', re.IGNORECASE),
            
            # Participants
            'couple': re.compile(r'커플|둘이서|couple|duo', re.IGNORECASE),
            'group': re.compile(r'그룹|단체|여러명|group|team', re.IGNORECASE),
            'kids': re.compile(r'아이들|어린이|kids|children', re.IGNORECASE),
            'family': re.compile(r'가족|family', re.IGNORECASE),
            
            # Actions
            'find': re.compile(r'찾아줘|보여줘|검색|알아봐|find|show', re.IGNORECASE),
            'recommend': re.compile(r'추천|골라줘|선택|recommend|suggest', re.IGNORECASE),
            'analyze': re.compile(r'분석|살펴봐|analyze', re.IGNORECASE),
        }
        
        return patterns
    
    async def parse(self, user_input: str) -> ParsingResult:
        """
        Parse user input into structured request
        
        Args:
            user_input: Natural language input from user
            
        Returns:
            ParsingResult with parsed request or error information
        """
        start_time = datetime.now()
        processing_steps = []
        
        try:
            # Step 1: Create parsing context
            processing_steps.append("Creating parsing context")
            context = self._create_parsing_context(user_input)
            
            # Step 2: Try regex-based quick parsing first
            processing_steps.append("Attempting regex-based parsing")
            quick_result = self._try_quick_parse(context)
            
            if quick_result and quick_result.confidence >= 0.8:
                processing_steps.append("Quick parsing successful")
                processing_time = (datetime.now() - start_time).total_seconds()
                
                return ParsingResult(
                    success=True,
                    parsed_request=quick_result,
                    processing_time=processing_time,
                    parsing_steps=processing_steps
                )
            
            # Step 3: Use LLM for complex parsing
            processing_steps.append("Using LLM for advanced parsing")
            await self._ensure_llm_provider()
            
            llm_result = await self._llm_parse(context, quick_result)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if llm_result:
                processing_steps.append("LLM parsing successful")
                return ParsingResult(
                    success=True,
                    parsed_request=llm_result,
                    processing_time=processing_time,
                    parsing_steps=processing_steps
                )
            else:
                processing_steps.append("LLM parsing failed, using fallback")
                fallback_result = self._create_fallback_result(context)
                processing_time = (datetime.now() - start_time).total_seconds()
                
                return ParsingResult(
                    success=True,
                    parsed_request=fallback_result,
                    processing_time=processing_time,
                    warnings=["Used fallback parsing due to complex input"],
                    parsing_steps=processing_steps
                )
                
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Parsing failed for input '{user_input}': {e}")
            
            return ParsingResult(
                success=False,
                error_message=str(e),
                processing_time=processing_time,
                parsing_steps=processing_steps
            )
    
    def _create_parsing_context(self, user_input: str) -> ParsingContext:
        """Create parsing context with normalized input and language detection"""
        normalized = user_input.strip().lower()
        
        # Simple language detection
        korean_chars = len(re.findall(r'[가-힣]', user_input))
        total_chars = len(re.findall(r'[가-힣a-zA-Z]', user_input))
        korean_ratio = korean_chars / total_chars if total_chars > 0 else 0
        
        detected_language = "korean" if korean_ratio > 0.3 else "english"
        
        return ParsingContext(
            original_input=user_input,
            normalized_input=normalized,
            detected_language=detected_language,
            confidence_factors={},
            processing_steps=[]
        )
    
    def _try_quick_parse(self, context: ParsingContext) -> Optional[ParsedUserRequest]:
        """Attempt quick parsing using regex patterns"""
        try:
            input_text = context.normalized_input
            confidence_factors = {}
            
            # Extract action type
            action_type = self._extract_action_type(input_text, confidence_factors)
            
            # Extract content information
            content_filter = self._extract_content_filter(input_text, confidence_factors)
            
            # Extract quantity information
            quantity_filter = self._extract_quantity_filter(input_text, confidence_factors)
            
            # Extract time information
            time_filter = self._extract_time_filter(input_text, confidence_factors)
            
            # Extract output preferences
            output_preferences = self._extract_output_preferences(input_text, confidence_factors)
            
            # Calculate overall confidence
            overall_confidence = sum(confidence_factors.values()) / len(confidence_factors) if confidence_factors else 0.5
            
            # Create parsed request
            parsed_request = ParsedUserRequest(
                original_input=context.original_input,
                action_type=action_type,
                confidence=overall_confidence,
                content_filter=content_filter,
                quantity_filter=quantity_filter,
                time_filter=time_filter,
                output_preferences=output_preferences,
                parsed_at=datetime.now(),
                parser_version="1.0"
            )
            
            return parsed_request
            
        except Exception as e:
            logger.warning(f"Quick parsing failed: {e}")
            return None
    
    def _extract_action_type(self, input_text: str, confidence_factors: Dict) -> ActionType:
        """Extract action type from input text"""
        # Check for Korean action keywords
        for action, keywords in KOREAN_ACTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in input_text:
                    confidence_factors['action'] = 0.9
                    return ActionType(action)
        
        # Default to find
        confidence_factors['action'] = 0.3
        return ActionType.FIND
    
    def _extract_content_filter(self, input_text: str, confidence_factors: Dict) -> ContentFilter:
        """Extract content-related filters"""
        content_filter = ContentFilter()
        
        # Detect content type using enhanced keyword matching
        content_type_detected = None
        best_confidence = 0.0
        
        for content_type, keywords in KOREAN_CONTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in input_text:
                    current_confidence = 0.9
                    if current_confidence > best_confidence:
                        best_confidence = current_confidence
                        content_type_detected = content_type
                    break
        
        if content_type_detected:
            if content_type_detected == "dance_challenge":
                content_filter.content_type = ContentType.DANCE_CHALLENGE
                content_filter.challenge_type = ChallengeType.DANCE
            elif content_type_detected == "food_challenge":
                content_filter.content_type = ContentType.FOOD_CHALLENGE
                content_filter.challenge_type = ChallengeType.FOOD
            elif content_type_detected == "fitness_challenge":
                content_filter.content_type = ContentType.FITNESS_CHALLENGE
                content_filter.challenge_type = ChallengeType.FITNESS
            elif content_type_detected == "creative_challenge":
                content_filter.content_type = ContentType.CREATIVE_CHALLENGE
            elif content_type_detected == "game_challenge":
                content_filter.content_type = ContentType.GAME_CHALLENGE
            else:
                content_filter.content_type = ContentType.GENERAL_CHALLENGE
            
            content_filter.video_category = VideoCategory.CHALLENGE
            confidence_factors['content_type'] = best_confidence
        else:
            # Fallback to pattern matching for dance
            if self.parsing_patterns['dance_related'].search(input_text):
                content_filter.content_type = ContentType.DANCE_CHALLENGE
                content_filter.challenge_type = ChallengeType.DANCE
                content_filter.video_category = VideoCategory.CHALLENGE
                confidence_factors['content_type'] = 0.8
            else:
                content_filter.content_type = ContentType.GENERAL_CHALLENGE
                confidence_factors['content_type'] = 0.5
        
        # Extract keywords
        keywords = []
        if 'kpop' in input_text or 'k-pop' in input_text:
            keywords.append('kpop')
            content_filter.genre = "K-pop"
        
        content_filter.keywords = keywords
        
        # Extract difficulty
        if self.parsing_patterns['easy'].search(input_text):
            content_filter.difficulty = DifficultyLevel.EASY
            confidence_factors['difficulty'] = 0.8
        elif self.parsing_patterns['hard'].search(input_text):
            content_filter.difficulty = DifficultyLevel.HARD
            confidence_factors['difficulty'] = 0.8
        
        # Extract participant type
        if self.parsing_patterns['couple'].search(input_text):
            content_filter.participants = ParticipantType.COUPLE
            confidence_factors['participants'] = 0.8
        elif self.parsing_patterns['group'].search(input_text):
            content_filter.participants = ParticipantType.GROUP
            confidence_factors['participants'] = 0.8
        elif self.parsing_patterns['kids'].search(input_text):
            content_filter.participants = ParticipantType.KIDS
            confidence_factors['participants'] = 0.8
        elif self.parsing_patterns['family'].search(input_text):
            content_filter.participants = ParticipantType.FAMILY
            confidence_factors['participants'] = 0.8
        
        return content_filter
    
    def _extract_quantity_filter(self, input_text: str, confidence_factors: Dict) -> QuantityFilter:
        """Extract quantity and ranking information"""
        quantity_filter = QuantityFilter()
        
        # Look for TOP N patterns
        top_match = self.parsing_patterns['top_n'].search(input_text)
        if top_match:
            quantity_filter.top_n = int(top_match.group(1))
            quantity_filter.count = int(top_match.group(1))
            confidence_factors['quantity'] = 0.9
            return quantity_filter
        
        # Look for count requests
        count_match = self.parsing_patterns['count_request'].search(input_text)
        if count_match:
            quantity_filter.count = int(count_match.group(1))
            confidence_factors['quantity'] = 0.8
        else:
            # Look for any numbers
            number_match = self.parsing_patterns['numbers'].search(input_text)
            if number_match:
                quantity_filter.count = int(number_match.group(1))
                confidence_factors['quantity'] = 0.6
            else:
                confidence_factors['quantity'] = 0.3
        
        # Check for view count filters
        view_match = self.parsing_patterns['view_count'].search(input_text)
        if view_match:
            view_text = view_match.group(1)
            view_count = self._parse_korean_numbers(view_text)
            quantity_filter.min_views = view_count
            confidence_factors['view_filter'] = 0.8
        
        return quantity_filter
    
    def _extract_time_filter(self, input_text: str, confidence_factors: Dict) -> TimeFilter:
        """Extract time-related filters"""
        time_filter = TimeFilter()
        
        # Check for specific time ranges
        if self.parsing_patterns['time_this'].search(input_text):
            if '주' in input_text or 'week' in input_text:
                time_filter.time_range = TimeRange.THIS_WEEK
            elif '달' in input_text or '월' in input_text or 'month' in input_text:
                time_filter.time_range = TimeRange.THIS_MONTH
            confidence_factors['time'] = 0.9
        elif self.parsing_patterns['time_last'].search(input_text):
            if '주' in input_text or 'week' in input_text:
                time_filter.time_range = TimeRange.LAST_WEEK
            elif '달' in input_text or '월' in input_text or 'month' in input_text:
                time_filter.time_range = TimeRange.LAST_MONTH
            confidence_factors['time'] = 0.9
        elif self.parsing_patterns['time_recent'].search(input_text):
            time_filter.time_range = TimeRange.RECENT
            confidence_factors['time'] = 0.8
        else:
            confidence_factors['time'] = 0.5
        
        # Look for custom day counts
        days_match = self.parsing_patterns['time_days'].search(input_text)
        if days_match:
            time_filter.time_range = TimeRange.CUSTOM
            time_filter.custom_days = int(days_match.group(1))
            confidence_factors['time'] = 0.9
        
        return time_filter
    
    def _extract_output_preferences(self, input_text: str, confidence_factors: Dict) -> OutputPreferences:
        """Extract output format preferences"""
        output_preferences = OutputPreferences()
        
        # Language detection
        korean_chars = len(re.findall(r'[가-힣]', input_text))
        total_chars = len(re.findall(r'[가-힣a-zA-Z]', input_text))
        
        if korean_chars / total_chars > 0.3 if total_chars > 0 else False:
            output_preferences.language = "korean"
        else:
            output_preferences.language = "english"
        
        confidence_factors['output'] = 0.7
        return output_preferences
    
    def _parse_korean_numbers(self, text: str) -> int:
        """Parse Korean number expressions to integers"""
        # Remove commas and spaces
        text = text.replace(',', '').replace(' ', '')
        
        # Handle Korean units
        if '억' in text:
            number = int(text.replace('억', ''))
            return number * 100000000
        elif '만' in text:
            number = int(text.replace('만', ''))
            return number * 10000
        elif '천' in text:
            number = int(text.replace('천', ''))
            return number * 1000
        else:
            try:
                return int(text)
            except ValueError:
                return 0
    
    async def _llm_parse(self, context: ParsingContext, quick_result: Optional[ParsedUserRequest]) -> Optional[ParsedUserRequest]:
        """Use LLM for advanced parsing of complex requests"""
        try:
            prompt = self._create_llm_parsing_prompt(context, quick_result)
            
            # Use a simple text generation approach instead of structured output
            # since we already have the parsing logic
            response = await self._call_llm_for_parsing(prompt)
            
            if response:
                # Parse the LLM response and enhance the quick result
                enhanced_result = self._enhance_with_llm_response(context, quick_result, response)
                return enhanced_result
            
            return quick_result
            
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            return quick_result
    
    def _create_llm_parsing_prompt(self, context: ParsingContext, quick_result: Optional[ParsedUserRequest]) -> str:
        """Create prompt for LLM parsing"""
        prompt = f"""자연어 요청을 분석하여 구조화된 정보를 추출해주세요.

사용자 입력: "{context.original_input}"

다음 정보를 분석해주세요:
1. 요청 액션 (찾기/추천/분석/비교/설명)
2. 콘텐츠 타입 (댄스챌린지/음식챌린지/피트니스챌린지 등)
3. 필터 조건 (난이도, 참여자 수, 장르 등)
4. 수량 및 순위 (몇 개, TOP N 등)
5. 시간 범위 (최근, 이번 주, 지난 달 등)
6. 특별 요구사항

기존 분석 결과가 있다면 참고하되, 더 정확한 정보를 제공해주세요.

분석 결과를 JSON 형태로 제공해주세요:
{{
    "action": "find|recommend|analyze|compare|explain",
    "content_type": "dance_challenge|food_challenge|fitness_challenge|etc",
    "keywords": ["키워드1", "키워드2"],
    "difficulty": "easy|medium|hard",
    "participants": "individual|couple|group|kids|family",
    "count": 숫자,
    "time_range": "recent|this_week|last_month|etc",
    "special_requirements": ["요구사항1", "요구사항2"],
    "confidence": 0.0-1.0
}}"""
        
        return prompt
    
    async def _call_llm_for_parsing(self, prompt: str) -> Optional[str]:
        """Call LLM for parsing assistance"""
        try:
            # Use the existing LLM provider's Gemini capabilities
            if hasattr(self.llm_provider, 'video_analysis_model'):
                import google.generativeai as genai
                
                response = self.llm_provider.video_analysis_model.generate_content(prompt)
                return response.text if hasattr(response, 'text') else None
            
            return None
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None
    
    def _enhance_with_llm_response(self, context: ParsingContext, quick_result: Optional[ParsedUserRequest], llm_response: str) -> ParsedUserRequest:
        """Enhance quick result with LLM insights"""
        if quick_result is None:
            # Create new result based on LLM response
            return self._create_fallback_result(context)
        
        try:
            # Try to extract JSON from LLM response
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                llm_data = json.loads(json_match.group())
                
                # Enhance the quick result with LLM insights
                if 'keywords' in llm_data:
                    quick_result.content_filter.keywords.extend(llm_data['keywords'])
                
                if 'special_requirements' in llm_data:
                    quick_result.content_filter.must_include.extend(llm_data['special_requirements'])
                
                # Update confidence based on LLM confidence
                if 'confidence' in llm_data:
                    quick_result.confidence = max(quick_result.confidence, llm_data['confidence'])
                
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
        
        return quick_result
    
    def _create_fallback_result(self, context: ParsingContext) -> ParsedUserRequest:
        """Create fallback result when parsing fails"""
        return ParsedUserRequest(
            original_input=context.original_input,
            action_type=ActionType.FIND,
            confidence=0.3,
            content_filter=ContentFilter(
                content_type=ContentType.GENERAL_CHALLENGE,
                keywords=[context.original_input]  # Use entire input as keyword
            ),
            quantity_filter=QuantityFilter(count=10),
            time_filter=TimeFilter(time_range=TimeRange.RECENT),
            output_preferences=OutputPreferences(
                language=context.detected_language
            ),
            parsed_at=datetime.now(),
            parser_version="1.0",
            ambiguous_parts=[context.original_input],
            suggestions=["입력을 더 구체적으로 표현해보세요"]
        )


# Factory function
def create_prompt_parser() -> PromptParser:
    """Create a new prompt parser instance"""
    return PromptParser()