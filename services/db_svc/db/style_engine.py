"""
Style Engine - Content formatting and rendering system.

This module handles the transformation of raw RSS content into formatted messages
using Style definitions. It supports templates, hashtag injection, content limits,
and provides hooks for ML/LLM enhancement.
"""

import re
import html
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup
from .models import Style, FeedContent, Channel


@dataclass
class FormattingContext:
    """Context information for content formatting."""
    feed_content: FeedContent
    style: Style
    channel: Channel
    user_preferences: Optional[Dict[str, Any]] = None
    custom_variables: Optional[Dict[str, Any]] = None


@dataclass
class FormattingResult:
    """Result of content formatting operation."""
    formatted_text: str
    metadata: Dict[str, Any]
    tags_used: List[str]
    length: int
    truncated: bool = False
    processing_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'formatted_text': self.formatted_text,
            'metadata': self.metadata,
            'tags_used': self.tags_used,
            'length': self.length,
            'truncated': self.truncated,
            'processing_time_ms': self.processing_time_ms
        }


class StyleEngine:
    """Content formatting engine that applies Style rules to FeedContent."""
    
    def __init__(self):
        self.default_templates = {
            'full': '<b>{title}</b>\n\n{description}\n\n{tags}\n\n<a href="{url}">Read more →</a>',
            'minimal': '<b>{title}</b>\n<a href="{url}">Read more →</a>',
            'news': '📰 <b>{title}</b>\n\n{description}\n\n{tags}\n\n🔗 <a href="{url}">Full article</a>',
            'summary': '<b>{title}</b>\n\n{summary}\n\n{tags}\n\n<a href="{url}">Read more →</a>'
        }
    
    def format_content(self, context: FormattingContext) -> FormattingResult:
        """
        Format RSS content according to style rules.
        
        Args:
            context: FormattingContext with content, style, and channel info
            
        Returns:
            FormattingResult with formatted text and metadata
        """
        start_time = datetime.now()
        
        try:
            # Prepare content variables
            variables = self._extract_content_variables(context)
            
            # Apply content cleaning and preprocessing
            variables = self._preprocess_content(variables, context.style)
            
            # Generate tags
            tags = self._generate_tags(context)
            variables['tags'] = ' '.join(tags) if tags else ''
            
            # Apply template
            template = self._get_template(context.style)
            formatted_text = self._apply_template(template, variables, context.style)
            
            # Apply post-processing rules
            formatted_text = self._apply_post_processing(formatted_text, context.style)
            
            # Enforce length limits
            formatted_text, truncated = self._enforce_length_limits(formatted_text, context.style)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return FormattingResult(
                formatted_text=formatted_text,
                metadata={
                    'template_used': template,
                    'variables_available': list(variables.keys()),
                    'style_id': context.style.id,
                    'style_name': context.style.name,
                    'channel_id': context.channel.id,
                    'content_type': context.feed_content.content_type
                },
                tags_used=tags,
                length=len(formatted_text),
                truncated=truncated,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            # Fallback to minimal formatting on error
            fallback_text = f"<b>{context.feed_content.title}</b>\n<a href=\"{context.feed_content.url}\">Read more →</a>"
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return FormattingResult(
                formatted_text=fallback_text,
                metadata={
                    'error': str(e),
                    'fallback_used': True,
                    'style_id': context.style.id if context.style else None
                },
                tags_used=['#error'],
                length=len(fallback_text),
                truncated=False,
                processing_time_ms=processing_time
            )
    
    def _extract_content_variables(self, context: FormattingContext) -> Dict[str, str]:
        """Extract variables from feed content for template substitution."""
        content = context.feed_content
        
        variables = {
            'title': content.title or 'Untitled',
            'description': content.description or '',
            'summary': content.summary or content.description or '',
            'url': content.url,
            'author': content.author or '',
            'published_date': content.published_date.strftime('%Y-%m-%d %H:%M') if content.published_date else '',
            'published_date_short': content.published_date.strftime('%m/%d') if content.published_date else '',
            'channel_title': context.channel.title,
            'channel_username': context.channel.username or '',
        }
        
        # Add custom variables if provided
        if context.custom_variables:
            variables.update(context.custom_variables)
            
        return variables
    
    def _preprocess_content(self, variables: Dict[str, str], style: Style) -> Dict[str, str]:
        """Clean and preprocess content variables."""
        # Clean HTML from description and summary
        if variables['description']:
            variables['description'] = self._clean_html(variables['description'])
        
        if variables['summary']:
            variables['summary'] = self._clean_html(variables['summary'])
        
        # Apply quote prefixes if configured
        if style.quote_prefix or style.quote_suffix:
            if variables['description']:
                variables['description'] = self._apply_quotes(
                    variables['description'], 
                    style.quote_prefix, 
                    style.quote_suffix
                )
        
        # Truncate long descriptions
        max_desc_length = style.advanced_rules.get('max_description_length', 1000)
        if len(variables['description']) > max_desc_length:
            variables['description'] = variables['description'][:max_desc_length] + '...'
        
        return variables
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and clean up text content."""
        if not text:
            return ''
        
        # Parse HTML
        soup = BeautifulSoup(text, 'html.parser')
        
        # Remove unwanted tags
        for tag in soup.find_all(['script', 'style', 'iframe', 'object', 'embed']):
            tag.decompose()
        
        # Get text and clean whitespace
        clean_text = soup.get_text()
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Unescape HTML entities
        clean_text = html.unescape(clean_text)
        
        return clean_text
    
    def _apply_quotes(self, text: str, prefix: Optional[str], suffix: Optional[str]) -> str:
        """Apply quote prefixes and suffixes to text."""
        if not text:
            return text
            
        if prefix:
            text = f"{prefix} {text}"
        if suffix:
            text = f"{text} {suffix}"
            
        return text
    
    def _generate_tags(self, context: FormattingContext) -> List[str]:
        """Generate hashtags based on style rules and content analysis."""
        tags = []
        style = context.style
        content = context.feed_content
        
        # Add style-defined hashtags
        if style.hashtags:
            tags.extend(style.hashtags)
        
        # Add content-based tags
        if content.tags:
            # Convert content tags to hashtags
            content_hashtags = [f"#{tag.strip().lower().replace(' ', '_')}" 
                             for tag in content.tags if tag.strip()]
            tags.extend(content_hashtags[:3])  # Limit to 3 content tags
        
        # Add category-based tags
        if content.categories:
            category_hashtags = [f"#{cat.strip().lower().replace(' ', '_')}" 
                               for cat in content.categories[:2] if cat.strip()]
            tags.extend(category_hashtags)
        
        # Content type tags
        if content.content_type and content.content_type != 'text':
            tags.append(f"#{content.content_type}")
        
        # Advanced rule-based tags
        advanced_rules = style.advanced_rules or {}
        if advanced_rules.get('auto_tags', True):
            auto_tags = self._extract_auto_tags(content.title, content.description)
            tags.extend(auto_tags[:2])  # Limit auto-generated tags
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            tag_clean = tag.lower()
            if tag_clean not in seen:
                seen.add(tag_clean)
                unique_tags.append(tag)
        
        # Limit total tags
        max_tags = advanced_rules.get('max_tags', 5)
        return unique_tags[:max_tags]
    
    def _extract_auto_tags(self, title: str, description: str) -> List[str]:
        """Extract automatic tags based on content analysis."""
        # TODO: Implement ML/LLM-based tag extraction
        # For now, use simple keyword matching
        
        auto_tags = []
        content = f"{title} {description}".lower()
        
        # Simple keyword-based tags
        tag_keywords = {
            '#ai': ['artificial intelligence', 'machine learning', 'neural network', 'deep learning'],
            '#tech': ['technology', 'software', 'programming', 'development'],
            '#news': ['breaking', 'report', 'announce', 'update'],
            '#science': ['research', 'study', 'discovery', 'experiment'],
            '#business': ['company', 'startup', 'investment', 'market']
        }
        
        for tag, keywords in tag_keywords.items():
            if any(keyword in content for keyword in keywords):
                auto_tags.append(tag)
        
        return auto_tags
    
    def _get_template(self, style: Style) -> str:
        """Get the template to use for formatting."""
        if style.template:
            return style.template
        
        # Fallback to default templates based on style name
        style_name_lower = style.name.lower()
        if 'minimal' in style_name_lower:
            return self.default_templates['minimal']
        elif 'news' in style_name_lower:
            return self.default_templates['news']
        elif 'summary' in style_name_lower:
            return self.default_templates['summary']
        else:
            return self.default_templates['full']
    
    def _apply_template(self, template: str, variables: Dict[str, str], style: Style) -> str:
        """Apply template with variable substitution."""
        try:
            # Simple variable substitution
            formatted = template
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                formatted = formatted.replace(placeholder, str(value))
            
            return formatted
            
        except Exception as e:
            # Fallback on template error
            return f"<b>{variables.get('title', 'Error')}</b>\n<a href=\"{variables.get('url', '#')}\">Read more →</a>"
    
    def _apply_post_processing(self, text: str, style: Style) -> str:
        """Apply post-processing rules to formatted text."""
        advanced_rules = style.advanced_rules or {}
        
        # Remove empty lines
        if advanced_rules.get('remove_empty_lines', True):
            text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Apply text transformations
        transformations = advanced_rules.get('transformations', {})
        if transformations.get('uppercase_title'):
            # Find titles in bold and uppercase them
            text = re.sub(r'<b>(.*?)</b>', lambda m: f"<b>{m.group(1).upper()}</b>", text)
        
        # Limit consecutive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _enforce_length_limits(self, text: str, style: Style) -> Tuple[str, bool]:
        """Enforce maximum length limits and truncate if necessary."""
        max_length = style.max_length
        
        if len(text) <= max_length:
            return text, False
        
        # Smart truncation - try to break at sentence or word boundaries
        truncated = text[:max_length - 3]  # Reserve space for "..."
        
        # Find last sentence boundary
        last_sentence = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?')
        )
        
        if last_sentence > max_length * 0.7:  # If we found a good sentence break
            truncated = truncated[:last_sentence + 1]
        else:
            # Find last word boundary
            last_space = truncated.rfind(' ')
            if last_space > max_length * 0.8:
                truncated = truncated[:last_space]
        
        return truncated + "...", True
    
    def create_style_preview(self, style: Style, sample_content: Dict[str, str]) -> str:
        """Create a preview of how content would look with this style."""
        # Create mock objects for preview
        from .models import FeedContent, Channel
        
        mock_content = type('MockFeedContent', (), {
            'title': sample_content.get('title', 'Sample Article Title'),
            'description': sample_content.get('description', 'This is a sample article description that shows how your content will be formatted.'),
            'summary': sample_content.get('summary', 'Sample summary'),
            'url': sample_content.get('url', 'https://example.com/article'),
            'author': sample_content.get('author', 'Sample Author'),
            'published_date': datetime.now(),
            'content_type': 'text',
            'tags': ['technology', 'news'],
            'categories': ['Tech News']
        })()
        
        mock_channel = type('MockChannel', (), {
            'title': 'Sample Channel',
            'username': 'sample_channel',
            'id': 1
        })()
        
        context = FormattingContext(
            feed_content=mock_content,
            style=style,
            channel=mock_channel
        )
        
        result = self.format_content(context)
        return result.formatted_text


# Global style engine instance
style_engine = StyleEngine()


# TODO: ML/LLM Enhancement Hooks
# These are placeholder functions for future ML/LLM integration

def enhance_content_with_ai(content: FeedContent, style: Style) -> Dict[str, Any]:
    """
    TODO: Integrate with AI service for content enhancement.
    
    This function should:
    1. Call ai_svc for content summarization
    2. Extract keywords and entities
    3. Generate improved descriptions
    4. Suggest optimal hashtags
    5. Detect content sentiment/topics
    
    Args:
        content: FeedContent to enhance
        style: Style preferences for enhancement
        
    Returns:
        Dict with enhanced content fields
    """
    # Placeholder implementation
    return {
        'enhanced_summary': content.summary or content.description,
        'suggested_tags': ['#ai_suggested'],
        'sentiment': 'neutral',
        'topics': [],
        'enhancement_confidence': 0.0
    }


def generate_smart_hashtags(title: str, description: str, channel_context: str) -> List[str]:
    """
    TODO: Generate intelligent hashtags using ML/LLM.
    
    This should analyze content and generate relevant hashtags based on:
    1. Content topic classification
    2. Named entity recognition
    3. Channel-specific preferences
    4. Trending topics analysis
    
    Args:
        title: Article title
        description: Article description
        channel_context: Channel topic/style context
        
    Returns:
        List of suggested hashtags
    """
    # Placeholder implementation
    return ['#ml_generated']


def optimize_content_for_engagement(content: str, channel_stats: Dict) -> str:
    """
    TODO: Optimize content for maximum engagement.
    
    This should:
    1. Analyze channel engagement patterns
    2. Suggest optimal content length
    3. Recommend emoji usage
    4. Optimize posting time suggestions
    
    Args:
        content: Formatted content
        channel_stats: Channel performance statistics
        
    Returns:
        Optimized content string
    """
    # Placeholder implementation
    return content